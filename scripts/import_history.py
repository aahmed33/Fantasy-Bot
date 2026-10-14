import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcchickens.importer import import_league_history


if __name__ == "__main__":
    import_league_history()