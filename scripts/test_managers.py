import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.sleeper import SleeperClient


def main():
    client = SleeperClient()

    users = client.get_users(CURRENT_LEAGUE_ID)
    rosters = client.get_rosters(CURRENT_LEAGUE_ID)

    print("=" * 70)
    print("McCHICKENS FANTASY LEAGUE - MANAGERS")
    print("=" * 70)

    for roster in rosters:
        owner_id = roster.get("owner_id")

        user = next(
            (user for user in users if user["user_id"] == owner_id),
            None
        )

        if user:
            display_name = user.get("display_name", "Unknown")
            team_name = user.get("metadata", {}).get("team_name", "No Team Name")
        else:
            display_name = "Unknown"
            team_name = "Unknown"

        print(f"Roster ID:   {roster['roster_id']}")
        print(f"User ID:     {owner_id}")
        print(f"Manager:     {display_name}")
        print(f"Team Name:   {team_name}")
        print("-" * 70)


if __name__ == "__main__":
    main()