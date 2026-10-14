import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcchickens.database import get_connection


def main():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        for table in ("seasons", "managers", "season_managers"):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count}")

        print("\nManagers per season:")

        cursor.execute(
            """
            SELECT season, COUNT(*)
            FROM season_managers
            GROUP BY season
            ORDER BY season
            """
        )

        for season, count in cursor.fetchall():
            print(f"{season}: {count} managers")

    finally:
        connection.close()


if __name__ == "__main__":
    main()