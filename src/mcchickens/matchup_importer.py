"""Idempotent import of completed NFL roster-weeks."""
import math

from .config import CURRENT_LEAGUE_ID
from .database import create_tables, get_connection
from .importer import import_league_history
from .sleeper import SleeperClient


def completed_week(league, state):
    season = int(league['season'])
    last = 18 if season >= 2021 else 17
    if league.get('status') in ('pre_draft', 'drafting'):
        return 0
    if league.get('status') == 'complete':
        return last
    current = int(state['season'])
    if season < current:
        return last
    if season > current or state.get('season_type') == 'pre':
        return 0
    if state.get('season_type') == 'post':
        return last
    return max(0, min(last, int(state.get('week') or 1) - 1))


def import_matchups(client=None, database_path=None, league_id=CURRENT_LEAGUE_ID):
    """Refresh completed weeks atomically; manager history is imported first.

    Current NFL week is deliberately excluded, even when some games finished.
    Legacy rows stay unverified until refreshed. Returns imported row count.
    """
    client = client or SleeperClient()
    create_tables(database_path)
    import_league_history(client, database_path, league_id)
    leagues = client.get_league_history(league_id)
    state = client.get_nfl_state() if any(l.get('status') != 'complete' for l in leagues) else {}
    connection = get_connection(database_path)
    count = 0
    try:
        with connection:
            for league in reversed(leagues):
                season = int(league['season'])
                end = completed_week(league, state)
                playoff_start = int(league.get('settings', {}).get('playoff_week_start') or 0)
                # Remove old speculative future rows from the original importer.
                connection.execute('DELETE FROM matchups WHERE season=? AND week>?', (season, end))
                for week in range(1, end + 1):
                    rows = client.get_matchups(league['league_id'], week)
                    if not isinstance(rows, list):
                        raise ValueError('Expected a matchup list')
                    seen = set()
                    validated = []
                    for row in rows:
                        roster = int(row['roster_id'])
                        if roster in seen:
                            raise ValueError('Duplicate roster in matchup week')
                        seen.add(roster)
                        points = row.get('custom_points')
                        if points is None:
                            points = row.get('points')
                        if points is not None:
                            points = float(points)
                            if not math.isfinite(points):
                                raise ValueError('Non-finite matchup score')
                        validated.append((season, week, roster, row.get('matchup_id'), points,
                                          int(bool(playoff_start and week >= playoff_start)), 1))
                    connection.execute('DELETE FROM matchups WHERE season=? AND week=?', (season, week))
                    connection.executemany('INSERT INTO matchups (season, week, roster_id, matchup_id, points, is_playoff, is_complete) VALUES (?, ?, ?, ?, ?, ?, ?)', validated)
                    count += len(validated)
        return count
    finally:
        connection.close()
