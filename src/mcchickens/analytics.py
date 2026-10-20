"""Deterministic weekly analytics using stable season-specific manager identities."""
from collections import defaultdict
from itertools import groupby

from .database import get_connection


def results(database_path=None, season=None, include_playoffs=False):
    """Return one perspective per manager per valid completed weekly contest."""
    connection = get_connection(database_path)
    try:
        rows = connection.execute('''
            SELECT m.season, m.week, m.matchup_id, m.roster_id, sm.user_id,
                   m.points, m.is_playoff
            FROM matchups m LEFT JOIN season_managers sm
              ON sm.season=m.season AND sm.roster_id=m.roster_id
            WHERE m.is_complete=1
            ORDER BY m.season, m.week, m.matchup_id, m.roster_id
        ''').fetchall()
    finally:
        connection.close()
    output = []
    for key, members in groupby(rows, key=lambda r: r[:3]):
        pair = list(members)
        if key[2] is None or len(pair) != 2:
            continue
        if season is not None and key[0] != season:
            continue
        if any(r[4] is None or r[5] is None for r in pair):
            continue
        if pair[0][4] == pair[1][4] or pair[0][6] != pair[1][6]:
            continue
        if not include_playoffs and pair[0][6]:
            continue
        for own, other in (pair, pair[::-1]):
            output.append(dict(season=own[0], week=own[1], matchup_id=own[2],
                               user_id=own[4], opponent_id=other[4], points=own[5],
                               points_against=other[5], is_playoff=bool(own[6]),
                               result='W' if own[5] > other[5] else 'L' if own[5] < other[5] else 'T'))
    return output


def _totals(games):
    stats = dict(games=len(games), wins=0, losses=0, ties=0,
                 points_for=0.0, points_against=0.0)
    for game in games:
        stats[{'W': 'wins', 'L': 'losses', 'T': 'ties'}[game['result']]] += 1
        stats['points_for'] += game['points']
        stats['points_against'] += game['points_against']
    stats['win_percentage'] = (stats['wins'] + stats['ties'] / 2) / len(games) if games else 0.0
    stats['average_points'] = stats['points_for'] / len(games) if games else 0.0
    return stats


def manager_statistics(games):
    grouped = defaultdict(list)
    for game in games:
        grouped[game['user_id']].append(game)
    return {user: _totals(rows) for user, rows in sorted(grouped.items())}


def head_to_head(games):
    """Directional records, keyed by (manager, opponent)."""
    grouped = defaultdict(list)
    for game in games:
        grouped[game['user_id'], game['opponent_id']].append(game)
    return {pair: _totals(rows) for pair, rows in sorted(grouped.items())}


def streaks(games):
    """Ties break win/loss streaks; gaps and offseason do not break them."""
    grouped = defaultdict(list)
    for game in games:
        grouped[game['user_id']].append(game)
    output = {}
    for user, rows in sorted(grouped.items()):
        runs = [(result, len(list(run))) for result, run in groupby(
            sorted(rows, key=lambda g: (g['season'], g['week'])), key=lambda g: g['result'])]
        output[user] = dict(current_result=runs[-1][0], current_length=runs[-1][1],
                            longest_win=max((n for r, n in runs if r == 'W'), default=0),
                            longest_loss=max((n for r, n in runs if r == 'L'), default=0))
    return output


def league_records(games):
    """Return every tied record holder, with weekly context."""
    if not games:
        return {}
    definitions = {
        'highest_score': (lambda g: g['points'], max),
        'lowest_score': (lambda g: g['points'], min),
        'largest_margin': (lambda g: g['points'] - g['points_against'], max),
        'closest_game': (lambda g: abs(g['points'] - g['points_against']), min),
    }
    output = {}
    for name, (value, aggregate) in definitions.items():
        candidates = games
        if name in ('largest_margin', 'closest_game'):
            candidates = [g for g in games if g['user_id'] < g['opponent_id']]
        metric = (lambda g: abs(g['points'] - g['points_against'])) if name == 'largest_margin' else value
        best = aggregate(metric(g) for g in candidates)
        output[name] = dict(value=best, holders=[g for g in candidates if metric(g) == best])
    return output


def milestones(games, thresholds=(10, 25, 50, 100)):
    """Exact career game/win threshold crossings, derived afresh after corrections."""
    if any(n <= 0 for n in thresholds):
        raise ValueError('Milestone thresholds must be positive')
    counters = defaultdict(lambda: dict(games=0, wins=0))
    output = []
    for game in sorted(games, key=lambda g: (g['season'], g['week'], g['user_id'])):
        totals = counters[game['user_id']]
        for metric in ('games', 'wins'):
            if metric == 'wins' and game['result'] != 'W':
                continue
            totals[metric] += 1
            if totals[metric] in thresholds:
                output.append(dict(user_id=game['user_id'], season=game['season'], week=game['week'],
                                   metric=metric, value=totals[metric]))
    return output


def storylines(games):
    """Structured statistical facts for the latest completed week, without prose AI."""
    if not games:
        return []
    latest = max((g['season'], g['week']) for g in games)
    output = []
    records = league_records(games)
    for name, record in records.items():
        for holder in record['holders']:
            if (holder['season'], holder['week']) == latest:
                output.append(dict(kind='record', record=name, value=record['value'], **holder))
    for user, run in streaks(games).items():
        if run['current_length'] >= 3 and any(
            g['user_id'] == user and (g['season'], g['week']) == latest for g in games
        ):
            output.append(dict(kind='streak', user_id=user, result=run['current_result'],
                               length=run['current_length'], season=latest[0], week=latest[1]))
    output.extend(dict(kind='milestone', **event) for event in milestones(games)
                  if (event['season'], event['week']) == latest)
    return output


def report(database_path=None, season=None, include_playoffs=False):
    games = results(database_path, season, include_playoffs)
    return dict(managers=manager_statistics(games),
                head_to_head=[dict(user_id=a, opponent_id=b, **stats)
                              for (a, b), stats in head_to_head(games).items()],
                streaks=streaks(games), records=league_records(games), milestones=milestones(games),
                storylines=storylines(games))
