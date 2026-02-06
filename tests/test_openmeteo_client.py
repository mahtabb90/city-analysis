import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from city_vibe.clients.weather.openmeteo_client import OpenMeteoClient


@patch("city_vibe.clients.weather.openmeteo_client.requests.Session")
def test_get_current_weather_success(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "current": {
            "time": "2026-02-06T12:00",
            "temperature_2m": 2.5,
            "apparent_temperature": 0.0,
            "rain": 0.0,
            "cloud_cover": 100,
            "wind_speed_10m": 15.0,
            "weather_code": 3,
        }
    }
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    client = OpenMeteoClient()
    weather = client.get_current_weather(59.3293, 18.0686)

    assert weather["temperature"] == 2.5
    assert weather["description"] == "Overcast"
    assert isinstance(weather["time"], datetime)


@patch("city_vibe.clients.weather.openmeteo_client.requests.Session")
def test_get_forecast_daily_success(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "daily": {
            "time": ["2026-02-06", "2026-02-07"],
            "weather_code": [0, 1],
            "temperature_2m_max": [5.0, 6.0],
            "temperature_2m_min": [0.0, 1.0],
            "apparent_temperature_max": [3.0, 4.0],
            "apparent_temperature_min": [-2.0, -1.0],
            "precipitation_sum": [0.0, 1.0],
            "precipitation_probability_max": [10, 50],
            "wind_speed_10m_max": [10.0, 12.0],
        }
    }
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    client = OpenMeteoClient()
    forecast = client.get_forecast_daily(59.3293, 18.0686, days=2)

    assert len(forecast["days"]) == 2
    assert forecast["days"][0]["description"] == "Clear sky"
    assert forecast["days"][1]["temp_max"] == 6.0


@patch("city_vibe.clients.weather.openmeteo_client.requests.Session")
def test_get_historical_weather_range_success(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "daily": {
            "time": ["2026-01-01", "2026-01-02"],
            "temperature_2m_mean": [1.0, 2.0],
            "relative_humidity_2m_mean": [80, 85],
            "precipitation_sum": [0.0, 0.5],
            "weather_code": [3, 45],
            "wind_speed_10m_mean": [10, 15],
        }
    }
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    client = OpenMeteoClient()
    historical = client.get_historical_weather_range(
        59.3293, 18.0686, datetime(2026, 1, 1), datetime(2026, 1, 2)
    )

    assert len(historical) == 2
    assert historical[0]["temperature"] == 1.0
    assert historical[1]["description"] == "Fog"


@patch("city_vibe.clients.weather.openmeteo_client.requests.Session")
def test_fetch_error(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_session.get.side_effect = Exception("Network error")

    client = OpenMeteoClient()
    result = client.get_current_weather(0, 0)

    assert result is None
