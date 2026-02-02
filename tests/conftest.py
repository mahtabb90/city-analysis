import sys
from pathlib import Path


root_dir = Path(__file__).resolve().parents[1]
src_dir = root_dir / "src"

sys.path.insert(0, str(src_dir))
