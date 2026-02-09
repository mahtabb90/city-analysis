import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from city_vibe.analysis.vibe_algorithm import (
    is_payday_weekend,
    is_bad_weather,
    is_good_outdoor_weather,
    calculate_vibe,
    VibeCategory,
    CityStatus,
)
from city_vibe.analysis.metrics import MetricSummary
from city_vibe.domain.models import WeatherRecord, TrafficRecord, AnalysisResult


def test_is_payday_weekend():
    # 25th is a Friday (4) in July 2025
    assert is_payday_weekend(datetime(2025, 7, 25)) is True
    # 25th is a Saturday (5) in October 2025
    assert is_payday_weekend(datetime(2025, 10, 25)) is True
    # 25th is a Sunday (6) in May 2025
    assert is_payday_weekend(datetime(2025, 5, 25)) is True
    # 25th is a Monday (0) in August 2025
    assert is_payday_weekend(datetime(2025, 8, 25)) is False
    # Not the 25th
    assert is_payday_weekend(datetime(2025, 7, 24)) is False


def test_is_bad_weather():
    # is_bad_weather(temp_avg, humidity_avg, status, precip_sum)
    temp_cold = 2.0
    temp_warm = 15.0
    hum_high = 95.0
    hum_low = 50.0

    # Cold weather
    assert is_bad_weather(temp_cold, hum_low, CityStatus.STABLE, 0.0) is True
    # High humidity
    assert is_bad_weather(temp_warm, hum_high, CityStatus.STABLE, 0.0) is True
    # Unstable weather
    assert is_bad_weather(temp_warm, hum_low, CityStatus.UNSTABLE, 0.0) is True
    # Significant precipitation
    assert is_bad_weather(temp_warm, hum_low, CityStatus.STABLE, 5.0) is True
    # Good weather
    assert is_bad_weather(temp_warm, hum_low, CityStatus.STABLE, 0.0) is False


def test_is_good_outdoor_weather():
    # is_good_outdoor_weather(temp_avg, humidity_avg, status)
    temp_mild = 15.0
    temp_cold = 2.0
    hum_low = 50.0
    hum_high = 95.0

    # Mild temp, low humidity, stable
    assert is_good_outdoor_weather(temp_mild, hum_low, CityStatus.STABLE) is True
    # Improving status
    assert is_good_outdoor_weather(temp_mild, hum_low, CityStatus.IMPROVING) is True
    # Cold temp
    assert is_good_outdoor_weather(temp_cold, hum_low, CityStatus.STABLE) is False
    # High humidity
    assert is_good_outdoor_weather(temp_mild, hum_high, CityStatus.STABLE) is False
    # Declining status
    assert is_good_outdoor_weather(temp_mild, hum_low, CityStatus.DECLINING) is False


@patch("city_vibe.analysis.vibe_algorithm.get_or_create_city")
@patch("city_vibe.analysis.vibe_algorithm.fetch_weather_history")
@patch("city_vibe.analysis.vibe_algorithm.fetch_traffic_history")
@patch("city_vibe.analysis.vibe_algorithm.insert_record")
def test_calculate_vibe_insufficient_data(
    mock_insert, mock_traffic, mock_weather, mock_city
):
    mock_city.return_value = 1
    mock_weather.return_value = []
    mock_traffic.return_value = []

    result = calculate_vibe("Stockholm", 7)
    assert result.category == VibeCategory.NEUTRAL.value
    assert "Insufficient data" in result.status


@patch("city_vibe.analysis.vibe_algorithm.get_or_create_city")
@patch("city_vibe.analysis.vibe_algorithm.fetch_weather_history")
@patch("city_vibe.analysis.vibe_algorithm.fetch_traffic_history")
@patch("city_vibe.analysis.vibe_algorithm.insert_record")
@patch("city_vibe.analysis.vibe_algorithm.datetime")
def test_calculate_vibe_cozy_at_home(
    mock_datetime, mock_insert, mock_traffic, mock_weather, mock_city
):
    mock_city.return_value = 1
    # Friday, 20th Feb 2026, 18:00 (Friday evening)
    mock_datetime.now.return_value = datetime(2026, 2, 20, 18, 0)

    # Mock data to trigger bad weather
    mock_weather.return_value = [
        WeatherRecord(
            id=1,
            city_id=1,
            timestamp=datetime.now(),
            temperature=2.0,
            humidity=95.0,
            precipitation=5.0,
            weather_code=0,
        )
    ]
    mock_traffic.return_value = [
        TrafficRecord(
            id=1,
            city_id=1,
            timestamp=datetime.now(),
            congestion_level=0.5,
            speed=50,
            incidents=0,
        )
    ]

    result = calculate_vibe("Stockholm", 7)
    assert result.category == VibeCategory.COZY_AT_HOME.value
    assert "cozy night in" in result.status


@patch("city_vibe.analysis.vibe_algorithm.get_or_create_city")
@patch("city_vibe.analysis.vibe_algorithm.fetch_weather_history")
@patch("city_vibe.analysis.vibe_algorithm.fetch_traffic_history")
@patch("city_vibe.analysis.vibe_algorithm.insert_record")
@patch("city_vibe.analysis.vibe_algorithm.datetime")
def test_calculate_vibe_people_out(
    mock_datetime, mock_insert, mock_traffic, mock_weather, mock_city
):
    mock_city.return_value = 1
    # Wednesday, 11th Feb 2026, 12:00 (Not payday, but good weather)
    mock_datetime.now.return_value = datetime(2026, 2, 11, 12, 0)

    # Mock data to trigger good outdoor weather
    mock_weather.return_value = [
        WeatherRecord(
            id=1,
            city_id=1,
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=40.0,
            precipitation=0.0,
            weather_code=0,
        )
    ]
    mock_traffic.return_value = [
        TrafficRecord(
            id=1,
            city_id=1,
            timestamp=datetime.now(),
            congestion_level=0.2,
            speed=60,
            incidents=0,
        )
    ]

    result = calculate_vibe("Stockholm", 7)
    assert result.category == VibeCategory.PEOPLE_OUT_ON_TOWN.value
    assert "streets are alive" in result.status
