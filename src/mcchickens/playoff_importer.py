"""Auditable playoff sources, isolated from the original league database."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .config import CURRENT_LEAGUE_ID
from .database import DATABASE_PATH, create_tables, get_connection
from .sleeper import SleeperClient


def validation_database(database_path):
    if database_path is None:
        raise ValueError("An explicit separate championship database is required")
    path = Path(database_path).resolve()
    if path == DATABASE_PATH.resolve() or (
        path.exists() and DATABASE_PATH.exists() and path.samefile(DATABASE_PATH)
    ):
        raise ValueError("The original SQLite database is protected; use a separate database")
    return path


def import_playoffs(database_path, client=None, league_id=CURRENT_LEAGUE_ID):
    """Fetch all completed seasons >=2020 before atomically publishing snapshots.

    Each snapshot freezes settings, brackets, owner IDs/names and playoff scores.
    Corrected responses replace the current pointer; prior revisions survive.
    No manager or weekly matchup data is overwritten by this importer.
    """
    path = validation_database(database_path)
    client = client or SleeperClient()
    leagues = client.get_league_history(league_id)
    eligible = [l for l in leagues if int(l['season']) >= 2020 and l.get('status') == 'complete']
    seasons = [int(l['season']) for l in eligible]
    if len(seasons) != len(set(seasons)):
        raise ValueError("Multiple leagues for the same season are ambiguous")
    snapshots = []
    for league in sorted(eligible, key=lambda l: int(l['season'])):
        season = int(league['season'])
        league_key = league['league_id']
        settings = league.get('settings') or {}
        start = settings.get('playoff_week_start')
        last = 18 if season >= 2021 else 17
        weeks = range(start, last + 1) if type(start) is int and 1 <= start <= last else []
        payload = dict(league=league, users=client.get_users(league_key),
                       rosters=client.get_rosters(league_key),
                       winners=client.get_playoff_bracket(league_key, 'winners'),
                       losers=client.get_playoff_bracket(league_key, 'losers'),
                       matchups={str(w): client.get_matchups(league_key, w) for w in weeks})
        # Reject transport/schema failures rather than publishing partial fetches.
        for name in ('users', 'rosters'):
            if not isinstance(payload[name], list):
                raise ValueError(f"Expected {name} list")
        for name in ('winners', 'losers'):
            if payload[name] is not None and not isinstance(payload[name], list):
                raise ValueError(f"Expected {name} bracket list or null")
        if any(not isinstance(rows, list) for rows in payload['matchups'].values()):
            raise ValueError("Expected weekly matchup list")
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        snapshots.append((season, digest, datetime.now(timezone.utc).isoformat(), encoded))
    create_tables(path)
    connection = get_connection(path)
    try:
        with connection:
            for season, digest, fetched, payload in snapshots:
                connection.execute('INSERT OR IGNORE INTO playoff_snapshots VALUES (?, ?, ?, ?)',
                                   (season, digest, fetched, payload))
                connection.execute('''INSERT INTO playoff_seasons VALUES (?, ?)
                    ON CONFLICT(season) DO UPDATE SET digest=excluded.digest''', (season, digest))
    finally:
        connection.close()
    return dict(imported_seasons=sorted(seasons), skipped_seasons=sorted(
        int(l['season']) for l in leagues if l not in eligible))
