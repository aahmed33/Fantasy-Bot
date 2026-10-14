import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from mcchickens.database import DATABASE_PATH, create_tables


def main():
    create_tables()

    print("=" * 60)
    print("McCHICKENS DATABASE INITIALIZED")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH}")
    print()
    print("Created tables:")
    print("  - managers")
    print("  - seasons")
    print("  - season_managers")
    print("=" * 60)


if __name__ == "__main__":
    main()