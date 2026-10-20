import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcchickens.championships import championship_report, season_history
from mcchickens.playoff_importer import import_playoffs, validation_database
from mcchickens.database import DATABASE_PATH, get_connection, create_tables
from mcchickens.analytics import report
from mcchickens.sleeper import SleeperClient


def fixture(year=2020, multi=False):
    start = 14 if multi else 15
    final_week = start + 1
    payload = dict(league=dict(season=str(year), league_id=str(year), name='League', status='complete',
        settings=dict(playoff_teams=4, playoff_week_start=start, playoff_round_type=1 if multi else 0)),
        users=[dict(user_id=str(i), display_name=f'Name {year}-{i}') for i in range(1, 7)],
        rosters=[dict(roster_id=i, owner_id=str(i)) for i in range(1, 7)],
        winners=[dict(m=1, r=1, t1=1, t2=4, w=1, l=4),
                 dict(m=2, r=1, t1=2, t2=3, w=2, l=3),
                 dict(m=3, r=2, t1=1, t2=2, t1_from={'w': 1}, t2_from={'w': 2}, w=1, l=2, p=1),
                 dict(m=4, r=2, t1=4, t2=3, t1_from={'l': 1}, t2_from={'l': 2}, w=3, l=4, p=3)],
        losers=[dict(m=1, r=1, t1=5, t2=6, w=5, l=6, p=1)], matchups={})
    for week, pairs in [(start, [(1, 4, 10, 5), (2, 3, 10, 5)]),
                        (final_week, [(1, 2, 20, 10), (3, 4, 20, 10)])]:
        payload['matchups'][str(week)] = [dict(roster_id=t, matchup_id=m, points=points)
            for m, (a, b, pa, pb) in enumerate(pairs, 1) for t, points in [(a, pa), (b, pb)]]
    if multi:
        payload['matchups'][str(final_week + 1)] = [dict(roster_id=1, matchup_id=1, points=0),
            dict(roster_id=2, matchup_id=1, points=5)]
    return payload


class FakeSleeper:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []
        self.fail = False

    def get_league_history(self, league_id):
        return [p['league'] for p in reversed(self.payloads)]

    def source(self, league_id):
        return next(p for p in self.payloads if p['league']['league_id'] == league_id)

    def get_users(self, league_id):
        return self.source(league_id)['users']

    def get_rosters(self, league_id):
        return self.source(league_id)['rosters']

    def get_playoff_bracket(self, league_id, kind):
        self.calls.append((league_id, kind))
        if self.fail and kind == 'losers':
            raise RuntimeError('HTTP failure')
        return self.source(league_id)[kind]

    def get_matchups(self, league_id, week):
        return self.source(league_id)['matchups'].get(str(week), [])


class ChampionshipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'playoffs.db'
        self.payload = fixture()
        self.client = FakeSleeper([self.payload])

    def load(self):
        return import_playoffs(self.path, self.client)

    def query(self, sql):
        connection = get_connection(self.path)
        try:
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def test_single_week_final_and_placement_separation(self):
        self.load()
        data = championship_report(self.path)
        year = data['champions_by_season'][0]
        self.assertEqual(year['champion']['user_id'], '1')
        self.assertEqual(year['runner_up']['user_id'], '2')
        self.assertEqual([p['place'] for p in year['placements']], [1, 2, 3, 4])
        self.assertEqual(len(year['participants']), 4)
        stats = {s['user_id']: s for s in data['leaderboard']}
        self.assertEqual(stats['1']['series_wins'], 2)
        self.assertEqual(stats['3']['series_wins'], 0)  # third-place win is not advancement
        self.assertEqual(stats['5']['championships'], 0)
        self.assertEqual(stats['5']['playoff_appearances'], 0)
        self.assertEqual(stats['2']['runner_up_finishes'], 1)
        self.assertEqual(stats['1']['by_round'], {'1': {'wins': 1, 'losses': 0}, '2': {'wins': 1, 'losses': 0}})

    def test_toilet_bowl_source_w_can_be_lower_scoring(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=1),
            dict(roster_id=6, matchup_id=3, points=100)])
        year = season_history(self.payload)
        consolation = year['consolation_series'][0]
        self.assertEqual(consolation['score_check']['status'], 'observed_source_l_higher')
        self.assertFalse(any('losers:1:score_disagreement' in issue for issue in year['issues']))
        self.assertEqual(year['champion']['user_id'], '1')
        self.assertFalse(any(p['manager']['user_id'] == '5' for p in year['placements']))

    def test_all_rounds_can_span_multiple_weeks(self):
        self.payload = fixture(multi=True)
        self.payload['matchups'] = {
            '14': [dict(roster_id=t, matchup_id=m, points=p) for m, pairs in
                   [(1, [(1, 10), (4, 2)]), (2, [(2, 10), (3, 2)])] for t, p in pairs],
            '15': [dict(roster_id=t, matchup_id=m, points=p) for m, pairs in
                   [(1, [(1, 1), (4, 2)]), (2, [(2, 1), (3, 2)])] for t, p in pairs],
            '16': [dict(roster_id=1, matchup_id=1, points=20), dict(roster_id=2, matchup_id=1, points=10)],
            '17': [dict(roster_id=1, matchup_id=1, points=0), dict(roster_id=2, matchup_id=1, points=5)]}
        self.client.payloads = [self.payload]
        self.load()
        year = championship_report(self.path)['champions_by_season'][0]
        self.assertEqual(year['series'][0]['score_check']['weeks'], [14, 15])
        self.assertEqual(year['championship_series']['score_check']['weeks'], [16, 17])
        self.assertEqual(championship_report(self.path)['leaderboard'][0]['series_wins'], 2)

    def test_toilet_bowl_last_place_and_manager_totals(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=1),
            dict(roster_id=6, matchup_id=3, points=100)])
        self.load()
        data = championship_report(self.path)
        history = data['champions_by_season'][0]['consolation']
        self.assertEqual(history['format'], 'toilet_bowl')
        self.assertEqual(history['toilet_bowl_last_place']['user_id'], '5')
        stats = {s['user_id']: s for s in data['consolation']['leaderboard']}
        self.assertEqual(stats['5']['last_place_finishes'], 1)
        self.assertEqual(stats['5']['lower_score_series_finishes'], 1)
        self.assertEqual(stats['6']['higher_score_series_wins'], 1)
        self.assertEqual(stats['5']['by_round']['1']['source_w_results'], 1)
        self.assertEqual(stats['5']['toilet_bowl_appearances'], 1)
        self.assertEqual(data['consolation']['storylines'][0]['kind'], 'toilet_bowl_last_place')
        self.assertEqual(data['leaderboard'][0]['championships'], 1)

    def test_toilet_bowl_multiweek_final_counts_once_and_corrects(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=100),
            dict(roster_id=6, matchup_id=3, points=0)])
        self.payload['matchups']['16'].extend([
            dict(roster_id=5, matchup_id=3, points=0),
            dict(roster_id=6, matchup_id=3, points=200)])
        self.load()
        self.load()
        data = championship_report(self.path)
        final = data['champions_by_season'][0]['consolation']['final_series']
        self.assertEqual(final['score_check']['weeks'], [15, 16])
        self.assertEqual(sum(s['last_place_finishes'] for s in data['consolation']['leaderboard']), 1)
        self.payload['losers'][0].update(w=6, l=5)
        self.load()
        data = championship_report(self.path)
        self.assertEqual(data['champions_by_season'][0]['consolation']['format'], 'consolation')
        self.assertEqual(sum(s['last_place_finishes'] for s in data['consolation']['leaderboard']), 0)
        self.assertEqual(sum(s['consolation_wins'] for s in data['consolation']['leaderboard']), 1)

    def test_unknown_toilet_bowl_outcomes_are_not_invented(self):
        for mode in ('missing_scores', 'tie', 'pending', 'ambiguous_final'):
            payload = copy.deepcopy(self.payload)
            if mode == 'tie':
                payload['matchups']['15'].extend([
                    dict(roster_id=5, matchup_id=3, points=10),
                    dict(roster_id=6, matchup_id=3, points=10)])
            if mode == 'pending':
                payload['losers'][0].update(w=None, l=None)
            if mode == 'ambiguous_final':
                payload['losers'].append(dict(payload['losers'][0], m=99))
            history = season_history(payload)['consolation']
            self.assertEqual(history['status'], 'unresolved')
            self.assertIsNone(history['toilet_bowl_last_place'])

    def test_multi_round_toilet_bowl_preserves_source_advancement(self):
        self.payload['losers'] = [
            dict(m=1, r=1, t1=3, t2=4, w=3, l=4),
            dict(m=2, r=1, t1=5, t2=6, w=5, l=6),
            dict(m=3, r=2, t1=3, t2=5, t1_from={'w': 1}, t2_from={'w': 2}, w=3, l=5, p=1),
            dict(m=4, r=2, t1=4, t2=6, t1_from={'l': 1}, t2_from={'l': 2}, w=4, l=6, p=3)]
        self.payload['matchups'] = {
            '15': [dict(roster_id=t, matchup_id=m, points=p) for m, pairs in
                   [(1, [(3, 1), (4, 10)]), (2, [(5, 1), (6, 10)])] for t, p in pairs],
            '16': [dict(roster_id=t, matchup_id=m, points=p) for m, pairs in
                   [(1, [(3, 1), (5, 10)]), (2, [(4, 1), (6, 10)])] for t, p in pairs]}
        self.load()
        data = championship_report(self.path)
        self.assertEqual(data['champions_by_season'][0]['consolation']['toilet_bowl_last_place']['user_id'], '3')
        stats = {s['user_id']: s for s in data['consolation']['leaderboard']}
        self.assertEqual(stats['3']['source_w_results'], 2)
        self.assertEqual(stats['3']['lower_score_series_finishes'], 2)
        self.assertEqual(stats['3']['last_place_finishes'], 1)
        self.assertEqual(len(data['consolation']['leaderboard']), 4)

    def test_official_rule_awards_source_l_when_source_w_is_match_winner(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=100),
            dict(roster_id=6, matchup_id=3, points=1)])
        self.load()
        bowl = championship_report(self.path)['toilet_bowl']
        final = bowl['history'][0]
        self.assertEqual(final['matchup_winner']['user_id'], '5')
        self.assertEqual(final['matchup_loser']['user_id'], '6')
        self.assertEqual(final['title_holder'], final['matchup_loser'])
        stats = {s['user_id']: s for s in bowl['leaderboard']}
        self.assertEqual(stats['6']['titles'], 1)
        self.assertEqual(stats['5']['titles'], 0)
        self.assertEqual(stats['5']['final_wins'], 1)
        self.assertEqual(stats['6']['final_losses'], 1)
        self.assertEqual(stats['5']['final_appearances'], 1)
        self.assertFalse(bowl['regular_season_last_place_included'])

    def test_official_rule_normalizes_reversed_source_outcome(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=1),
            dict(roster_id=6, matchup_id=3, points=100)])
        self.load()
        final = championship_report(self.path)['toilet_bowl']['history'][0]
        self.assertEqual(final['final_series']['winner_roster_id'], 5)  # raw advancement
        self.assertEqual(final['matchup_loser']['roster_id'], 5)
        self.assertEqual(final['title_holder']['user_id'], '5')
        self.assertEqual(final['matchup_winner']['user_id'], '6')

    def test_official_rule_multiweek_duplicate_and_correction(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=100), dict(roster_id=6, matchup_id=3, points=0)])
        self.payload['matchups']['16'].extend([
            dict(roster_id=5, matchup_id=3, points=0), dict(roster_id=6, matchup_id=3, points=200)])
        self.load()
        self.load()
        bowl = championship_report(self.path)['toilet_bowl']
        self.assertEqual(sum(s['titles'] for s in bowl['leaderboard']), 1)
        self.assertEqual(bowl['history'][0]['title_holder']['user_id'], '5')
        # Correct only source encoding: actual higher/lower totals remain fixed.
        self.payload['losers'][0].update(w=6, l=5)
        self.load()
        self.assertEqual(championship_report(self.path)['toilet_bowl']['history'][0]['title_holder']['user_id'], '5')

    def test_official_rule_ambiguous_data_stays_unresolved(self):
        self.load()
        final = championship_report(self.path)['toilet_bowl']['history'][0]
        self.assertEqual(final['status'], 'unresolved')
        self.assertIsNone(final['title_holder'])
        self.assertEqual(sum(s['titles'] for s in championship_report(self.path)['toilet_bowl']['leaderboard']), 0)

    def test_official_rule_historical_identity_and_departed_manager(self):
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=1), dict(roster_id=6, matchup_id=3, points=100)])
        newer = copy.deepcopy(self.payload)
        newer['league'].update(season='2021', league_id='2021')
        newer['rosters'][4]['owner_id'] = 'new-owner'
        newer['users'].append(dict(user_id='new-owner', display_name='Replacement'))
        self.client.payloads.append(newer)
        self.load()
        bowl = championship_report(self.path)['toilet_bowl']
        self.assertEqual([r['title_holder']['user_id'] for r in bowl['history']], ['5', 'new-owner'])
        self.assertEqual(bowl['history'][0]['title_holder']['display_name'], 'Name 2020-5')
        self.assertEqual({s['user_id']: s['titles'] for s in bowl['leaderboard']}['5'], 1)

    def test_toilet_bowl_required_validation_detects_unresolved_and_missing_years(self):
        self.load()
        process = subprocess.run([sys.executable, 'scripts/validate_championships.py', '--database', str(self.path),
                                  '--require-toilet-bowl', '--through-season', '2025'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        errors = json.loads(process.stdout)['errors']
        self.assertTrue(any('title unresolved' in e for e in errors))
        self.assertTrue(any('2025: required season not imported' in e for e in errors))

    def seed_regular_standings(self):
        for row in self.payload['rosters']:
            roster = row['roster_id']
            row['settings'] = dict(wins=7-roster, losses=roster, ties=0,
                                   fpts=1000-roster, fpts_decimal=0,
                                   fpts_against=1000, fpts_against_decimal=0)

    def test_regular_season_last_place_and_toilet_title_are_independent(self):
        self.seed_regular_standings()  # roster 6 finishes last in regular season
        self.payload['matchups']['15'].extend([
            dict(roster_id=5, matchup_id=3, points=1), dict(roster_id=6, matchup_id=3, points=100)])
        self.load()
        report_data = championship_report(self.path)
        self.assertEqual(report_data['regular_season']['history'][0]['last_place']['user_id'], '6')
        self.assertEqual(report_data['toilet_bowl']['history'][0]['title_holder']['user_id'], '5')
        stats = {s['user_id']: s for s in report_data['regular_season']['leaderboard']}
        self.assertEqual(stats['6']['last_place_finishes'], 1)
        self.assertEqual(stats['5']['last_place_finishes'], 0)
        bowl = {s['user_id']: s for s in report_data['toilet_bowl']['leaderboard']}
        self.assertEqual(bowl['6']['titles'], 0)
        self.assertEqual(bowl['5']['titles'], 1)
        self.load()
        self.assertEqual(championship_report(self.path)['regular_season']['leaderboard'][0]['last_place_finishes'], 1)

    def test_regular_standings_tiebreaks_and_unresolved_exact_tie(self):
        self.seed_regular_standings()
        self.payload['rosters'][-2]['settings'] = dict(self.payload['rosters'][-1]['settings'], fpts_decimal=1)
        year = season_history(self.payload)['regular_season_standings']
        self.assertEqual(year['last_place']['user_id'], '6')
        self.payload['rosters'][-2]['settings']['fpts_decimal'] = 0
        self.payload['rosters'][-2]['settings']['fpts_against_decimal'] = 1
        year = season_history(self.payload)['regular_season_standings']
        self.assertEqual(year['last_place']['user_id'], '6')
        self.payload['rosters'][-2]['settings']['fpts_against_decimal'] = 0
        year = season_history(self.payload)['regular_season_standings']
        self.assertEqual(year['status'], 'unresolved')
        self.assertIsNone(year['last_place'])

    def test_regular_standings_missing_and_unequal_records_are_not_guessed(self):
        self.assertEqual(season_history(self.payload)['regular_season_standings']['status'], 'unresolved')
        self.seed_regular_standings()
        self.payload['rosters'][0]['settings']['wins'] += 1
        self.assertEqual(season_history(self.payload)['regular_season_standings']['status'], 'unresolved')
        self.payload['league']['total_rosters'] = 10
        self.assertIn('incomplete_regular_season_roster_count', season_history(self.payload)['regular_season_standings']['issues'])

    def test_multi_week_final_is_one_series(self):
        self.payload = fixture(multi=True)
        self.client.payloads = [self.payload]
        self.load()
        data = championship_report(self.path)
        final = data['champions_by_season'][0]['championship_series']
        self.assertEqual(final['score_check']['weeks'], [15, 16])
        self.assertEqual(final['score_check']['totals'], [20, 15])
        self.assertEqual(data['leaderboard'][0]['championships'], 1)
        self.assertEqual(data['championship_head_to_head'][0]['appearances'], 1)
        self.assertEqual(data['leaderboard'][0]['series_wins'], 2)

    def test_bracket_winner_authoritative_on_score_disagreement(self):
        self.payload['matchups']['16'][0]['points'] = -100
        self.load()
        year = championship_report(self.path)['champions_by_season'][0]
        self.assertEqual(year['champion']['user_id'], '1')
        self.assertEqual(year['championship_series']['score_check']['status'], 'observed_disagreement')
        self.assertTrue(any('score_disagreement' in issue for issue in year['issues']))

    def test_custom_zero_scores_and_ties_do_not_override_bracket(self):
        self.payload['matchups']['16'][0]['custom_points'] = 0
        self.payload['matchups']['16'][1]['custom_points'] = 0
        year = season_history(self.payload)
        self.assertEqual(year['championship_series']['score_check']['status'], 'observed_tie')
        self.assertEqual(year['champion']['user_id'], '1')

    def test_incomplete_final_never_infers_winner(self):
        self.payload['winners'][2].update(w=None, l=None)
        self.load()
        data = championship_report(self.path)
        self.assertIsNone(data['champions_by_season'][0]['champion'])
        self.assertEqual(data['coverage']['unresolved_seasons'], [2020])
        self.assertEqual(sum(s['championships'] for s in data['leaderboard']), 0)
        self.assertEqual(data['leaderboard'][0]['championship_appearances'], 1)
        self.assertTrue(all(s['championship_drought'] is None for s in data['leaderboard']))

    def test_missing_ambiguous_and_malformed_brackets(self):
        for winners in ([], None, [dict(m=1, r=1, t1=1, t2=2, w=1, l=2)],
                        self.payload['winners'] + [dict(self.payload['winners'][2], m=99)],
                        [dict(m=1, r=1, t1=1, t2=2, w=3, l=2, p=1)],
                        [dict(m=1, r='bad', t1=1, t2=2, w=1, l=2, p=1)]):
            payload = copy.deepcopy(self.payload)
            payload['winners'] = winners
            self.assertIsNone(season_history(payload)['champion'])

    def test_graph_references_byes_and_different_formats(self):
        for size in (4, 6, 8):
            payload = fixture()
            payload['users'] = [dict(user_id=str(i), display_name=str(i)) for i in range(1, size + 1)]
            payload['rosters'] = [dict(roster_id=i, owner_id=str(i)) for i in range(1, size + 1)]
            payload['league']['settings']['playoff_teams'] = size
            if size == 6:
                payload['winners'] = [dict(m=1, r=1, t1=3, t2=6, w=3, l=6), dict(m=2, r=1, t1=4, t2=5, w=4, l=5),
                    dict(m=3, r=2, t1=1, t2={'w': 1}, w=1, l=3), dict(m=4, r=2, t1=2, t2={'w': 2}, w=2, l=4),
                    dict(m=5, r=3, t1={'w': 3}, t2={'w': 4}, w=1, l=2, p=1)]
            if size == 8:
                payload['winners'] = [dict(m=i, r=1, t1=i, t2=9-i, w=i, l=9-i) for i in range(1, 5)] + [
                    dict(m=5, r=2, t1={'w': 1}, t2={'w': 4}, w=1, l=4),
                    dict(m=6, r=2, t1={'w': 2}, t2={'w': 3}, w=2, l=3),
                    dict(m=7, r=3, t1={'w': 5}, t2={'w': 6}, w=1, l=2, p=1)]
            result = season_history(payload)
            self.assertEqual(result['champion']['user_id'], '1')
            self.assertEqual(len(result['participants']), size)

    def test_invalid_graph_and_duplicate_round_teams_are_rejected(self):
        for changes in ('cycle', 'wrong_reference', 'duplicate', 'missing_ancestor'):
            payload = copy.deepcopy(self.payload)
            if changes == 'cycle':
                payload['winners'][0]['t1_from'] = {'w': 3}
            elif changes == 'wrong_reference':
                payload['winners'][2]['t1_from'] = {'l': 1}
            elif changes == 'duplicate':
                payload['winners'][1].update(t1=1, w=1)
            else:
                payload['winners'][2]['t1_from'] = {'w': 99}
            self.assertIsNone(season_history(payload)['champion'])

    def test_departed_managers_and_roster_reuse_preserve_historical_names(self):
        newer = fixture(2021)
        newer['rosters'][0]['owner_id'] = '7'
        newer['users'].append(dict(user_id='7', display_name='New champion'))
        self.client.payloads.append(newer)
        self.load()
        data = championship_report(self.path)
        self.assertEqual([s['champion']['user_id'] for s in data['champions_by_season']], ['1', '7'])
        self.assertEqual(data['champions_by_season'][0]['champion']['display_name'], 'Name 2020-1')
        self.assertEqual({s['user_id']: s for s in data['leaderboard']}['1']['championships'], 1)

    def test_duplicate_imports_and_corrections_keep_audit_history(self):
        self.load()
        self.load()
        self.assertEqual(self.query('SELECT COUNT(*) FROM playoff_snapshots'), [(1,)])
        self.payload['winners'][2].update(w=2, l=1)
        self.load()
        self.assertEqual(self.query('SELECT COUNT(*) FROM playoff_snapshots'), [(2,)])
        self.assertEqual(championship_report(self.path)['champions_by_season'][0]['champion']['user_id'], '2')

    def test_fetch_failure_preserves_previous_snapshots(self):
        self.load()
        before = self.query('SELECT * FROM playoff_seasons')
        self.client.fail = True
        with self.assertRaises(RuntimeError):
            self.load()
        self.assertEqual(self.query('SELECT * FROM playoff_seasons'), before)

    def test_completed_only_from_2020_and_safe_database(self):
        old, current = fixture(2019), fixture(2026)
        current['league']['status'] = 'in_season'
        self.client.payloads += [old, current]
        summary = self.load()
        self.assertEqual(summary['imported_seasons'], [2020])
        self.assertEqual(len(self.client.calls), 2)
        with self.assertRaises(ValueError):
            validation_database(DATABASE_PATH)
        with self.assertRaises(ValueError):
            validation_database(None)

    def test_streaks_droughts_unknown_year_and_season_filter(self):
        self.client.payloads += [fixture(2021), fixture(2022), fixture(2023)]
        self.load()
        stats = {s['user_id']: s for s in championship_report(self.path)['leaderboard']}
        self.assertEqual(stats['1']['longest_consecutive_championships'], 4)
        self.assertEqual(stats['2']['championship_drought'], 4)
        self.assertEqual(championship_report(self.path, 2022)['leaderboard'][0]['championships'], 1)
        self.client.payloads.append(fixture(2025))
        self.load()
        result = championship_report(self.path)
        self.assertEqual(result['coverage']['missing_seasons'], [2024])
        self.assertEqual(result['leaderboard'][0]['longest_consecutive_championships'], 4)
        self.assertIsNone({s['user_id']: s for s in result['leaderboard']}['2']['championship_drought'])
        self.assertTrue(any(s['kind'] == 'consecutive_championships' for s in result['storylines']))

    def test_missing_owner_does_not_guess_identity(self):
        self.payload['rosters'][0]['owner_id'] = None
        self.load()
        result = championship_report(self.path)
        self.assertIsNone(result['champions_by_season'][0]['champion']['user_id'])
        self.assertEqual(sum(s['championships'] for s in result['leaderboard']), 0)

    def test_old_database_report_is_additive_and_empty(self):
        create_tables(self.path)
        connection = get_connection(self.path)
        try:
            connection.execute('DROP TABLE playoff_seasons')
            connection.execute('DROP TABLE playoff_snapshots')
            connection.commit()
        finally:
            connection.close()
        data = report(self.path)
        self.assertIn('managers', data)
        self.assertEqual(data['championships']['schema_version'], 1)
        self.assertEqual(data['championships']['leaderboard'], [])

    def test_json_cli_and_protected_original_cli(self):
        self.load()
        result = subprocess.run([sys.executable, 'scripts/report.py', '--database', str(self.path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['championships']['record_unit'], 'playoff_series')
        result = subprocess.run([sys.executable, 'scripts/import_championships.py', '--database', str(DATABASE_PATH)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('protected', result.stderr)

    def test_schema_contract_and_validator_cli(self):
        self.load()
        data = championship_report(self.path)
        self.assertEqual(set(data), {'schema_version', 'record_unit', 'coverage',
            'champions_by_season', 'leaderboard', 'championship_head_to_head', 'storylines', 'consolation', 'toilet_bowl', 'regular_season'})
        self.assertEqual(set(data['coverage']), {'imported_seasons', 'missing_seasons',
            'unresolved_seasons', 'live_verification'})
        process = subprocess.run([sys.executable, 'scripts/validate_championships.py', '--database', str(self.path)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['errors'], [])
        self.payload['winners'][2].update(w=None, l=None)
        self.load()
        process = subprocess.run([sys.executable, 'scripts/validate_championships.py', '--database', str(self.path)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(json.loads(process.stdout)['errors'])

    def test_direct_loser_cannot_reenter_title_game(self):
        self.payload['winners'][2] = dict(m=3, r=2, t1=4, t2=2, w=4, l=2, p=1)
        self.payload['winners'] = self.payload['winners'][:3]
        year = season_history(self.payload)
        self.assertIsNone(year['champion'])
        self.assertIn('championship_final_has_loser_path', year['issues'])

    def test_missing_weeks_and_repeated_pair_are_not_guessed(self):
        self.payload['matchups'] = {}
        year = season_history(self.payload)
        self.assertEqual(year['championship_series']['score_check']['status'], 'unavailable')
        self.assertEqual(year['champion']['user_id'], '1')
        self.payload['winners'].append(dict(m=5, r=3, t1=1, t2=2, w=1, l=2, p=5))
        year = season_history(self.payload)
        self.assertEqual(year['championship_series']['score_check']['status'], 'ambiguous_pair')

    def test_official_endpoints(self):
        client = SleeperClient()
        client._get = Mock(return_value=[])
        client.get_playoff_bracket('league', 'winners')
        client._get.assert_called_with('league/league/winners_bracket')
        client.get_playoff_bracket('league', 'losers')
        client._get.assert_called_with('league/league/losers_bracket')
        with self.assertRaises(ValueError):
            client.get_playoff_bracket('league', 'other')


if __name__ == '__main__':
    unittest.main()
