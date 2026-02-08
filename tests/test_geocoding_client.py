import pytest
import requests
from unittest.mock import MagicMock, patch
from city_vibe.clients.geocoding.geocoding_client import GeocodingClient


@patch("city_vibe.clients.geocoding.geocoding_client.requests.Session")
def test_get_coordinates_success(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"latitude": 59.3293, "longitude": 18.0686}]
    }
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    client = GeocodingClient()
    coords = client.get_coordinates("Stockholm")

    assert coords == (59.3293, 18.0686)
    mock_session.get.assert_called_once()


@patch("city_vibe.clients.geocoding.geocoding_client.requests.Session")
def test_get_coordinates_no_results(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    client = GeocodingClient()
    coords = client.get_coordinates("UnknownCity")

    assert coords is None


@patch("city_vibe.clients.geocoding.geocoding_client.requests.Session")
def test_get_coordinates_api_error(mock_session_class):
    mock_session = mock_session_class.return_value
    mock_session.get.side_effect = requests.exceptions.RequestException("API Error")

    client = GeocodingClient()
    coords = client.get_coordinates("Stockholm")

    assert coords is None
