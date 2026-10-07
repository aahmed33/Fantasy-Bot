import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.config import CURRENT_LEAGUE_ID
from mcchickens.sleeper import SleeperClient
from mcchickens.utils import get_team_name


def main():
    client = SleeperClient()

    leagues = client.get_league_history(CURRENT_LEAGUE_ID)

    print("=" * 80)
    print("McCHICKENS FANTASY LEAGUE - MANAGER HISTORY")
    print("=" * 80)

    # Oldest season first
    for league in reversed(leagues):
        league_id = league["league_id"]
        season = league["season"]

        users = client.get_users(league_id)
        rosters = client.get_rosters(league_id)

        users_by_id = {
            user["user_id"]: user
            for user in users
        }

        print()
        print(f"{season} SEASON")
        print("-" * 80)

        for roster in sorted(rosters, key=lambda r: r["roster_id"]):
            owner_id = roster.get("owner_id")
            user = users_by_id.get(owner_id)

            if user:
                manager_name = user.get("display_name", "Unknown")
                team_name = get_team_name(user)
            else:
                manager_name = "Unknown"
                team_name = "Unknown"

            print(
                f"Roster {roster['roster_id']:>2} | "
                f"{manager_name:<20} | "
                f"{team_name:<25} | "
                f"User ID: {owner_id}"
            )


if __name__ == "__main__":
    main()