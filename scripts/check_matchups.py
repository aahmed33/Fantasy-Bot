import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcchickens.database import get_connection


def main():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                season,
                COUNT(*) AS records,
                COUNT(DISTINCT week) AS weeks,
                MIN(week),
                MAX(week)
            FROM matchups
            GROUP BY season
            ORDER BY season
            """
        )

        print("=" * 65)
        print("McCHICKENS HISTORICAL MATCHUP DATA")
        print("=" * 65)

        for season, records, weeks, first, last in cursor.fetchall():
            print(
                f"{season} | "
                f"Records: {records:>3} | "
                f"Weeks: {weeks:>2} | "
                f"Range: {first}-{last}"
            )

        cursor.execute("SELECT COUNT(*) FROM matchups")
        print(f"\nTotal roster-week records: {cursor.fetchone()[0]}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()