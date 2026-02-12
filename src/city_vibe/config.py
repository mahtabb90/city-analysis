from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parents[2]

# Database configuration
DATABASE_NAME = "city_analysis.db"
DATABASE_PATH = BASE_DIR / "data" / DATABASE_NAME
COMMENTS_PATH = BASE_DIR / "data" / "comments.json"

# Ensure directories exist
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "city_vibe.log"),
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "city_vibe": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Default cities for data ingestion
DEFAULT_CITIES = ["Stockholm"]
