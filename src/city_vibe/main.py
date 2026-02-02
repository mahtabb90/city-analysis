
import logging
import sys

from city_vibe.database import db_exists, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting City Vibe Analysis...")

    # Check if database exists, if not, initialize it
    if not db_exists():
        logger.info("Database not found. Initializing...")
        init_db()
    else:
        logger.info("Database already exists.")

    # Placeholder for further application logic
    logger.info("System ready.")


if __name__ == "__main__":
    main()


