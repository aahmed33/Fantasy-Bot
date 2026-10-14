import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.database import DATABASE_PATH


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )

        tables = cursor.fetchall()

        print("=" * 60)
        print("McCHICKENS DATABASE")
        print("=" * 60)

        for table in tables:
            print(table[0])

        print("=" * 60)

    finally:
        connection.close()


if __name__ == "__main__":
    main()