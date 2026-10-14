from .config import CURRENT_LEAGUE_ID
from .database import create_tables, get_connection
from .sleeper import SleeperClient


def import_matchups():
    create_tables()

    client = SleeperClient()
    leagues = client.get_league_history(CURRENT_LEAGUE_ID)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        for league in reversed(leagues):
            season = int(league["season"])
            league_id = league["league_id"]

            print(f"\nImporting {season} matchups...")

            season_count = 0

            # Weeks 1-18 cover the modern NFL season.
            # Empty future weeks are skipped.
            for week in range(1, 19):
                matchups = client.get_matchups(league_id, week)

                if not matchups:
                    continue

                for matchup in matchups:
                    roster_id = matchup["roster_id"]
                    matchup_id = matchup.get("matchup_id")
                    points = matchup.get("points")

                    cursor.execute(
                        """
                        INSERT INTO matchups
                            (season, week, roster_id, matchup_id, points)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(season, week, roster_id)
                        DO UPDATE SET
                            matchup_id = excluded.matchup_id,
                            points = excluded.points
                        """,
                        (
                            season,
                            week,
                            roster_id,
                            matchup_id,
                            points
                        )
                    )

                    season_count += 1

            print(f"  Imported {season_count} roster-week records")

        connection.commit()
        print("\nMatchup import completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()