import requests
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GeocodingClient:
    BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self):
        self.session = requests.Session()

    def get_coordinates(self, city_name: str) -> Optional[Tuple[float, float]]:
        """
        Fetches latitude and longitude for a city name.
        Returns (lat, lon) tuple if found, otherwise None.
        """
        params = {
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        try:
            response = self.session.get(
                self.BASE_URL, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data and "results" in data and len(data["results"]) > 0:
                first_result = data["results"][0]
                return first_result["latitude"], first_result["longitude"]
            else:
                logger.warning(f"No geocoding results for city: {city_name}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching geocoding data for {city_name}: {e}")
            return None
