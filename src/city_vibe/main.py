import sys
from city_vibe.database import db_exists, init_db
from city_vibe.data_manager import DataManager
from city_vibe.config import LOGGING_CONFIG, DEFAULT_CITIES
from city_vibe.presentation.cli import menu


def main() -> None:
    # Configure logging for the application.
    import logging.config
    import logging

    logging.config.dictConfig(LOGGING_CONFIG)

    logger = logging.getLogger(__name__)

    if "--cli" in sys.argv:
        # The menu() function now handles its own warm-up with CLI styling
        menu()
        return

    logger.info("Starting City Vibe Analysis (Automated Mode)...")

    data_manager = DataManager()

    # Initialize the database if it doesn't exist
    if not db_exists():
        logger.info("Database not found. Initializing database...")
        init_db()
        logger.info("Database initialized.")

    # Geocode DEFAULT_CITIES and fetch initial historical data
    logger.info(f"Processing default cities: {DEFAULT_CITIES}")
    for city_name in DEFAULT_CITIES:
        data_manager.refresh_city_data(city_name)

    # Refresh current data and run vibe analysis for all confirmed cities
    data_manager.refresh_all_confirmed_cities_current_data()

    logger.info("City Vibe Analysis (Automated Mode) completed.")


# The if __name__ == "__main__": block is removed as run.py calls main() directly.
