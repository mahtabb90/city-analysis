import logging
from datetime import datetime, timedelta
from typing import List, Optional

from city_vibe.clients.weather.openmeteo_client import OpenMeteoClient
from city_vibe.clients.traffic.traffic_client import TrafficClient
from city_vibe.clients.geocoding.geocoding_client import GeocodingClient
from city_vibe.domain.models import (
    WeatherRecord,
    TrafficRecord,
    ForecastRecord,
)
from city_vibe import database
from city_vibe.analysis.vibe_algorithm import calculate_vibe

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self):
        self.weather_client = OpenMeteoClient()
        self.traffic_client = TrafficClient()
        self.geocoding_client = GeocodingClient()

    def refresh_city_data(self, city_name: str) -> Optional[int]:
        """
        Fetches 60 days of historical weather and traffic data for a given city,
        stores it in the database, and marks the city as confirmed.
        """
        try:
            # 1. Get or create city and its coordinates
            city_id = database.get_or_create_city(city_name)
            city_record = database.get_city_by_id(city_id)
            if (
                not city_record
                or not city_record.latitude
                or not city_record.longitude
            ):
                logger.error(
                    f"Could not get coordinates for city '{city_name}'. "
                    "Aborting data refresh."
                )
                return None

            lat, lon = city_record.latitude, city_record.longitude
            logger.info(
                f"Refreshing data for city '{city_name}' ({lat}, {lon})."
            )

            # Define date range for historical data (60 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)

            # Fetch historical weather data
            weather_history_raw = (
                self.weather_client.get_historical_weather_range(
                    lat, lon, start_date, end_date
                )
            )
            if weather_history_raw:
                weather_records = [
                    WeatherRecord(
                        city_id=city_id,
                        timestamp=rec["date"],
                        temperature=rec["temperature"],
                        humidity=rec["humidity"],
                        wind_speed=rec["wind_speed"],
                        precipitation=rec["precipitation"],
                    )
                    for rec in weather_history_raw
                ]
                database.insert_many_records("weather_data", weather_records)
                logger.info(
                    f"Stored {len(weather_records)} historical weather "
                    f"records for '{city_name}'."
                )
            else:
                logger.warning(
                    f"No historical weather data fetched for '{city_name}'."
                )

            # Fetch historical traffic data
            traffic_history_raw = (
                self.traffic_client.get_historical_traffic_range(
                    city_name, start_date, end_date
                )
            )
            if traffic_history_raw:
                traffic_records = [
                    TrafficRecord(
                        city_id=city_id,
                        timestamp=datetime.fromisoformat(rec["timestamp"]),
                        congestion_level=rec["congestion"],
                        speed=rec["speed"],
                        incidents=rec["incidents"],
                    )
                    for rec in traffic_history_raw
                ]
                database.insert_many_records("traffic_data", traffic_records)
                logger.info(
                    f"Stored {len(traffic_records)} historical traffic "
                    f"records for '{city_name}'."
                )
            else:
                logger.warning(
                    f"No historical traffic data fetched for '{city_name}'."
                )

            # Mark city as confirmed
            database.update_city_confirmation_status(
                city_id, True, updated_at=datetime.now()
            )
            logger.info(f"City '{city_name}' marked as confirmed.")
            return city_id

        except Exception as e:
            logger.error(f"Error refreshing data for city '{city_name}': {e}")
            return None

    def get_city_forecast(self, city_name: str) -> Optional[List[ForecastRecord]]:
        """
        Fetches the 7-day weather forecast for a given city,
        stores it in the database (replacing old forecast), and returns it.
        """
        try:
            city_record = database.get_city_by_id(
                database.get_or_create_city(city_name)
            )
            if (
                not city_record
                or not city_record.latitude
                or not city_record.longitude
            ):
                logger.error(
                    f"Could not get coordinates for city '{city_name}'. "
                    "Aborting forecast fetch."
                )
                return None

            lat, lon = city_record.latitude, city_record.longitude
            logger.info(
                f"Fetching 7-day forecast for '{city_name}' ({lat}, {lon})."
            )

            forecast_raw = self.weather_client.get_forecast_daily(
                lat, lon, days=7
            )

            if forecast_raw and forecast_raw.get("days"):
                retrieval_time = datetime.now()

                forecast_records = [
                    ForecastRecord(
                        city_id=city_record.id,
                        date=rec["date"],
                        description=rec["description"],
                        temp_max=rec["temp_max"],
                        temp_min=rec["temp_min"],
                        feels_like_max=rec["feels_like_max"],
                        feels_like_min=rec["feels_like_min"],
                        precipitation_mm=rec["precipitation_mm"],
                        precipitation_chance=rec["precipitation_chance"],
                        wind_speed_max=rec["wind_speed_max"],
                        forecast_retrieval_time=retrieval_time,
                    )
                    for rec in forecast_raw["days"]
                ]
                database.insert_many_records("forecast_data", forecast_records)
                logger.info(
                    f"Stored {len(forecast_records)} forecast records "
                    f"for '{city_name}'."
                )
                return forecast_records
            else:
                logger.warning(
                    f"No 7-day forecast data fetched for '{city_name}'."
                )
                return None
        except Exception as e:
            logger.error(f"Error fetching forecast for city '{city_name}': {e}")
            return None

    def refresh_all_confirmed_cities_current_data(self):
        """
        Fetches current data, forecasts, and updates the vibe analysis
        for all confirmed cities.
        """
        logger.info("Refreshing all data for confirmed cities.")
        confirmed_cities = database.get_confirmed_cities()

        if not confirmed_cities:
            logger.info("No confirmed cities found. Skipping refresh.")
            return

        for city in confirmed_cities:
            try:
                # 1. Fetch current weather
                current_weather_raw = self.weather_client.get_current_weather(
                    city.latitude, city.longitude
                )
                if current_weather_raw:
                    weather_record = WeatherRecord(
                        city_id=city.id,
                        timestamp=current_weather_raw["time"],
                        temperature=current_weather_raw["temperature"],
                        humidity=None,
                        wind_speed=current_weather_raw["wind_speed"],
                        precipitation=current_weather_raw["rain"],
                    )
                    database.insert_record("weather_data", weather_record)
                    logger.info(f"Updated current weather for '{city.name}'.")

                # 2. Fetch current traffic
                current_traffic_raw = self.traffic_client.get_current_traffic(
                    city.name
                )
                if current_traffic_raw:
                    traffic_record = TrafficRecord(
                        city_id=city.id,
                        timestamp=datetime.fromisoformat(
                            current_traffic_raw["timestamp"]
                        ),
                        congestion_level=current_traffic_raw["congestion"],
                        speed=current_traffic_raw["speed"],
                        incidents=current_traffic_raw["incidents"],
                    )
                    database.insert_record("traffic_data", traffic_record)
                    logger.info(f"Updated current traffic for '{city.name}'.")

                # 3. Update 7-day forecast
                self.get_city_forecast(city.name)

                # 4. Trigger Vibe Analysis
                analysis = calculate_vibe(city.name)
                logger.info(
                    f"Vibe analysis for '{city.name}' complete: "
                    f"{analysis.category}"
                )

            except Exception as e:
                logger.error(
                    f"Error refreshing data for city '{city.name}': {e}"
                )
