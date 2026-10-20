import sqlite3
from contextlib import closing
import sys
import tempfile
import subprocess
import json
from unittest.mock import Mock, patch
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcchickens.database import create_tables, get_connection
from mcchickens.matchup_importer import completed_week, import_matchups
from mcchickens.analytics import results, report, milestones, head_to_head, league_records, storylines
from mcchickens.sleeper import SleeperClient


class FakeClient:
    def __init__(self):
        self.league = dict(season='2025', league_id='one', name='League', status='in_season',
                           settings={'playoff_week_start': 3})
        self.rows = {1: [dict(roster_id=1, matchup_id=1, points=10),
                         dict(roster_id=2, matchup_id=1, points=20, custom_points=0)],
                     2: [dict(roster_id=1, matchup_id=1, points=5),
                         dict(roster_id=2, matchup_id=1, points=5)],
                     3: [dict(roster_id=1, matchup_id=1, points=1),
                         dict(roster_id=2, matchup_id=1, points=10)]}
        self.calls = []
        self.fail = False

    def get_league_history(self, league_id):
        return [self.league]

    def get_users(self, league_id):
        return [dict(user_id='a', display_name='Alice'), dict(user_id='b', display_name='Bob')]

    def get_rosters(self, league_id):
        return [dict(roster_id=1, owner_id='a'), dict(roster_id=2, owner_id='b')]

    def get_nfl_state(self):
        return dict(season='2025', season_type='regular', week=4)

    def get_matchups(self, league_id, week):
        self.calls.append(week)
        if self.fail and week == 2:
            raise RuntimeError('network failure')
        return self.rows.get(week, [])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.db'
        self.client = FakeClient()

    def load(self):
        return import_matchups(self.client, self.path)

    def query(self, sql):
        con = get_connection(self.path)
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()

    def test_ingest_idempotent_overrides_playoffs_and_finality(self):
        self.assertEqual(self.load(), 6)
        self.assertEqual(self.client.calls, [1, 2, 3])
        self.load()
        self.assertEqual(self.query('SELECT COUNT(*) FROM matchups'), [(6,)])
        self.assertEqual(self.query('SELECT points, is_complete FROM matchups WHERE week=1 AND roster_id=2'), [(0.0, 1)])
        self.assertEqual(len(results(self.path)), 4)
        self.assertEqual(len(results(self.path, include_playoffs=True)), 6)

    def test_refresh_corrects_scores_and_removes_stale_rows(self):
        self.load()
        self.client.rows[1][0]['points'] = -1
        self.client.rows[2] = []
        self.load()
        self.assertEqual(self.query('SELECT COUNT(*) FROM matchups'), [(4,)])
        self.assertEqual(report(self.path)['managers']['a']['losses'], 1)

    def test_failure_rolls_back_all_matchup_changes(self):
        self.load()
        before = self.query('SELECT * FROM matchups ORDER BY week, roster_id')
        self.client.rows[1][0]['points'] = 999
        self.client.fail = True
        with self.assertRaises(RuntimeError):
            self.load()
        self.assertEqual(before, self.query('SELECT * FROM matchups ORDER BY week, roster_id'))

    def test_invalid_scores_and_duplicate_rosters_rollback(self):
        for invalid in (float('nan'), float('inf')):
            self.client.rows[1][0]['points'] = invalid
            with self.assertRaises(ValueError):
                self.load()
            self.assertEqual(self.query('SELECT COUNT(*) FROM matchups'), [(0,)])
        self.client.rows[1][0]['points'] = 1
        self.client.rows[1].append(self.client.rows[1][0])
        with self.assertRaises(ValueError):
            self.load()

    def test_statistics_ties_streaks_records_milestones(self):
        self.load()
        data = report(self.path)
        alice = data['managers']['a']
        self.assertEqual((alice['games'], alice['wins'], alice['ties'], alice['points_for']), (2, 1, 1, 15))
        self.assertEqual(alice['win_percentage'], .75)
        self.assertEqual(data['streaks']['a']['current_result'], 'T')
        self.assertEqual(data['streaks']['a']['longest_win'], 1)
        self.assertEqual(data['records']['largest_margin']['value'], 10)
        self.assertEqual(data['records']['closest_game']['value'], 0)
        self.assertEqual(len(milestones(results(self.path), (1, 2))), 5)
        self.assertEqual(head_to_head(results(self.path))['b', 'a']['losses'], 1)
        self.assertEqual(report(self.path, 2024)['managers'], {})

    def test_byes_missing_scores_unknown_owners_and_invalid_groups(self):
        for rows in ([dict(roster_id=1, matchup_id=None, points=100)],
                     [dict(roster_id=1, matchup_id=1, points=None), dict(roster_id=2, matchup_id=1, points=2)],
                     [dict(roster_id=1, matchup_id=1, points=1), dict(roster_id=3, matchup_id=1, points=2)],
                     [dict(roster_id=i, matchup_id=1, points=i) for i in (1, 2, 3)]):
            self.client.rows = {1: rows}
            self.load()
            self.assertEqual(results(self.path), [])

    def test_completed_week_boundaries(self):
        state = dict(season='2025', season_type='regular', week=4)
        self.assertEqual(completed_week(self.client.league, state), 3)
        self.assertEqual(completed_week(dict(season='2020', status='complete'), {}), 17)
        for season, phase, expected in [('2026', 'regular', 0), ('2025', 'pre', 0), ('2025', 'post', 18), ('2024', 'regular', 18)]:
            league = dict(season=season, status='in_season')
            self.assertEqual(completed_week(league, dict(state, season_type=phase)), expected)

    def test_legacy_migration_preserves_unverified_scores(self):
        with closing(sqlite3.connect(self.path)) as con:
            con.execute('CREATE TABLE matchups (season INTEGER, week INTEGER, roster_id INTEGER, matchup_id INTEGER, points REAL, is_playoff INTEGER DEFAULT 0, PRIMARY KEY(season,week,roster_id))')
            con.execute('INSERT INTO matchups VALUES (2024,1,1,1,10,0)')
            con.commit()
        create_tables(self.path)
        create_tables(self.path)
        self.assertEqual(self.query('SELECT points, is_complete FROM matchups'), [(10, 0)])

    def test_reassigned_owner_and_current_display_name(self):
        self.load()
        self.client.get_users = lambda league_id: [dict(user_id='c', display_name='Carol'), dict(user_id='b', display_name='New Bob')]
        self.client.get_rosters = lambda league_id: [dict(roster_id=1, owner_id='c'), dict(roster_id=2, owner_id='b')]
        self.load()
        self.assertEqual(self.query('SELECT COUNT(*) FROM season_managers'), [(2,)])
        self.assertNotIn('a', report(self.path)['managers'])
        self.assertEqual(self.query("SELECT current_display_name FROM managers WHERE user_id='b'"), [('New Bob',)])

    def test_cli_json_report(self):
        self.load()
        process = subprocess.run([sys.executable, 'scripts/report.py', '--database', str(self.path), '--season', '2025'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['managers']['a']['wins'], 1)

    def test_storylines_tied_records_and_streaks(self):
        self.load()
        games = results(self.path)
        facts = storylines(games)
        self.assertTrue(any(f['record'] == 'closest_game' for f in facts))
        self.assertTrue(all(f['week'] == 2 for f in facts))
        self.assertEqual(len(league_records(games)['highest_score']['holders']), 1)
        self.assertEqual(storylines([]), [])
        repeated = [dict(games[0], week=week) for week in (1, 2, 3)]
        repeated += [dict(games[1], week=week) for week in (1, 2, 3)]
        self.assertEqual(len([f for f in storylines(repeated) if f['kind'] == 'streak']), 2)
        with self.assertRaises(ValueError):
            milestones(games, (0,))

    def test_http_errors_propagate_and_timeout_is_set(self):
        response = Mock()
        response.json.return_value = {'league_id': 'one'}
        with patch('mcchickens.sleeper.requests.get', return_value=response) as request:
            self.assertEqual(SleeperClient().get_league('one'), {'league_id': 'one'})
            self.assertEqual(request.call_args.kwargs['timeout'], 10)
            response.raise_for_status.assert_called_once()
            response.raise_for_status.side_effect = RuntimeError('HTTP error')
            with self.assertRaises(RuntimeError):
                SleeperClient().get_league('one')

    def test_history_cycle_and_zero_sentinel(self):
        client = SleeperClient()
        client.get_league = lambda league_id: dict(previous_league_id=league_id)
        with self.assertRaises(ValueError):
            client.get_league_history('one')
        client.get_league = lambda league_id: dict(previous_league_id='0')
        self.assertEqual(len(client.get_league_history('one')), 1)

    def test_season_identity_across_roster_changes(self):
        self.load()
        self.client.league['season'] = '2024'
        self.client.league['league_id'] = 'older'
        self.client.get_rosters = lambda league_id: [dict(roster_id=2, owner_id='a'), dict(roster_id=1, owner_id='b')]
        self.load()
        self.assertEqual(report(self.path)['managers']['a']['games'], 4)
        self.assertEqual(report(self.path)['managers']['a']['wins'], 1)
        self.assertEqual(report(self.path)['managers']['a']['losses'], 1)


if __name__ == '__main__':
    unittest.main()
