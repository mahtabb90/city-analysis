from city_vibe import database
from city_vibe.database import db_exists, init_db
from city_vibe.data_manager import DataManager
from city_vibe.config import LOGGING_CONFIG, DEFAULT_CITIES


def main() -> None:
    # Configure logging for the application.
    import logging.config
    import logging

    logging.config.dictConfig(LOGGING_CONFIG)

    logger = logging.getLogger(__name__)

    logger.info("Starting City Vibe Analysis...")

    if not db_exists():
        logger.info("Database not found. Initializing...")
        init_db()
    else:
        logger.info("Database already exists.")

    data_manager = DataManager()

    # Process default cities on startup if they are not confirmed
    for city_name in DEFAULT_CITIES:
        try:
            city_id = database.get_or_create_city(city_name)
            city_record = database.get_city_by_id(city_id)

            if city_record and city_record.is_confirmed:
                logger.info(
                    f"Default city '{city_name}' confirmed. "
                    "Skipping historical data refresh."
                )
            else:
                logger.info(
                    f"Processing default city: '{city_name}' "
                    "for historical data."
                )
                data_manager.refresh_city_data(city_name)
        except ValueError as e:
            logger.error(
                f"Geocoding error for city '{city_name}': {e}."
            )
        except Exception as e:
            logger.error(
                f"Unexpected error for city '{city_name}': {e}."
            )

    data_manager.refresh_all_confirmed_cities_current_data()

    logger.info("System ready.")


if __name__ == "__main__":
    main()
