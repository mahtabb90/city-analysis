import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch
from city_vibe.database import init_db, db_exists, get_connection


@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a temporary database path."""
    db_path = tmp_path / "test_city_analysis.db"
    with patch("city_vibe.database.DATABASE_PATH", db_path):
        yield db_path


def test_init_db_creates_file(temp_db):
    """Test that init_db actually creates the database file."""
    assert not temp_db.exists()
    init_db()
    assert temp_db.exists()


def test_db_exists(temp_db):
    """Test the db_exists helper function."""
    assert not db_exists()
    temp_db.touch()
    assert db_exists()


def test_init_db_creates_tables(temp_db):
    """Test that all expected tables are created during initialization."""
    init_db()
    
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {"cities", "weather_data", "traffic_data", "analysis_results"}
        for table in expected_tables:
            assert table in tables


def test_init_db_idempotent(temp_db):
    """Test that calling init_db multiple times doesn't cause errors."""
    init_db()
    init_db() # Should not raise an exception even if tables already exist
    assert temp_db.exists()


def test_get_connection(temp_db):
    """Test that get_connection returns a valid sqlite3 connection."""
    init_db()
    conn = get_connection()
    try:
        assert isinstance(conn, sqlite3.Connection)
        # Check if we can execute a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
    finally:
        conn.close()
