import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.sleeper import SleeperClient


def main():
    client = SleeperClient()

    leagues = client.get_league_history(CURRENT_LEAGUE_ID)

    print("=" * 75)
    print("McCHICKENS FANTASY LEAGUE - HISTORICAL SEASONS")
    print("=" * 75)

    for league in leagues:
        print(f"Season:              {league['season']}")
        print(f"League Name:         {league['name']}")
        print(f"League ID:           {league['league_id']}")
        print(f"Previous League ID:  {league.get('previous_league_id')}")
        print("-" * 75)

    print(f"Total Seasons Found: {len(leagues)}")


if __name__ == "__main__":
    main()