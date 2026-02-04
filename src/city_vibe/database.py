import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any, Iterable
from pydantic import BaseModel
from city_vibe.config import DATABASE_PATH
from city_vibe.domain.models import WeatherRecord, TrafficRecord

logger = logging.getLogger(__name__)


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
    Shared helper to execute SQL queries and handle connection/errors in one place.
    fetch: 'all', 'one', or None
    many: boolean to use executemany
    """
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
    logger.info(f"Initializing database at {DATABASE_PATH}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                latitude REAL,
                longitude REAL
            );
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL,
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
    name: str, latitude: Optional[float] = None, longitude: Optional[float] = None
) -> int:
    """Retrieves a city ID or creates it."""

    row = _execute("SELECT id FROM cities WHERE name = ?", (name,), fetch="one")
    if row:
        return row["id"]
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
    """Updates city coordinates."""
    _execute(
        "UPDATE cities SET latitude = ?, longitude = ? WHERE id = ?",
        (latitude, longitude, city_id),
        commit=True,
    )


def delete_old_records(table_name: str, days: int):
    """Prunes old data from the specified table."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    _execute(f"DELETE FROM {table_name} WHERE timestamp < ?", (cutoff,), commit=True)
