"""Regular-season standings from frozen Sleeper roster records, never playoffs."""
from decimal import Decimal, InvalidOperation


def standings(payload, identities):
    output = dict(status='unresolved', basis='sleeper_roster_regular_season_records',
                  ranking_rule='record_then_points_for_then_higher_points_against',
                  standings=[], last_place=None, issues=[])
    expected = payload['league'].get('total_rosters') or (payload['league'].get('settings') or {}).get('num_teams')
    if expected is not None and expected != len(payload['rosters']):
        output['issues'].append('incomplete_regular_season_roster_count')
        return output
    rows = []
    for roster in payload['rosters']:
        try:
            manager = identities[roster['roster_id']]
            settings = roster['settings']
            record = [settings[key] for key in ('wins', 'losses', 'ties')]
            if any(type(n) is not int or n < 0 for n in record):
                raise ValueError('Invalid record')
            wins, losses, ties = record
            if wins + losses + ties == 0:
                raise ValueError('No regular-season games')
            pf = Decimal(str(settings['fpts'])) + Decimal(str(settings.get('fpts_decimal', 0))) / 100
            pa = Decimal(str(settings['fpts_against'])) + Decimal(str(settings.get('fpts_against_decimal', 0))) / 100
            if not pf.is_finite() or not pa.is_finite() or manager['user_id'] is None:
                raise ValueError('Unknown points or owner')
            rows.append(((2 * wins + ties, pf, pa), dict(manager=manager, wins=wins, losses=losses,
                         ties=ties, points_for=float(pf), points_against=float(pa))))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            output['issues'].append('missing_or_invalid_regular_season_roster_data')
    if len(rows) != len(payload['rosters']) or not rows:
        return output
    if len({r['wins'] + r['losses'] + r['ties'] for _, r in rows}) != 1:
        output['issues'].append('unequal_regular_season_games')
        return output
    rows.sort(key=lambda pair: pair[0], reverse=True)
    previous = None
    rank = 0
    for index, (key, row) in enumerate(rows, 1):
        if key != previous:
            rank = index
        row['rank'] = rank
        output['standings'].append(row)
        previous = key
    candidates = [r for key, r in rows if key == rows[-1][0]]
    if len(candidates) != 1:
        output['issues'].append('unresolved_regular_season_last_place_tie')
        return output
    output.update(status='final', last_place=candidates[0]['manager'])
    return output


def regular_season_totals(timeline):
    totals = {}
    history = []
    for season in timeline:
        result = season['regular_season_standings']
        history.append(dict(season=season['season'], **result))
        for row in result['standings']:
            manager = row['manager']
            stats = totals.setdefault(manager['user_id'], dict(user_id=manager['user_id'],
                latest_display_name=None, seasons=0, last_place_finishes=0))
            stats['latest_display_name'] = manager['display_name'] or stats['latest_display_name']
            stats['seasons'] += 1
        if result['status'] == 'final':
            totals[result['last_place']['user_id']]['last_place_finishes'] += 1
    return dict(schema_version=1, record_unit='regular_season_standings', history=history,
                leaderboard=sorted(totals.values(), key=lambda s: (-s['last_place_finishes'], s['user_id'])))
