import requests
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GeocodingClient:
    BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self):
        self.session = requests.Session()

    def get_coordinates(
        self, city_name: str, country_code: Optional[str] = "SE"
    ) -> Optional[Tuple[float, float]]:
        """
        Fetches latitude and longitude for a city name.
        Supports optional country_code (default "SE" for Sweden).
        Returns (lat, lon) tuple if found, otherwise None.
        """
        params = {
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        if country_code:
            params["country_code"] = country_code

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = data.get("results") or []
            if results:
                first_result = results[0]
                return (
                    float(first_result["latitude"]),
                    float(first_result["longitude"]),
                )
            else:
                logger.warning(f"No geocoding results for city: {city_name}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching geocoding data for {city_name}: {e}")
            return None
