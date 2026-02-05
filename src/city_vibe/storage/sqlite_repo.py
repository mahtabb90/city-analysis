from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from city_vibe.config import DATABASE_PATH
from city_vibe.domain.models import AnalysisResult, City, TrafficRecord, WeatherRecord


def _to_iso(dt: datetime) -> str:
    # Store timestamps in a consistent, parseable format
    return dt.replace(microsecond=0).isoformat(sep=" ")


def _from_iso(value: str) -> datetime:
    # SQLite returns TEXT; we store ISO "YYYY-MM-DD HH:MM:SS"
    return datetime.fromisoformat(value)


class SQLiteRepo:
    """
    Small repository layer for SQLite.

    - Keeps SQL out of CLI and other modules.
    - Returns domain dataclasses (City, WeatherRecord, TrafficRecord, AnalysisResult).
    - Supports dependency injection via db_path for CI-safe tests (tmp_path).
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path: Path = db_path or DATABASE_PATH

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        # Ensure foreign keys are enforced in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # -------------------------
    # Cities
    # -------------------------
    def get_city_by_name(self, name: str) -> City | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, latitude, longitude FROM cities WHERE name = ?",
                (name,),
            ).fetchone()

        if not row:
            return None

        return City(
            id=int(row["id"]),
            name=str(row["name"]),
            latitude=row["latitude"],
            longitude=row["longitude"],
        )

    def get_or_create_city(
        self,
        name: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> City:
        """
        Get existing city by name, otherwise insert it.
        If the city exists and lat/lon are provided (and missing), update them.
        """
        existing = self.get_city_by_name(name)
        if existing:
            # Optional: update missing lat/lon if provided
            needs_update = (
                (existing.latitude is None and latitude is not None)
                or (existing.longitude is None and longitude is not None)
            )
            if needs_update:
                new_lat = existing.latitude if existing.latitude is not None else latitude
                new_lon = existing.longitude if existing.longitude is not None else longitude

                with self._connect() as conn:
                    conn.execute(
                        "UPDATE cities SET latitude = ?, longitude = ? WHERE id = ?",
                        (new_lat, new_lon, existing.id),
                    )
                    conn.commit()

                return replace(existing, latitude=new_lat, longitude=new_lon)

            return existing

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO cities (name, latitude, longitude) VALUES (?, ?, ?)",
                (name, latitude, longitude),
            )
            conn.commit()
            city_id = int(cur.lastrowid)

        return City(id=city_id, name=name, latitude=latitude, longitude=longitude)

    def list_cities(self) -> list[City]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, latitude, longitude FROM cities ORDER BY name ASC"
            ).fetchall()

        return [
            City(
                id=int(r["id"]),
                name=str(r["name"]),
                latitude=r["latitude"],
                longitude=r["longitude"],
            )
            for r in rows
        ]

    # -------------------------
    # Weather
    # -------------------------
    def insert_weather_record(self, record: WeatherRecord) -> WeatherRecord:
        """
        Insert a weather record. Returns the record with assigned id.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO weather_data (city_id, timestamp, temperature, humidity)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record.city_id,
                    _to_iso(record.timestamp),
                    record.temperature,
                    record.humidity,
                ),
            )
            conn.commit()
            new_id = int(cur.lastrowid)

        return record.model_copy(update={"id": new_id})


    def insert_weather_records(self, records: Iterable[WeatherRecord]) -> list[WeatherRecord]:
        """
        Bulk insert convenience. Returns inserted records with ids.
        """
        inserted: list[WeatherRecord] = []
        for r in records:
            inserted.append(self.insert_weather_record(r))
        return inserted

    def get_recent_weather(self, city_id: int, limit: int = 30) -> list[WeatherRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, city_id, timestamp, temperature, humidity
                FROM weather_data
                WHERE city_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (city_id, limit),
            ).fetchall()

        # Return in chronological order (oldest -> newest) for plotting/metrics
        records = [
            WeatherRecord(
                id=int(r["id"]),
                city_id=int(r["city_id"]),
                timestamp=_from_iso(str(r["timestamp"])),
                temperature=float(r["temperature"]),
                humidity=float(r["humidity"]) if r["humidity"] is not None else 0.0,
            )
            for r in rows
        ]
        return list(reversed(records))

    # -------------------------
    # Traffic
    # -------------------------
    def insert_traffic_record(self, record: TrafficRecord) -> TrafficRecord:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO traffic_data (city_id, timestamp, congestion_level)
                VALUES (?, ?, ?)
                """,
                (
                    record.city_id,
                    _to_iso(record.timestamp),
                    record.congestion_level,
                ),
            )
            conn.commit()
            new_id = int(cur.lastrowid)

        return replace(record, id=new_id)

    def get_recent_traffic(self, city_id: int, limit: int = 30) -> list[TrafficRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, city_id, timestamp, congestion_level
                FROM traffic_data
                WHERE city_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (city_id, limit),
            ).fetchall()

        records = [
            TrafficRecord(
                id=int(r["id"]),
                city_id=int(r["city_id"]),
                timestamp=_from_iso(str(r["timestamp"])),
                congestion_level=float(r["congestion_level"]),
            )
            for r in rows
        ]
        return list(reversed(records))

    # -------------------------
    # Analysis results
    # -------------------------
    def insert_analysis_result(self, result: AnalysisResult) -> AnalysisResult:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analysis_results (city_id, timestamp, category, status, metrics_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result.city_id,
                    _to_iso(result.timestamp),
                    result.category,
                    result.status,
                    result.metrics_json,
                ),
            )
            conn.commit()
            new_id = int(cur.lastrowid)

        return result.model_copy(update={"id": new_id})


    def get_latest_analysis(self, city_id: int, category: str | None = None) -> AnalysisResult | None:
        sql = """
            SELECT id, city_id, timestamp, category, status, metrics_json
            FROM analysis_results
            WHERE city_id = ?
        """
        params: list[object] = [city_id]

        if category is not None:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY timestamp DESC LIMIT 1"

        with self._connect() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()

        if not row:
            return None

        return AnalysisResult(
            id=int(row["id"]),
            city_id=int(row["city_id"]),
            timestamp=_from_iso(str(row["timestamp"])),
            category=str(row["category"]),
            status=str(row["status"]),
            metrics_json=str(row["metrics_json"]),
        )

    def list_recent_analyses(self, limit: int = 10) -> list[AnalysisResult]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, city_id, timestamp, category, status, metrics_json
                FROM analysis_results
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            AnalysisResult(
                id=int(r["id"]),
                city_id=int(r["city_id"]),
                timestamp=_from_iso(str(r["timestamp"])),
                category=str(r["category"]),
                status=str(r["status"]),
                metrics_json=str(r["metrics_json"]),
            )
            for r in rows
        ]
