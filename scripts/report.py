"""Offline JSON analytics report: python scripts/report.py --help."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcchickens.analytics import report
from mcchickens.database import DATABASE_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DATABASE_PATH)
    parser.add_argument('--season', type=int)
    parser.add_argument('--include-playoffs', action='store_true')
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database does not exist; run import_matchups.py first')
    print(json.dumps(report(args.database, args.season, args.include_playoffs), indent=2))


if __name__ == '__main__':
    main()
