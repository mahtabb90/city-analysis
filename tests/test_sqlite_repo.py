from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from city_vibe.domain.models import AnalysisResult, WeatherRecord
from city_vibe.storage import SQLiteRepo


def init_db_at_path(db_path: Path) -> None:
    """Initialize schema in a temporary SQLite file (CI-safe)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()
        cur.executescript(
            """
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
            """
        )
        conn.commit()


def make_repo(tmp_path: Path) -> SQLiteRepo:
    db_path = tmp_path / "test.db"
    init_db_at_path(db_path)
    return SQLiteRepo(db_path=db_path)


def test_get_or_create_city(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    city = repo.get_or_create_city("Stockholm", latitude=59.3, longitude=18.0)
    assert city.id is not None
    assert city.name == "Stockholm"

    # Calling again should return same city (not create new)
    city2 = repo.get_or_create_city("Stockholm")
    assert city2.id == city.id


def test_insert_and_fetch_weather(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    city = repo.get_or_create_city("Stockholm")

    record = WeatherRecord(
        city_id=city.id,
        timestamp=datetime.utcnow(),
        temperature=5.0,
        humidity=70.0,
    )

    saved = repo.insert_weather_record(record)
    assert saved.id is not None

    records = repo.get_recent_weather(city.id, limit=5)
    assert len(records) == 1
    assert records[0].city_id == city.id
    assert records[0].temperature == 5.0


def test_insert_and_fetch_latest_analysis(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    city = repo.get_or_create_city("Stockholm")

    metrics = {"avg": 5.0, "trend": 0.2, "variability": 0.1}

    result = AnalysisResult(
        city_id=city.id,
        timestamp=datetime.utcnow(),
        category="weather",
        status="STABLE",
        metrics_json=json.dumps(metrics),
    )

    saved = repo.insert_analysis_result(result)
    assert saved.id is not None

    latest = repo.get_latest_analysis(city.id)
    assert latest is not None
    assert latest.city_id == city.id
    assert latest.status == "STABLE"
