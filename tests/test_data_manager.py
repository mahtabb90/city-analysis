import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from city_vibe.data_manager import DataManager
from city_vibe.domain.models import City

# --- Fixtures for Mocking Clients and Database ---


@pytest.fixture
def mock_open_meteo_client_instance():
    """Mocks the instance of OpenMeteoClient that DataManager uses."""
    with patch("city_vibe.data_manager.OpenMeteoClient") as MockOpenMeteoClass:
        mock_instance = MockOpenMeteoClass.return_value
        # Default mock responses
        mock_instance.get_historical_weather_range.return_value = [
            {
                "date": datetime.now() - timedelta(days=i),
                "temperature": 10.0,
                "humidity": 70.0,
                "wind_speed": 5.0,
                "precipitation": 0.0,
            }
            for i in range(60)
        ]
        mock_instance.get_forecast_daily.return_value = {
            "days": [
                {
                    "date": datetime.now() + timedelta(days=i),
                    "description": "sunny",
                    "temp_max": 20.0,
                    "temp_min": 10.0,
                    "feels_like_max": 18.0,
                    "feels_like_min": 8.0,
                    "precipitation_mm": 0.0,
                    "precipitation_chance": 0.0,
                    "wind_speed_max": 10.0,
                }
                for i in range(7)
            ]
        }
        mock_instance.get_current_weather.return_value = {
            "time": datetime.now(),
            "temperature": 15.0,
            "rain": 0.0,
            "cloud_cover": 50,
            "wind_speed": 10.0,
            "humidity": 60.0,
        }
        yield mock_instance


@pytest.fixture
def mock_traffic_client_instance():
    """Mocks the TrafficClient instance that DataManager uses."""
    with patch("city_vibe.data_manager.TrafficClient") as MockTrafficClass:
        mock_instance = MockTrafficClass.return_value
        # Default mock responses
        mock_instance.get_historical_traffic_range.return_value = [
            {
                "timestamp": (datetime.now() - timedelta(days=i, hours=j)).isoformat(),
                "congestion": 0.5,
                "speed": 30.0,
                "incidents": 1,
            }
            for i in range(60)
            for j in range(5)
        ]
        mock_instance.get_current_traffic.return_value = {
            "timestamp": datetime.now().isoformat(),
            "congestion": 0.7,
            "speed": 25.0,
            "incidents": 2,
        }
        yield mock_instance


@pytest.fixture
def mock_geocoding_client_instance():
    """Mocks the GeocodingClient instance that DataManager uses."""
    with patch("city_vibe.data_manager.GeocodingClient") as MockGeocodingClass:
        mock_instance = MockGeocodingClass.return_value
        # Default coordinates
        mock_instance.get_coordinates.return_value = (10.0, 20.0)
        yield mock_instance


@pytest.fixture
def mock_database():
    """Mocks the database module functions."""
    with patch("city_vibe.data_manager.database") as mock_db:
        mock_db.get_or_create_city.return_value = 1
        mock_db.get_city_by_id.return_value = City(
            id=1,
            name="TestCity",
            latitude=10.0,
            longitude=20.0,
            is_confirmed=False,
            last_updated=datetime.now(),
        )
        # Default to no confirmed cities
        mock_db.get_confirmed_cities.return_value = []

        mock_db.insert_many_records.return_value = None
        mock_db.insert_record.return_value = None
        mock_db.update_city_confirmation_status.return_value = None
        mock_db.delete_forecast_data_for_city.return_value = None
        yield mock_db


# --- Tests for DataManager ---


def test_data_manager_init():
    """Test that DataManager initializes its clients."""
    with patch("city_vibe.data_manager.OpenMeteoClient") as MockOpenMeteo, patch(
        "city_vibe.data_manager.TrafficClient"
    ) as MockTraffic, patch("city_vibe.data_manager.GeocodingClient") as MockGeocoding:

        dm = DataManager()
        MockOpenMeteo.assert_called_once()
        MockTraffic.assert_called_once()
        MockGeocoding.assert_called_once()
        assert isinstance(dm.weather_client, MagicMock)
        assert isinstance(dm.traffic_client, MagicMock)
        assert isinstance(dm.geocoding_client, MagicMock)


def test_refresh_city_data_success(
    mock_open_meteo_client_instance,
    mock_traffic_client_instance,
    mock_database,
    mock_geocoding_client_instance,
):
    """Test successful refresh of city data (historical weather & traffic)."""
    dm = DataManager()
    city_name = "NewYork"
    city_id = 1
    mock_database.get_or_create_city.return_value = city_id
    mock_database.get_city_by_id.return_value = City(
        id=city_id,
        name=city_name,
        latitude=40.0,
        longitude=-70.0,
        is_confirmed=False,
        last_updated=datetime.now(),
    )

    # Mock datetime.now()
    mock_updated_at = datetime(2023, 1, 1, 12, 0, 0)
    with patch("city_vibe.data_manager.datetime") as mock_dt:
        mock_dt.now.return_value = mock_updated_at
        result = dm.refresh_city_data(city_name)

    assert result == city_id

    mock_database.get_or_create_city.assert_called_once_with(city_name)
    mock_database.get_city_by_id.assert_called_once_with(city_id)

    mock_open_meteo_client_instance.get_historical_weather_range.assert_called_once()
    assert (
        mock_open_meteo_client_instance.get_historical_weather_range.call_args[0][0]
        == 40.0
    )  # Latitude

    mock_traffic_client_instance.get_historical_traffic_range.assert_called_once()
    assert (
        mock_traffic_client_instance.get_historical_traffic_range.call_args[0][0]
        == city_name
    )

    assert (
        mock_database.insert_many_records.call_count == 2
    )  # Once for weather, once for traffic
    assert mock_database.insert_many_records.call_args_list[0][0][0] == "weather_data"
    assert mock_database.insert_many_records.call_args_list[1][0][0] == "traffic_data"

    mock_database.update_city_confirmation_status.assert_called_once_with(
        city_id, True, updated_at=mock_updated_at
    )


def test_refresh_city_data_geocoding_failure(
    mock_database, mock_geocoding_client_instance
):
    """Test refresh_city_data when geocoding fails."""
    dm = DataManager()
    city_name = "NonExistentCity"
    mock_database.get_or_create_city.side_effect = ValueError(
        "Coordinates required for city..."
    )

    result = dm.refresh_city_data(city_name)
    assert result is None
    # Verify that geocoding error prevents further data fetching/storage
    mock_database.get_or_create_city.assert_called_once_with(city_name)
    # get_or_create_city is mocked to fail before it
    mock_geocoding_client_instance.get_coordinates.assert_not_called()
    mock_database.update_city_confirmation_status.assert_not_called()


def test_get_city_forecast_success(mock_open_meteo_client_instance, mock_database):
    """Test successful retrieval and storage of 7-day forecast."""
    dm = DataManager()
    city_name = "ForecastCity"
    city_id = 2
    mock_database.get_or_create_city.return_value = city_id
    mock_database.get_city_by_id.return_value = City(
        id=city_id,
        name=city_name,
        latitude=30.0,
        longitude=30.0,
        is_confirmed=True,
        last_updated=datetime.now(),
    )
    # Mock datetime.now().date()
    mock_today_date = datetime.now().date()
    # Mock data for get_forecast_daily to return date strings
    mock_open_meteo_client_instance.get_forecast_daily.return_value = {
        "days": [
            {
                "date": (mock_today_date + timedelta(days=i)).isoformat(),
                "description": f"desc_{i}",
                "temp_max": 20.0 + i,
                "temp_min": 10.0 + i,
                "feels_like_max": 18.0 + i,
                "feels_like_min": 8.0 + i,
                "precipitation_mm": 0.0,
                "precipitation_chance": 0.0,
                "wind_speed_max": 10.0,
            }
            for i in range(7)
        ]
    }

    forecast_results = dm.get_city_forecast(city_name)
    assert forecast_results is not None
    assert len(forecast_results) == 7

    mock_database.get_or_create_city.assert_called_once_with(city_name)
    mock_open_meteo_client_instance.get_forecast_daily.assert_called_once_with(
        30.0, 30.0, days=7
    )
    mock_database.insert_many_records.assert_called_once()
    assert mock_database.insert_many_records.call_args[0][0] == "forecast_data"
    mock_database.delete_forecast_data_for_city.assert_called_once_with(
        city_id
    )  # Should be called once


def test_refresh_all_confirmed_cities_current_data_no_cities(mock_database):
    """Test when there are no confirmed cities."""
    dm = DataManager()
    mock_database.get_confirmed_cities.return_value = []

    dm.refresh_all_confirmed_cities_current_data()
    mock_database.get_confirmed_cities.assert_called_once()
    mock_database.insert_record.assert_not_called()


def test_refresh_all_confirmed_cities_current_data_with_cities(
    mock_open_meteo_client_instance, mock_traffic_client_instance, mock_database
):
    """Test refresh current data for confirmed cities."""
    dm = DataManager()
    city1 = City(
        id=1,
        name="City1",
        latitude=10.0,
        longitude=10.0,
        is_confirmed=True,
        last_updated=datetime.now(),
    )
    city2 = City(
        id=2,
        name="City2",
        latitude=20.0,
        longitude=20.0,
        is_confirmed=True,
        last_updated=datetime.now(),
    )
    mock_database.get_confirmed_cities.return_value = [city1, city2]

    dm.refresh_all_confirmed_cities_current_data()

    mock_database.get_confirmed_cities.assert_called_once()

    assert mock_open_meteo_client_instance.get_current_weather.call_count == 2
    mock_open_meteo_client_instance.get_current_weather.assert_any_call(
        city1.latitude, city1.longitude
    )
    mock_open_meteo_client_instance.get_current_weather.assert_any_call(
        city2.latitude, city2.longitude
    )

    assert mock_traffic_client_instance.get_current_traffic.call_count == 2
    mock_traffic_client_instance.get_current_traffic.assert_any_call(city1.name)
    mock_traffic_client_instance.get_current_traffic.assert_any_call(city2.name)

    assert mock_database.insert_record.call_count == 4  # 2 weather, 2 traffic
    assert mock_database.insert_record.call_args_list[0][0][0] == "weather_data"
    assert mock_database.insert_record.call_args_list[1][0][0] == "traffic_data"
    assert mock_database.insert_record.call_args_list[2][0][0] == "weather_data"
    assert mock_database.insert_record.call_args_list[3][0][0] == "traffic_data"
