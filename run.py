import sys
from pathlib import Path

# Define the project root directory
BASE_DIR = Path(__file__).resolve().parent
SRC_PATH = BASE_DIR/"src"

# Add the src directory to the module search path
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from city_vibe.main import main

if __name__ == "__main__":
    main()