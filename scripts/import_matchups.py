import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcchickens.matchup_importer import import_matchups
from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.database import DATABASE_PATH


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import completed historical matchup weeks")
    parser.add_argument('--database', type=Path, default=DATABASE_PATH)
    parser.add_argument('--league-id', default=CURRENT_LEAGUE_ID)
    args = parser.parse_args()
    count = import_matchups(database_path=args.database, league_id=args.league_id)
    print(f"Imported {count} completed roster-week records")