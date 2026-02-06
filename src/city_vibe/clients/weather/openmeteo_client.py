import requests
from datetime import datetime
from typing import Dict, Optional, List


class OpenMeteoClient:

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self):
        self.session = requests.Session()

    def _fetch(self, url: str, params: Dict) -> Dict:
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching from Open-Meteo: {e}")
            return {}

    @staticmethod
    def _wmo_to_description(code: int) -> str:
        """Convert WMO weather code to readable string"""
        mapping = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return mapping.get(code, f"Unknown weather code ({code})")

    def get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Returns None if the request fails.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,apparent_temperature,"
                "rain,weather_code,cloud_cover,wind_speed_10m"
            ),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
        }

        data = self._fetch(self.FORECAST_URL, params)
        if not data or "current" not in data:
            return None

        current = data["current"]

        return {
            "time": datetime.fromisoformat(current["time"]),
            "temperature": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "rain": current["rain"],  # mm in the last hour
            "cloud_cover": current["cloud_cover"],
            "wind_speed": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
            "description": self._wmo_to_description(current["weather_code"]),
        }

    def get_forecast_daily(
        self, lat: float, lon: float, days: int = 7
    ) -> Optional[Dict]:
        """
        7 days forecast
        Once again none if the request fails.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "weather_code,"
                "temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_sum,precipitation_probability_max,"
                "wind_speed_10m_max"
            ),
            "timezone": "auto",
            "forecast_days": min(days, 16),
        }

        data = self._fetch(self.FORECAST_URL, params)
        if not data or "daily" not in data or "time" not in data["daily"]:
            return None

        daily = data["daily"]
        forecast = []

        for i in range(len(daily["time"])):
            forecast.append(
                {
                    "date": datetime.fromisoformat(daily["time"][i]),
                    "description": self._wmo_to_description(
                        daily["weather_code"][i]
                    ),
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "feels_like_max": daily["apparent_temperature_max"][i],
                    "feels_like_min": daily["apparent_temperature_min"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "precipitation_chance": daily[
                        "precipitation_probability_max"
                    ][i],
                    "wind_speed_max": daily["wind_speed_10m_max"][i],
                }
            )

        return {
            "days": forecast,
            "timezone": data.get("timezone"),
            "latitude": lat,
            "longitude": lon,
        }

    def get_historical_weather_range(
        self, lat: float, lon: float, start_date: datetime, end_date: datetime
    ) -> Optional[List[Dict]]:
        """
        Fetches historical weather data for a specific range.
        Returns a list of daily weather data dictionaries if successful, otherwise None.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": (
                "temperature_2m_mean,"
                "relative_humidity_2m_mean,"
                "precipitation_sum,"
                "weather_code,"
                "wind_speed_10m_mean"
            ),
            "timezone": "auto",
        }

        data = self._fetch(self.ARCHIVE_URL, params)
        if not data or "daily" not in data or "time" not in data["daily"]:
            return None

        daily = data["daily"]
        historical_data = []

        for i in range(len(daily["time"])):
            historical_data.append(
                {
                    "date": datetime.fromisoformat(daily["time"][i]),
                    "temperature": daily["temperature_2m_mean"][i],
                    "humidity": daily["relative_humidity_2m_mean"][i],
                    "precipitation": daily["precipitation_sum"][i],
                    "weather_code": daily["weather_code"][i],
                    "description": self._wmo_to_description(
                        daily["weather_code"][i]
                    ),
                    "wind_speed": daily["wind_speed_10m_mean"][i],
                }
            )

        return historical_data
