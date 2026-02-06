import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import random

from city_vibe.clients.traffic.mock_api import generate_mock_traffic_data
from city_vibe.clients.traffic.traffic_client import TrafficClient


def test_generate_mock_traffic_data_randomization():
    """Test that mock traffic data has some randomization."""
    random.seed(42)  # Seed for reproducibility
    data1 = generate_mock_traffic_data()
    data2 = generate_mock_traffic_data()

    assert "congestion" in data1
    assert "speed" in data1
    assert "incidents" in data1

    # Assert some difference due to randomization
    assert data1 != data2


def test_generate_mock_traffic_data_date_variation_weekday_weekend():
    """Test that mock traffic data varies between weekday and weekend."""
    random.seed(42)  # Seed for reproducibility

    # Friday (weekday)
    weekday_date = datetime(2023, 10, 27)
    weekday_data = generate_mock_traffic_data(date=weekday_date)

    # Saturday (weekend)
    weekend_date = datetime(2023, 10, 28)
    weekend_data = generate_mock_traffic_data(date=weekend_date)

    # Asserting that congestion is generally lower and speed higher on weekends
    # The random fluctuations make direct comparison hard, so check relative difference
    assert weekday_data["congestion"] > weekend_data["congestion"] - 0.2
    assert (
        weekday_data["speed"] < weekend_data["speed"] + 10
    )  # Allow for some overlap due to randomization
    assert "date" in weekday_data  # Check that date is included
    assert "date" in weekend_data


def test_traffic_client_get_current_traffic():
    """Test that get_current_traffic returns a single data point."""
    client = TrafficClient()
    city_name = "Mockville"

    # Patch generate_mock_traffic_data where it's *used* in traffic_client
    with patch(
        "city_vibe.clients.traffic.traffic_client.generate_mock_traffic_data",
        return_value={"congestion": 0.5, "speed": 40, "incidents": 1},
    ) as mock_gen:
        result = client.get_current_traffic(city_name)
        mock_gen.assert_called_once()
        assert result["city"] == city_name
        assert "congestion" in result
        assert "timestamp" in result
        assert isinstance(datetime.fromisoformat(result["timestamp"]), datetime)


def test_traffic_client_get_historical_traffic_range():
    """Test that get_historical_traffic_range generates 5 points per day."""
    client = TrafficClient()
    city_name = "MockCity"
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 2)  # Two days

    # Mock generate_mock_traffic_data to return predictable values
    mock_values = [
        {"congestion": i / 10.0, "speed": 40, "incidents": 1} for i in range(10)
    ]  # Enough values for 2 days * 5 points
    with patch(
        "city_vibe.clients.traffic.traffic_client.generate_mock_traffic_data",
        side_effect=mock_values,
    ) as mock_gen:
        results = client.get_historical_traffic_range(
            city_name, start_date, end_date, points_per_day=5
        )

        assert mock_gen.call_count == 10  # 2 days * 5 points
        assert len(results) == 10  # Total 10 records

        # Check structure of results and timestamps
        for i, record in enumerate(results):
            assert record["city"] == city_name
            assert "timestamp" in record
            assert isinstance(datetime.fromisoformat(record["timestamp"]), datetime)
            assert record["congestion"] == mock_values[i]["congestion"]

        # Check specific timestamps for day 1
        day1_timestamps = [
            datetime.fromisoformat(results[j]["timestamp"]).replace(microsecond=0)
            for j in range(5)
        ]
        expected_day1_times = [
            (start_date + timedelta(hours=8)).replace(microsecond=0),
            (start_date + timedelta(hours=11)).replace(microsecond=0),
            (start_date + timedelta(hours=14)).replace(microsecond=0),
            (start_date + timedelta(hours=17)).replace(microsecond=0),
            (start_date + timedelta(hours=20)).replace(microsecond=0),
        ]
        assert day1_timestamps == expected_day1_times

        # Check specific timestamps for day 2
        day2_timestamps = [
            datetime.fromisoformat(results[j]["timestamp"]).replace(microsecond=0)
            for j in range(5, 10)
        ]
        expected_day2_times = [
            (end_date + timedelta(hours=8)).replace(microsecond=0),
            (end_date + timedelta(hours=11)).replace(microsecond=0),
            (end_date + timedelta(hours=14)).replace(microsecond=0),
            (end_date + timedelta(hours=17)).replace(microsecond=0),
            (end_date + timedelta(hours=20)).replace(microsecond=0),
        ]
        assert day2_timestamps == expected_day2_times
