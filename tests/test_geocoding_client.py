import pytest
from unittest.mock import Mock, patch

import requests

from city_vibe.clients.geo.openmeteo_geocoding_client import OpenMeteoGeocodingClient


def _mock_response(status_code=200, json_data=None):
    """Create a minimal mock of requests.Response."""
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = Mock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError("HTTP error")
    return resp


@patch("city_vibe.clients.geo.openmeteo_geocoding_client.requests.get")
def test_geocode_success_returns_lat_lon(mock_get):
    mock_get.return_value = _mock_response(
        200,
        json_data={"results": [{"latitude": 59.3293, "longitude": 18.0686}]},
    )

    client = OpenMeteoGeocodingClient()
    lat, lon = client.geocode("Stockholm", country_code="SE")

    assert lat == 59.3293
    assert lon == 18.0686

    # Verify request parameters were used (basic check)
    args, kwargs = mock_get.call_args
    assert "timeout" in kwargs
    assert kwargs["params"]["name"] == "Stockholm"
    assert kwargs["params"]["count"] == 1
    assert kwargs["params"]["country_code"] == "SE"


@patch("city_vibe.clients.geo.openmeteo_geocoding_client.requests.get")
def test_geocode_no_results_raises_value_error(mock_get):
    mock_get.return_value = _mock_response(200, json_data={"results": []})

    client = OpenMeteoGeocodingClient()
    with pytest.raises(ValueError):
        client.geocode("NoSuchCity", country_code="SE")


@patch("city_vibe.clients.geo.openmeteo_geocoding_client.requests.get")
def test_geocode_http_error_is_raised(mock_get):
    mock_get.return_value = _mock_response(500, json_data={})

    client = OpenMeteoGeocodingClient()
    with pytest.raises(requests.HTTPError):
        client.geocode("Stockholm", country_code="SE")
