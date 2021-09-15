import json
from pathlib import Path

from ...constants import TMP_DIR


DEM_DIR = Path(TMP_DIR, "dems")
if not DEM_DIR.exists():
    DEM_DIR.mkdir()


with open(Path(Path(__file__).parent, "ned_13_index.json")) as f:
    ned_13_index = json.load(f)["tiles"]
