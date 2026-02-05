from __future__ import annotations

import requests


class OpenMeteoGeocodingClient:
    """Simple city name -> (lat, lon) using Open-Meteo geocoding."""

    BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def geocode(self, city_name: str, *, country_code: str | None = "SE") -> tuple[float, float]:
        params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
        if country_code:
            params["country_code"] = country_code

        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results") or []
        if not results:
            raise ValueError(f"No geocoding result for city: {city_name}")

        best = results[0]
        return float(best["latitude"]), float(best["longitude"])
