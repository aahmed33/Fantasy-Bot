import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "data" / "mcchickens.db"


def get_connection():
    """Create and return a connection to the McChickens database."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    # Enforce SQLite foreign key constraints.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_tables():
    """Create the initial McChickens database tables."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS managers (
                user_id TEXT PRIMARY KEY,
                current_display_name TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS seasons (
                season INTEGER PRIMARY KEY,
                league_id TEXT NOT NULL UNIQUE,
                league_name TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS season_managers (
                season INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                roster_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                team_name TEXT NOT NULL,

                PRIMARY KEY (season, user_id),

                FOREIGN KEY (season)
                    REFERENCES seasons(season),

                FOREIGN KEY (user_id)
                    REFERENCES managers(user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS matchups (
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                roster_id INTEGER NOT NULL,
                matchup_id INTEGER,
                points REAL,
                is_playoff INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (season, week, roster_id),

                FOREIGN KEY (season)
                    REFERENCES seasons(season),

                CHECK (is_playoff IN (0, 1))
            )
            """
        )

        connection.commit()

    finally:
        connection.close()