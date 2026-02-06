import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from city_vibe import database
from city_vibe.domain.models import City, ForecastRecord


@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a temporary database path."""
    db_path = tmp_path / "test_city_analysis.db"
    with patch("city_vibe.database.DATABASE_PATH", db_path):
        database.init_db()
        yield db_path


@pytest.fixture
def sample_city_data():
    """Returns sample data for a city."""
    return {"name": "TestCity", "latitude": 10.0, "longitude": 20.0}


@pytest.fixture
def mock_geocoding_success():
    """Mocks the GeocodingClient to return successful coordinates."""
    with patch(
        "city_vibe.database._geocoding_client.get_coordinates",
        return_value=(10.0, 20.0),
    ) as mock_method:
        yield mock_method


# --- Initialization Tests ---


def test_init_db_creates_file(tmp_path):
    """Test that init_db actually creates the database file."""
    db_path = tmp_path / "new_test_db.db"
    with patch("city_vibe.database.DATABASE_PATH", db_path):
        assert not db_path.exists()
        database.init_db()
        assert db_path.exists()


def test_db_exists(tmp_path):
    """Test the db_exists helper function."""
    db_path = tmp_path / "exists_test.db"
    with patch("city_vibe.database.DATABASE_PATH", db_path):
        assert not database.db_exists()
        db_path.touch()
        assert database.db_exists()


def test_init_db_creates_tables(temp_db):
    """Test that all expected tables are created during initialization."""
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "cities",
            "weather_data",
            "traffic_data",
            "analysis_results",
            "forecast_data",
        }
        for table in expected_tables:
            assert table in tables


def test_init_db_idempotent(temp_db):
    """Test that calling init_db multiple times doesn't cause errors."""
    database.init_db()
    database.init_db()
    assert temp_db.exists()


def test_get_connection(temp_db):
    """Test that get_connection returns a valid sqlite3 connection."""
    conn = database.get_connection()
    try:
        assert isinstance(conn, sqlite3.Connection)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
    finally:
        conn.close()


# --- Schema and Enhancement Tests ---


def test_city_table_schema(temp_db):
    """Verify cities table has all expected columns."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cities)")
    cols = {row[1] for row in cursor.fetchall()}
    expected_cols = {
        "id",
        "name",
        "latitude",
        "longitude",
        "is_confirmed",
        "last_updated",
    }
    assert expected_cols.issubset(cols)
    conn.close()


def test_get_or_create_city_metadata(temp_db, mock_geocoding_success):
    """Test city creation with default values and timestamps."""
    time_before = datetime.utcnow()
    city_id = database.get_or_create_city("NewDefaultCity")
    city = database.get_city_by_id(city_id)
    time_after = datetime.utcnow()

    assert city.name == "NewDefaultCity"
    assert not city.is_confirmed
    assert isinstance(city.last_updated, datetime)
    assert (
        time_before.replace(microsecond=0)
        <= city.last_updated.replace(microsecond=0)
        <= time_after.replace(microsecond=0)
    )


def test_update_city_confirmation_status(temp_db, sample_city_data):
    """Test updating confirmation status and timestamps."""
    city_id = database.get_or_create_city(
        sample_city_data["name"],
        sample_city_data["latitude"],
        sample_city_data["longitude"],
    )

    # Initial state
    city = database.get_city_by_id(city_id)
    assert not city.is_confirmed

    # Update with explicit timestamp
    update_time = datetime.now() + timedelta(seconds=1)
    database.update_city_confirmation_status(city_id, True, updated_at=update_time)

    city = database.get_city_by_id(city_id)
    assert city.is_confirmed
    assert city.last_updated.replace(microsecond=0) == update_time.replace(
        microsecond=0
    )


def test_get_confirmed_cities(temp_db, mock_geocoding_success):
    """Test retrieving only confirmed cities."""
    c1 = database.get_or_create_city("CityA")
    database.get_or_create_city("CityB")
    c3 = database.get_or_create_city("CityC")

    database.update_city_confirmation_status(c1, True)
    database.update_city_confirmation_status(c3, True)

    confirmed = database.get_confirmed_cities()
    assert len(confirmed) == 2
    assert {c.name for c in confirmed} == {"CityA", "CityC"}
    assert all(c.is_confirmed for c in confirmed)


def test_delete_forecast_data(temp_db, mock_geocoding_success):
    """Test deleting forecast data for a specific city."""
    city_id = database.get_or_create_city("CityX", 10.0, 10.0)

    forecast = [
        ForecastRecord(
            city_id=city_id,
            date=datetime.now().date() + timedelta(days=i),
            description=f"desc_{i}",
            temp_max=20.0,
            temp_min=10.0,
            feels_like_max=18.0,
            feels_like_min=8.0,
            precipitation_mm=0.0,
            precipitation_chance=0.0,
            wind_speed_max=10.0,
            forecast_retrieval_time=datetime.now(),
        )
        for i in range(3)
    ]
    database.insert_many_records("forecast_data", forecast)

    # Verify insertion
    conn = database.get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM forecast_data WHERE city_id = ?", (city_id,)
    ).fetchone()[0]
    assert count == 3

    # Delete and verify
    database.delete_forecast_data_for_city(city_id)
    count = conn.execute(
        "SELECT COUNT(*) FROM forecast_data WHERE city_id = ?", (city_id,)
    ).fetchone()[0]
    assert count == 0
    conn.close()