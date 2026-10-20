"""Import championship sources into an explicit separate validation database."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.playoff_importer import import_playoffs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--league-id', default=CURRENT_LEAGUE_ID)
    args = parser.parse_args()
    try:
        summary = import_playoffs(args.database, league_id=args.league_id)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
