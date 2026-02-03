import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from city_vibe.database import (
    init_db,
    insert_record,
    insert_many_records,
    fetch_weather_history,
    fetch_traffic_history,
    get_or_create_city,
    update_city_metadata,
    delete_old_records,
    get_connection,
)
from city_vibe.domain.models import City, WeatherRecord, TrafficRecord


@pytest.fixture
def test_db(tmp_path):
    """Provides a clean temporary database for each test."""
    db_path = tmp_path / "crud_combined_test.db"
    with patch("city_vibe.database.DATABASE_PATH", db_path):
        init_db()
        yield db_path


# --- City Tests ---


def test_get_or_create_city(test_db):
    """Verifies city retrieval and creation logic."""
    city_id1 = get_or_create_city("Stockholm", 59.3, 18.0)
    assert city_id1 is not None

    # Get existing
    city_id2 = get_or_create_city("Stockholm")
    assert city_id1 == city_id2

    # Create another
    city_id3 = get_or_create_city("Oslo")
    assert city_id1 != city_id3


def test_update_metadata(test_db):
    """Verifies the update functionality for city metadata."""
    city_id = insert_record("cities", City(name="Metropolis"))
    update_city_metadata(city_id, 40.7, -74.0)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT latitude FROM cities WHERE id = ?", (city_id,)
        ).fetchone()
        assert row["latitude"] == 40.7


# --- Weather Tests ---


def test_insert_and_fetch_weather_history(test_db):
    """Verifies basic insert and fetch functionality for weather."""
    city_id = get_or_create_city("Testville")
    weather = WeatherRecord(city_id=city_id, temperature=22.5, humidity=45.0)
    insert_record("weather_data", weather)

    history = fetch_weather_history("Testville", days=1)
    assert len(history) == 1
    assert history[0].temperature == 22.5


# --- Traffic Tests ---


def test_insert_many_traffic(test_db):
    """Verifies bulk insert and history retrieval for traffic data."""
    city_id = get_or_create_city("Berlin")
    base_time = datetime.now()
    records = [
        TrafficRecord(
            city_id=city_id,
            timestamp=base_time - timedelta(minutes=10),
            congestion_level=0.1,
            speed=50.0,
            incidents=0,
        ),
        TrafficRecord(
            city_id=city_id,
            timestamp=base_time - timedelta(minutes=5),
            congestion_level=0.5,
            speed=20.0,
            incidents=1,
        ),
        TrafficRecord(
            city_id=city_id,
            timestamp=base_time,
            congestion_level=0.8,
            speed=5.0,
            incidents=3,
        ),
    ]

    insert_many_records("traffic_data", records)

    history = fetch_traffic_history("Berlin")
    assert len(history) == 3
    assert history[0].speed == 5.0  # Latest first
    assert history[2].speed == 50.0


# --- Deletion & Maintenance ---


def test_delete_old_records(test_db):
    """Verifies that old records are correctly removed."""
    city_id = get_or_create_city("Paris")
    old_time = datetime.now() - timedelta(days=10)
    record = TrafficRecord(city_id=city_id, timestamp=old_time, congestion_level=0.1)
    insert_many_records("traffic_data", [record])

    # Delete records older than 5 days
    delete_old_records("traffic_data", days=5)

    history = fetch_traffic_history("Paris")
    assert len(history) == 0


# --- Security ---


def test_sql_injection_protection(test_db):
    """Verifies protection against SQL injection in inserts."""
    dangerous_name = "'; DROP TABLE cities; --"
    insert_record("cities", City(name=dangerous_name))

    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cities'"
        )
        assert cursor.fetchone() is not None
