from .config import CURRENT_LEAGUE_ID
from .database import get_connection, create_tables
from .sleeper import SleeperClient
from .utils import get_team_name


def import_league_history(client=None, database_path=None, league_id=CURRENT_LEAGUE_ID):
    """Import all historical league seasons and managers into SQLite."""

    create_tables(database_path)

    client = client or SleeperClient()
    leagues = client.get_league_history(league_id)

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        for league in reversed(leagues):
            season = int(league["season"])
            league_id = league["league_id"]

            print(f"Importing {season}...")

            users = client.get_users(league_id)
            rosters = client.get_rosters(league_id)

            users_by_id = {
                user["user_id"]: user
                for user in users
            }

            cursor.execute(
                """
                INSERT INTO seasons (season, league_id, league_name)
                VALUES (?, ?, ?)
                ON CONFLICT(season) DO UPDATE SET
                    league_id = excluded.league_id,
                    league_name = excluded.league_name
                """,
                (season, league_id, league["name"].strip())
            )

            # Refresh ownership snapshots so replaced owners cannot duplicate a roster.
            cursor.execute("DELETE FROM season_managers WHERE season = ?", (season,))
            for roster in rosters:
                owner_id = roster.get("owner_id")
                user = users_by_id.get(owner_id)

                if not user:
                    print(
                        f"  Skipping roster {roster['roster_id']}: "
                        "no matching manager"
                    )
                    continue

                display_name = user.get("display_name") or "Unknown"
                team_name = get_team_name(user)

                cursor.execute(
                    """
                    INSERT INTO managers (user_id, current_display_name)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    (owner_id, display_name)
                )

                cursor.execute(
                    """
                    INSERT INTO season_managers
                        (season, user_id, roster_id, display_name, team_name)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(season, user_id) DO UPDATE SET
                        roster_id = excluded.roster_id,
                        display_name = excluded.display_name,
                        team_name = excluded.team_name
                    """,
                    (
                        season,
                        owner_id,
                        roster["roster_id"],
                        display_name,
                        team_name
                    )
                )

        # Refresh current names using the most recent season.
        cursor.execute(
            """
            UPDATE managers
            SET current_display_name = (
                SELECT sm.display_name
                FROM season_managers sm
                WHERE sm.user_id = managers.user_id
                ORDER BY sm.season DESC
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1 FROM season_managers sm
                WHERE sm.user_id = managers.user_id
            )
            """
        )

        connection.commit()
        print("Historical import completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
