import sys
from pathlib import Path


# Add the src directory to Python's import path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.sleeper import SleeperClient


def main():
    client = SleeperClient()

    league = client.get_league(CURRENT_LEAGUE_ID)

    print("=" * 55)
    print("McCHICKENS FANTASY BOT - SLEEPER CONNECTION TEST")
    print("=" * 55)

    print(f"League Name:       {league['name']}")
    print(f"Season:            {league['season']}")
    print(f"League ID:         {league['league_id']}")
    print(f"Number of Teams:   {league['total_rosters']}")
    print(f"Status:            {league['status']}")
    print(f"Previous League:   {league.get('previous_league_id')}")

    print("=" * 55)


if __name__ == "__main__":
    main()