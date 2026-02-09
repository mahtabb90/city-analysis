import sqlite3
import logging
from datetime import datetime, timedelta

from typing import List, Optional, Any, Iterable
from pydantic import BaseModel

from city_vibe.config import DATABASE_PATH
from city_vibe.domain.models import WeatherRecord
from city_vibe.domain.models import TrafficRecord
from city_vibe.domain.models import City  # noqa: F401
from city_vibe.domain.models import ForecastRecord
from city_vibe.domain.models import AnalysisResult  # noqa: F401
from city_vibe.clients.geocoding.geocoding_client import GeocodingClient

_geocoding_client = GeocodingClient()


def get_connection():
    """Returns a connection to the SQLite database with Row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _execute(
    query: str,
    params: Iterable = (),
    commit: bool = False,
    fetch: str = None,
    many: bool = False,
) -> Any:
    """
    Shared helper to execute SQL queries.
    fetch: 'all', 'one', or None
    many: boolean to use executemany
    """
    logger = logging.getLogger(__name__)
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if many:
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params)

            if commit:
                conn.commit()

            if fetch == "all":
                return cursor.fetchall()
            if fetch == "one":
                return cursor.fetchone()

            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error during query [{query[:50]}...]: {e}")
        raise


def init_db():
    """Initializes the database schema if it doesn't exist."""
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing database at {DATABASE_PATH}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                latitude REAL,
                longitude REAL,
                is_confirmed BOOLEAN DEFAULT FALSE,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL,
                wind_speed REAL,
                precipitation REAL,
                weather_code INTEGER,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            );
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                congestion_level REAL,
                speed REAL,
                incidents INTEGER,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            );
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                status TEXT,
                metrics_json TEXT,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            );
            CREATE TABLE IF NOT EXISTS forecast_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                date DATE NOT NULL,
                description TEXT,
                temp_max REAL,
                temp_min REAL,
                feels_like_max REAL,
                feels_like_min REAL,
                precipitation_mm REAL,
                precipitation_chance REAL,
                wind_speed_max REAL,
                forecast_retrieval_time DATETIME NOT NULL,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            );
        """)
    logger.info("Database initialization complete.")


def db_exists():
    """Checks if the database file exists."""

    return DATABASE_PATH.exists()


# --- CRUD Functions ---


def insert_record(table_name: str, record: BaseModel) -> int:
    """Inserts a single record using the model's fields."""

    data = record.model_dump(exclude={"id"})
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
    return _execute(query, list(data.values()), commit=True)


def insert_many_records(table_name: str, records: List[BaseModel]):
    """Inserts multiple records in a single transaction."""

    if not records:
        return
    data_list = [r.model_dump(exclude={"id"}) for r in records]
    cols = ", ".join(data_list[0].keys())
    placeholders = ", ".join(["?" for _ in data_list[0]])
    query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
    _execute(query, [list(d.values()) for d in data_list], commit=True, many=True)


def get_or_create_city(
    name: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> int:
    """
    Retrieves a city ID or creates it.
    Automatically fetches latitude and longitude if not provided.
    """
    logger = logging.getLogger(__name__)
    row = _execute(
        "SELECT id, latitude, longitude, is_confirmed " "FROM cities WHERE name = ?",
        (name,),
        fetch="one",
    )
    if row:
        city_id = row["id"]
        # Update if coordinates are missing or different
        if (row["latitude"] is None and row["longitude"] is None) or (
            latitude is not None
            and longitude is not None
            and (row["latitude"] != latitude or row["longitude"] != longitude)
        ):
            if latitude is None or longitude is None:
                coords = _geocoding_client.get_coordinates(name)
                if coords:
                    latitude, longitude = coords
                else:
                    logger.warning(
                        f"No coordinates for city '{name}'. Skipping update."
                    )
                    return city_id

            if latitude is not None and longitude is not None:
                update_city_metadata(city_id, latitude, longitude)
                logger.info(
                    f"Updated coordinates for '{name}': ({latitude}, {longitude})"
                )
        return city_id

    # If city does not exist, fetch coordinates if not provided
    if latitude is None or longitude is None:
        coords = _geocoding_client.get_coordinates(name)
        if coords:
            latitude, longitude = coords
        else:
            logger.error(
                f"No coordinates for new city '{name}'. "
                "Cannot create city without coordinates."
            )
            raise ValueError(f"Coordinates required for city '{name}'.")

    logger.info(
        f"Creating new city '{name}' with coordinates: ({latitude}, {longitude})"
    )
    return _execute(
        "INSERT INTO cities (name, latitude, longitude) VALUES (?, ?, ?)",
        (name, latitude, longitude),
        commit=True,
    )


def fetch_weather_history(city_name: str, days: int = 7) -> List[WeatherRecord]:
    """Fetches weather records for a city."""

    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    query = """
        SELECT w.* FROM weather_data w
        JOIN cities c ON w.city_id = c.id
        WHERE c.name = ? AND w.timestamp >= ?
        ORDER BY w.timestamp DESC
    """
    rows = _execute(query, (city_name, since), fetch="all")
    return [WeatherRecord.model_validate(dict(row)) for row in rows]


def fetch_traffic_history(city_name: str, days: int = 7) -> List[TrafficRecord]:
    """Fetches traffic records for a city."""

    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    query = """
        SELECT t.* FROM traffic_data t
        JOIN cities c ON t.city_id = c.id
        WHERE c.name = ? AND t.timestamp >= ?
        ORDER BY t.timestamp DESC
    """
    rows = _execute(query, (city_name, since), fetch="all")
    return [TrafficRecord.model_validate(dict(row)) for row in rows]


def update_city_metadata(city_id: int, latitude: float, longitude: float):
    """Updates city coordinates and last_updated timestamp."""
    _execute(
        "UPDATE cities SET latitude = ?, longitude = ?, "
        "last_updated = CURRENT_TIMESTAMP WHERE id = ?",
        (latitude, longitude, city_id),
        commit=True,
    )


def update_city_confirmation_status(
    city_id: int, is_confirmed: bool, updated_at: Optional[datetime] = None
):
    """Updates confirmation status and last_updated timestamp."""
    timestamp_param = (
        updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "CURRENT_TIMESTAMP"
    )
    query = "UPDATE cities SET is_confirmed = ?, last_updated = ? WHERE id = ?"
    params = (is_confirmed, timestamp_param, city_id)

    if updated_at is None:
        query = (
            "UPDATE cities SET is_confirmed = ?, "
            "last_updated = CURRENT_TIMESTAMP WHERE id = ?"
        )
        params = (is_confirmed, city_id)

    _execute(query, params, commit=True)


def get_confirmed_cities() -> List[City]:
    """Fetches all cities that are marked as confirmed."""
    rows = _execute(
        "SELECT id, name, latitude, longitude, is_confirmed, last_updated "
        "FROM cities WHERE is_confirmed = TRUE",
        fetch="all",
    )
    confirmed_cities = []
    for row in rows:
        city_data = dict(row)
        if city_data["last_updated"]:
            city_data["last_updated"] = datetime.fromisoformat(
                city_data["last_updated"]
            )
        confirmed_cities.append(City.model_validate(city_data))
    return confirmed_cities


def get_city_by_id(city_id: int) -> Optional[City]:
    """Fetches a city record by its ID."""
    row = _execute(
        "SELECT id, name, latitude, longitude, is_confirmed, last_updated FROM cities WHERE id = ?",
        (city_id,),
        fetch="one",
    )
    if row:
        city_data = dict(row)
        if city_data["last_updated"]:  # Convert if not None
            city_data["last_updated"] = datetime.fromisoformat(
                city_data["last_updated"]
            )
        return City.model_validate(city_data)
    return None


def fetch_latest_current_vibe_analysis(city_id: int) -> Optional[AnalysisResult]:
    """
    Fetches the latest non-forecast overall vibe analysis for a specific city.
    Excludes categories prefixed with 'Forecast_'.
    """
    query = """
        SELECT * FROM analysis_results
        WHERE city_id = ? AND category NOT LIKE 'Forecast_%%'
        ORDER BY timestamp DESC
        LIMIT 1
    """
    row = _execute(query, (city_id,), fetch="one")
    if row:
        return AnalysisResult.model_validate(dict(row))
    return None


def fetch_all_forecast_weather_for_city(city_id: int) -> List[ForecastRecord]:
    """
    Fetches all unique forecast weather records for a specific city, ordered by date.
    Only retrieves the latest forecast for each date.
    """
    query = """
        SELECT T1.*
        FROM forecast_data AS T1
        INNER JOIN (
            SELECT date, MAX(forecast_retrieval_time) AS MaxRetrievalTime
            FROM forecast_data
            WHERE city_id = ?
            GROUP BY date
        ) AS T2
        ON T1.date = T2.date AND T1.forecast_retrieval_time = T2.MaxRetrievalTime
        WHERE T1.city_id = ?
        ORDER BY T1.date ASC
    """
    rows = _execute(query, (city_id, city_id), fetch="all")
    return [ForecastRecord.model_validate(dict(row)) for row in rows]


def fetch_all_forecast_vibe_for_city(city_id: int) -> List[AnalysisResult]:
    """
    Fetches all forecast vibe analyses for a specific city, ordered by timestamp (date).
    Only retrieves the latest forecast vibe for each date.
    """
    query = """
        SELECT T1.*
        FROM analysis_results AS T1
        INNER JOIN (
            SELECT
                strftime('%Y-%m-%d', timestamp) AS forecast_date,
                MAX(timestamp) AS MaxTimestamp
            FROM analysis_results
            WHERE city_id = ? AND category LIKE 'Forecast_%%'
            GROUP BY forecast_date
        ) AS T2
        ON strftime('%Y-%m-%d', T1.timestamp) = T2.forecast_date AND T1.timestamp = T2.MaxTimestamp
        WHERE T1.city_id = ? AND T1.category LIKE 'Forecast_%%'
        ORDER BY T1.timestamp ASC
    """
    rows = _execute(query, (city_id, city_id), fetch="all")
    return [AnalysisResult.model_validate(dict(row)) for row in rows]


def fetch_forecast_data(
    city_id: int, target_date: datetime.date
) -> Optional[ForecastRecord]:
    """Fetches the latest forecast record for a specific city and date."""
    query = """
        SELECT * FROM forecast_data
        WHERE city_id = ? AND date = ?
        ORDER BY forecast_retrieval_time DESC
        LIMIT 1
    """
    # Convert date object to string for comparison with DATE column
    date_str = target_date.strftime("%Y-%m-%d")
    row = _execute(query, (city_id, date_str), fetch="one")
    if row:
        return ForecastRecord.model_validate(dict(row))
    return None


def delete_forecast_data_for_city(city_id: int):
    """Deletes all forecast data for a specific city."""
    _execute("DELETE FROM forecast_data WHERE city_id = ?", (city_id,), commit=True)


def delete_old_records(table_name: str, days: int):
    """Prunes old data from the specified table."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    _execute(f"DELETE FROM {table_name} WHERE timestamp < ?", (cutoff,), commit=True)


def clear_all_data():
    """Deletes all records from all data tables."""
    logger = logging.getLogger(__name__)
    logger.info("Clearing all data from database tables...")
    _execute("DELETE FROM analysis_results", commit=True)
    _execute("DELETE FROM traffic_data", commit=True)
    _execute("DELETE FROM weather_data", commit=True)
    _execute("DELETE FROM cities", commit=True)
    logger.info("All data cleared.")
