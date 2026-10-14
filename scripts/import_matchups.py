import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcchickens.matchup_importer import import_matchups


if __name__ == "__main__":
    import_matchups()