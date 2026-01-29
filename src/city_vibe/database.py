import sqlite3
import logging
from city_vibe.config import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    """Initializes the database schema if it doesn't exist."""
    logger.info(f"Initializing database at {DATABASE_PATH}")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create Cities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                latitude REAL,
                longitude REAL
            )
        """)
        
        # Create Weather Data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        """)
        
        # Create Traffic Data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                congestion_level REAL,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        """)
        
        # Create Analysis Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                category TEXT, -- e.g., 'weather', 'traffic'
                status TEXT,   -- e.g., 'stable', 'improving'
                metrics_json TEXT,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        """)
        
        conn.commit()
    logger.info("Database initialization complete.")

def db_exists():
    """Checks if the database file exists."""
    return DATABASE_PATH.exists()
