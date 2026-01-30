from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parents[2]

# Database configuration
DATABASE_NAME = "city_analysis.db"
DATABASE_PATH = BASE_DIR / "data" / DATABASE_NAME

# Ensure data directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
