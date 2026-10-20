"""Authoritative bracket series analytics; never infer a title from weekly scores."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import json

from .database import get_connection
from .standings import standings, regular_season_totals


def _positive(value):
    return type(value) is int and value > 0


def _identities(payload):
    users = {u['user_id']: u for u in payload['users'] if isinstance(u, dict) and u.get('user_id')}
    rosters = defaultdict(list)
    owner_counts = Counter(r.get('owner_id') for r in payload['rosters'] if isinstance(r, dict))
    for row in payload['rosters']:
        if isinstance(row, dict) and _positive(row.get('roster_id')):
            rosters[row['roster_id']].append(row)
    output = {}
    for roster, rows in rosters.items():
        owner = rows[0].get('owner_id') if len(rows) == 1 else None
        if owner_counts[owner] > 1:
            owner = None
        user = users.get(owner, {})
        output[roster] = dict(roster_id=roster, user_id=owner,
                              display_name=user.get('display_name'),
                              team_name=(user.get('metadata') or {}).get('team_name'))
    return output


def _score_check(payload, teams, bracket):
    empty = dict(status='unavailable', weeks=[], totals=None,
                 scope='observed_paired_weeks_only')
    if any(t is None for t in teams):
        return empty
    # A pair appearing in multiple series cannot safely be assigned weekly scores.
    duplicates = 0
    for row in bracket:
        if isinstance(row, dict) and {row.get('t1') if _positive(row.get('t1')) else None,
                                     row.get('t2') if _positive(row.get('t2')) else None} == set(teams):
            duplicates += 1
    if duplicates > 1:
        return dict(empty, status='ambiguous_pair')
    totals = [Decimal(0), Decimal(0)]
    weeks = []
    for week, rows in sorted(payload['matchups'].items(), key=lambda item: int(item[0])):
        own = [[r for r in rows if isinstance(r, dict) and r.get('roster_id') == team] for team in teams]
        if any(len(r) != 1 for r in own):
            continue
        a, b = own[0][0], own[1][0]
        mid = a.get('matchup_id')
        if mid is None or mid != b.get('matchup_id'):
            continue
        if sum(isinstance(r, dict) and r.get('matchup_id') == mid for r in rows) != 2:
            continue
        scores = [r.get('custom_points') if r.get('custom_points') is not None else r.get('points') for r in (a, b)]
        try:
            values = [Decimal(str(v)) for v in scores]
            if not all(v.is_finite() for v in values):
                continue
        except InvalidOperation:
            continue
        totals = [a + b for a, b in zip(totals, values)]
        weeks.append(int(week))
    if not weeks:
        return empty
    return dict(status='observed', weeks=weeks, totals=[float(v) for v in totals],
                scope='observed_paired_weeks_only')


def _bracket(payload, kind, identities):
    raw = payload.get(kind)
    issues = []
    if not isinstance(raw, list) or not raw:
        return [], [f'{kind}:missing_or_empty_bracket']
    ids = [r.get('m') for r in raw if isinstance(r, dict)]
    if len(ids) != len(raw) or any(not _positive(m) for m in ids) or len(ids) != len(set(ids)):
        return [], [f'{kind}:invalid_or_duplicate_match_ids']
    nodes = {r['m']: r for r in raw}
    resolved = {}
    visiting = set()

    def resolve(mid):
        if mid in resolved:
            return resolved[mid]
        if mid in visiting or mid not in nodes:
            return None
        visiting.add(mid)
        row = nodes[mid]
        valid = _positive(row.get('r')) and (row.get('p') is None or _positive(row.get('p')))
        teams = []
        placement_path = _positive(row.get('p')) and row['p'] > 1
        for side in ('t1', 't2'):
            direct = row.get(side)
            ref = row.get(side + '_from', direct if isinstance(direct, dict) else None)
            team = direct if _positive(direct) else None
            if ref is not None:
                if not isinstance(ref, dict) or len(ref) != 1 or next(iter(ref), None) not in ('w', 'l'):
                    valid = False
                else:
                    result_key, previous = next(iter(ref.items()))
                    prior = resolve(previous) if _positive(previous) else None
                    if (prior is None or prior['status'] != 'final' or
                            not _positive(row.get('r')) or prior['round'] >= row['r']):
                        valid = False
                    else:
                        expected = prior['winner_roster_id'] if result_key == 'w' else prior['loser_roster_id']
                        if team is not None and team != expected:
                            valid = False
                        team = expected
                        placement_path = placement_path or result_key == 'l' or prior['category'] == 'placement'
            if team is not None and team not in identities:
                valid = False
            teams.append(team)
        winner, loser = row.get('w'), row.get('l')
        pending = winner is None and loser is None
        if all(t is not None for t in teams) and teams[0] == teams[1]:
            valid = False
        final = (not pending and all(_positive(t) for t in teams)
                 and _positive(winner) and _positive(loser) and winner != loser
                 and set(teams) == {winner, loser})
        status = 'final' if valid and final else 'pending' if valid and pending else 'invalid'
        check = dict(status='unavailable', weeks=[], totals=None,
                     scope='observed_paired_weeks_only')
        result = dict(bracket=kind, match_id=mid,
                      round=row['r'] if _positive(row.get('r')) else None,
                      placement=row['p'] if _positive(row.get('p')) else None,
                      outcome_semantics='official_bracket_w_l',
                      category='consolation' if kind == 'losers' else 'placement' if placement_path else 'advancement',
                      teams=[identities.get(t, dict(roster_id=t, user_id=None, display_name=None, team_name=None)) for t in teams],
                      winner_roster_id=winner if status == 'final' else None,
                      loser_roster_id=loser if status == 'final' else None,
                      status=status, score_check=check)
        resolved[mid] = result
        visiting.remove(mid)
        if status != 'final':
            issues.append(f'{kind}:{mid}:{status}')
        return result

    for mid in nodes:
        resolve(mid)
    # Some historical responses supply direct teams without *_from edges.
    # A roster that already lost cannot re-enter the title-advancement path.
    ordered = sorted(resolved.values(), key=lambda r: (r['round'] or 0, r['match_id']))
    for result in ordered:
        if kind != 'winners' or result['round'] is None:
            continue
        for team in result['teams']:
            previous = [r for r in ordered if r['round'] is not None and r['round'] < result['round']
                        and any(t['roster_id'] == team['roster_id'] for t in r['teams'])]
            if previous:
                prior = max(previous, key=lambda r: r['round'])
                if prior['status'] == 'final' and (prior['loser_roster_id'] == team['roster_id'] or prior['category'] == 'placement'):
                    result['category'] = 'placement'
    # Validate exclusive team slots within a round, including resolved references.
    slots = Counter((r['round'], t['roster_id']) for r in resolved.values()
                    for t in r['teams'] if t['roster_id'] is not None)
    for result in resolved.values():
        if any(slots[result['round'], t['roster_id']] > 1 for t in result['teams'] if t['roster_id'] is not None):
            result.update(status='invalid', winner_roster_id=None, loser_roster_id=None)
            issues.append(f"{kind}:{result['match_id']}:duplicate_round_participant")
    # Propagate invalid ancestors so a contradictory semifinal cannot award a title.
    changed = True
    while changed:
        changed = False
        for mid, result in resolved.items():
            for side in ('t1', 't2'):
                ref = nodes[mid].get(side + '_from', nodes[mid].get(side))
                if isinstance(ref, dict) and len(ref) == 1:
                    previous = next(iter(ref.values()))
                    prior = resolved.get(previous) if _positive(previous) else None
                    if result['status'] != 'invalid' and (prior is None or prior['status'] != 'final'):
                        result.update(status='invalid', winner_roster_id=None, loser_roster_id=None)
                        issues.append(f'{kind}:{mid}:invalid_ancestor')
                        changed = True
    pair_rows = [dict(t1=r['teams'][0]['roster_id'], t2=r['teams'][1]['roster_id']) for r in resolved.values()]
    for result in resolved.values():
        teams = [t['roster_id'] for t in result['teams']]
        check = _score_check(payload, teams, pair_rows)
        if result['status'] == 'final' and check['totals'] is not None:
            a, b = check['totals']
            expected = teams[0] if a > b else teams[1] if b > a else None
            check['status'] = 'observed_tie' if expected is None else 'observed_agreement' if expected == result['winner_roster_id'] else 'observed_disagreement'
            if kind == 'losers' and expected is not None:
                # A toilet bowl can advance the lower-scoring roster. Preserve
                # official w/l without claiming it is a league win or placement.
                check['status'] = ('observed_source_w_higher' if expected == result['winner_roster_id']
                                   else 'observed_source_l_higher')
            if check['status'] == 'observed_disagreement':
                issues.append(f"{kind}:{result['match_id']}:score_disagreement_bracket_retained")
        result['score_check'] = check
    return sorted(resolved.values(), key=lambda r: (r['round'] if _positive(r['round']) else 0, r['match_id'])), issues


def consolation_history(series):
    """Classify source advancement from observed aggregate scores, not enum guesses.

    Unknown/tied/mixed evidence never awards a toilet-bowl last-place finish.
    Source w/l remain available even when the bracket format is unconfirmed.
    """
    finals = [r for r in series if r['placement'] == 1]
    final = finals[0] if len(finals) == 1 else None
    finalized = [r for r in series if r['status'] == 'final']
    evidence = {r['score_check']['status'] for r in finalized}
    complete_evidence = bool(finalized) and len(finalized) == len(series)
    mode = 'unknown'
    if complete_evidence and evidence == {'observed_source_l_higher'}:
        mode = 'toilet_bowl'
    elif complete_evidence and evidence == {'observed_source_w_higher'}:
        mode = 'consolation'
    participants = {t['roster_id']: t for r in series for t in r['teams'] if t['roster_id'] is not None}
    terminal = None
    if final and final['status'] == 'final':
        terminal = next(t for t in final['teams'] if t['roster_id'] == final['winner_roster_id'])
    return dict(format=mode, format_basis='observed_aggregate_score_order',
                source_settings_are_preserved=True,
                status='final' if terminal is not None and mode != 'unknown' else 'unresolved',
                participants=[participants[k] for k in sorted(participants)],
                final_series=final,
                toilet_bowl_last_place=terminal if mode == 'toilet_bowl' else None,
                consolation_winner=terminal if mode == 'consolation' else None,
                issues=[] if mode != 'unknown' else ['format_unconfirmed_missing_tied_or_mixed_score_evidence'])


def consolation_totals(timeline):
    totals = {}
    facts = []
    for year in timeline:
        history = year['consolation']
        for manager in history['participants']:
            user = manager['user_id']
            if user is None:
                continue
            stats = totals.setdefault(user, dict(user_id=user, latest_display_name=None,
                appearances=0, toilet_bowl_appearances=0, last_place_finishes=0,
                consolation_wins=0, source_w_results=0, source_l_results=0,
                higher_score_series_wins=0, lower_score_series_finishes=0, by_round={}))
            stats['latest_display_name'] = manager['display_name'] or stats['latest_display_name']
            stats['appearances'] += 1
            stats['toilet_bowl_appearances'] += int(history['format'] == 'toilet_bowl')
        for row in year['consolation_series']:
            if row['status'] != 'final':
                continue
            for manager in row['teams']:
                if manager['user_id'] not in totals:
                    continue
                stats = totals[manager['user_id']]
                source_w = manager['roster_id'] == row['winner_roster_id']
                key = 'source_w_results' if source_w else 'source_l_results'
                stats[key] += 1
                round_stats = stats['by_round'].setdefault(str(row['round']), dict(source_w_results=0, source_l_results=0))
                round_stats[key] += 1
                check = row['score_check']['status']
                if check in ('observed_source_w_higher', 'observed_source_l_higher'):
                    higher = source_w == (check == 'observed_source_w_higher')
                    stats['higher_score_series_wins' if higher else 'lower_score_series_finishes'] += 1
        for key, metric, kind in [('toilet_bowl_last_place', 'last_place_finishes', 'toilet_bowl_last_place'),
                                  ('consolation_winner', 'consolation_wins', 'consolation_won')]:
            manager = history[key]
            if manager and manager['user_id'] in totals:
                totals[manager['user_id']][metric] += 1
                facts.append(dict(kind=kind, season=year['season'], user_id=manager['user_id']))
    return dict(schema_version=1, record_unit='playoff_series',
                leaderboard=[totals[k] for k in sorted(totals)], storylines=facts)


def toilet_bowl_history(timeline):
    """McChickens: the actual final LOSER holds the title, never the winner.

    Sleeper source w/l can encode advancement toward last place. Normalize
    those fields only when observed aggregate evidence confirms their meaning.
    No score alone can award a title without a validated finalized bracket.
    """
    history, totals = [], {}
    h2h = defaultdict(lambda: dict(finals=0, wins=0, losses=0, titles=0))
    for year in timeline:
        consolation = year['consolation']
        final = consolation['final_series']
        orientation = consolation['format']
        entry = dict(season=year['season'], league_id=year['league_id'],
                     status='unresolved', rule='mcchickens_final_loser',
                     final_series=final, matchup_winner=None, matchup_loser=None,
                     title_holder=None, outcome_basis='official_bracket_with_observed_orientation',
                     issues=[])
        for manager in consolation['participants']:
            user = manager['user_id']
            if user is not None:
                stats = totals.setdefault(user, dict(user_id=user, latest_display_name=None,
                    titles=0, bracket_appearances=0, final_appearances=0,
                    final_wins=0, final_losses=0, series_wins=0, series_losses=0, by_round={}))
                stats['latest_display_name'] = manager['display_name'] or stats['latest_display_name']
                stats['bracket_appearances'] += 1
        if final and final['status'] in ('pending', 'final'):
            entrants = final['teams']
            if all(t['user_id'] is not None for t in entrants) and len({t['user_id'] for t in entrants}) == 2:
                for team in entrants:
                    totals[team['user_id']]['final_appearances'] += 1
        if not final or final['status'] != 'final':
            entry['issues'].append('missing_ambiguous_or_unfinalized_toilet_bowl_final')
        elif orientation == 'unknown':
            entry['issues'].append('bracket_outcome_orientation_unconfirmed')
        elif any(t['user_id'] is None for t in final['teams']):
            entry['issues'].append('historical_final_owner_unresolved')
        else:
            # For lower-score advancement, source w is the GAME LOSER.
            # For ordinary higher-score advancement, source l is the GAME LOSER.
            loser_roster = final['winner_roster_id'] if orientation == 'toilet_bowl' else final['loser_roster_id']
            loser = next(t for t in final['teams'] if t['roster_id'] == loser_roster)
            winner = next(t for t in final['teams'] if t['roster_id'] != loser_roster)
            entry.update(status='final', matchup_winner=winner, matchup_loser=loser,
                         title_holder=loser)
            totals[loser['user_id']]['titles'] += 1
            totals[loser['user_id']]['final_losses'] += 1
            totals[winner['user_id']]['final_wins'] += 1
            for own, other, lost in [(loser, winner, True), (winner, loser, False)]:
                stats = h2h[own['user_id'], other['user_id']]
                stats['finals'] += 1
                stats['losses' if lost else 'wins'] += 1
                stats['titles'] += int(lost)
        if orientation != 'unknown':
            for series in year['consolation_series']:
                if series['status'] != 'final':
                    continue
                loser_roster = series['winner_roster_id'] if orientation == 'toilet_bowl' else series['loser_roster_id']
                for team in series['teams']:
                    if team['user_id'] not in totals:
                        continue
                    metric = 'losses' if team['roster_id'] == loser_roster else 'wins'
                    totals[team['user_id']]['series_' + metric] += 1
                    round_stats = totals[team['user_id']]['by_round'].setdefault(str(series['round']), dict(wins=0, losses=0))
                    round_stats[metric] += 1
        history.append(entry)
    return dict(schema_version=1, rule='mcchickens_final_loser', record_unit='playoff_series',
                regular_season_last_place_included=False, history=history,
                leaderboard=sorted(totals.values(), key=lambda t: (-t['titles'], -t['final_appearances'], t['user_id'])),
                head_to_head=[dict(user_id=a, opponent_id=b, **stats) for (a, b), stats in sorted(h2h.items())])


def season_history(payload):
    identities = _identities(payload)
    winners, issues = _bracket(payload, 'winners', identities)
    losers, loser_issues = _bracket(payload, 'losers', identities)
    issues += loser_issues
    settings = payload['league'].get('settings') or {}
    if not _positive(settings.get('playoff_week_start')):
        issues.append('missing_playoff_start_score_crosscheck_unavailable')
    finals = [r for r in winners if r['placement'] == 1]
    final = finals[0] if len(finals) == 1 else None
    if final is None:
        issues.append('missing_or_ambiguous_championship_final')
        for candidate in finals:
            candidate.update(status='invalid', winner_roster_id=None, loser_roster_id=None)
    if final and final['category'] != 'advancement':
        issues.append('championship_final_has_loser_path')
        final = None
    champion = runner = None
    if final and final['status'] == 'final':
        champion = identities[final['winner_roster_id']]
        runner = identities[final['loser_roster_id']]
    participants = {}
    for row in winners:
        for team in row['teams']:
            if team['roster_id'] in identities:
                participants[team['roster_id']] = team
    if settings.get('playoff_teams') != len(participants):
        issues.append('playoff_participant_count_unconfirmed')
    if any(team['user_id'] is None for team in participants.values()):
        issues.append('unmapped_or_ambiguous_playoff_owner')
    placements = defaultdict(set)
    for row in winners:
        if row['status'] == 'final' and _positive(row['placement']):
            placements[row['placement']].add(row['winner_roster_id'])
            placements[row['placement'] + 1].add(row['loser_roster_id'])
    roster_places = defaultdict(set)
    for place, rosters in placements.items():
        for roster in rosters:
            roster_places[roster].add(place)
    reliable = []
    for place, rosters in sorted(placements.items()):
        if len(rosters) == 1 and len(roster_places[next(iter(rosters))]) == 1:
            reliable.append(dict(place=place, manager=identities[next(iter(rosters))], bracket='winners'))
        else:
            issues.append('conflicting_final_placements')
    if champion is not None and any(
        len(roster_places[t['roster_id']]) != 1 for t in (champion, runner)
    ):
        issues.append('conflicting_championship_placements')
        champion = runner = None
        final.update(status='invalid', winner_roster_id=None, loser_roster_id=None)
    return dict(season=int(payload['league']['season']), league_id=payload['league']['league_id'],
                status='final' if champion is not None else 'unresolved',
                champion=champion, runner_up=runner, championship_series=final,
                participants=[participants[k] for k in sorted(participants)],
                series=winners, consolation_series=losers,
                consolation=consolation_history(losers), placements=reliable,
                settings=settings, regular_season_standings=standings(payload, identities),
                issues=sorted(set(issues)),
                managers=[identities[k] for k in sorted(identities)])


def championship_report(database_path=None, season=None):
    connection = get_connection(database_path)
    try:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name='playoff_seasons'").fetchone()
        sources = connection.execute('''SELECT s.payload, s.digest, s.fetched_at
            FROM playoff_seasons p JOIN playoff_snapshots s
            ON s.season=p.season AND s.digest=p.digest ORDER BY p.season''').fetchall() if exists else []
    finally:
        connection.close()
    timeline = []
    for encoded, digest, fetched in sources:
        item = season_history(json.loads(encoded))
        if season is None or item['season'] == season:
            item['source_digest'] = digest
            item['fetched_at'] = fetched
            timeline.append(item)
    leaderboard = {}
    for item in timeline:
        for manager in item['managers']:
            user = manager['user_id']
            if user is None:
                continue
            stats = leaderboard.setdefault(user, dict(user_id=user, latest_display_name=None,
                championships=0, championship_appearances=0, runner_up_finishes=0,
                playoff_appearances=0, series_wins=0, series_losses=0, by_round={},
                longest_consecutive_championships=0, current_consecutive_championships=0,
                championship_drought=None, drought_known_lower_bound=0, last_active_season=None))
            stats['latest_display_name'] = manager['display_name'] or stats['latest_display_name']
            stats['last_active_season'] = item['season']
        for team in item['participants']:
            if team['user_id'] in leaderboard:
                leaderboard[team['user_id']]['playoff_appearances'] += 1
        final = item['championship_series']
        if final and final['status'] in ('pending', 'final'):
            # An appearance requires two identified bracket entrants, not a winner.
            for team in final['teams']:
                if team['user_id'] in leaderboard and all(_positive(t['roster_id']) for t in final['teams']):
                    leaderboard[team['user_id']]['championship_appearances'] += 1
        for key, metric in [('champion', 'championships'), ('runner_up', 'runner_up_finishes')]:
            team = item[key]
            if team and team['user_id'] in leaderboard:
                leaderboard[team['user_id']][metric] += 1
        for series in item['series']:
            if series['status'] != 'final' or series['category'] != 'advancement':
                continue
            for team in series['teams']:
                if team['user_id'] not in leaderboard:
                    continue
                stats = leaderboard[team['user_id']]
                won = team['roster_id'] == series['winner_roster_id']
                stats['series_wins' if won else 'series_losses'] += 1
                totals = stats['by_round'].setdefault(str(series['round']), dict(wins=0, losses=0))
                totals['wins' if won else 'losses'] += 1
    by_year = {t['season']: t for t in timeline}
    for user, stats in leaderboard.items():
        run = longest = 0
        previous = None
        for item in timeline:
            champion = item['champion']
            champ_id = champion['user_id'] if champion else None
            if champ_id == user:
                run = run + 1 if previous == item['season'] - 1 else 1
                longest = max(longest, run)
            else:
                run = 0
            previous = item['season']
        active_years = [i['season'] for i in timeline if any(m['user_id'] == user for m in i['managers'])]
        drought = lower = 0
        uncertain = False
        for year in range(min(active_years), max(active_years) + 1):
            item = by_year.get(year)
            if item is None:
                uncertain = True
                lower = 0
                continue
            if year not in active_years:
                continue
            champion = item['champion']
            champ_id = champion['user_id'] if champion else None
            if champ_id == user:
                drought = lower = 0
                uncertain = False
            elif champ_id is None:
                uncertain = True
                lower = 0
            else:
                drought += 1
                lower += 1
        stats['longest_consecutive_championships'] = longest
        stats['current_consecutive_championships'] = run if timeline and timeline[-1]['champion'] and timeline[-1]['champion']['user_id'] else None
        stats['championship_drought'] = None if uncertain else drought
        stats['drought_known_lower_bound'] = lower
    h2h = defaultdict(lambda: dict(appearances=0, wins=0, losses=0, seasons=[]))
    for item in timeline:
        final = item['championship_series']
        if not final or final['status'] != 'final' or any(t['user_id'] is None for t in final['teams']):
            continue
        for own, other in (final['teams'], final['teams'][::-1]):
            stats = h2h[own['user_id'], other['user_id']]
            stats['appearances'] += 1
            stats['wins' if own['roster_id'] == final['winner_roster_id'] else 'losses'] += 1
            stats['seasons'].append(item['season'])
    facts = []
    for item in timeline:
        if item['champion'] and item['champion']['user_id']:
            facts.append(dict(kind='championship_won', season=item['season'], user_id=item['champion']['user_id']))
    for stats in leaderboard.values():
        if stats['longest_consecutive_championships'] >= 2:
            facts.append(dict(kind='consecutive_championships', user_id=stats['user_id'], count=stats['longest_consecutive_championships']))
        if stats['championship_drought'] is not None and stats['championship_drought'] >= 3:
            facts.append(dict(kind='championship_drought', user_id=stats['user_id'], count=stats['championship_drought']))
    years = sorted(by_year)
    expected = [season] if season is not None else list(range(2020, max(years) + 1)) if years else []
    return dict(schema_version=1, record_unit='playoff_series',
                coverage=dict(imported_seasons=years, missing_seasons=[y for y in expected if y not in by_year],
                              unresolved_seasons=[i['season'] for i in timeline if i['status'] != 'final'],
                              live_verification='not_certified_by_report'),
                champions_by_season=timeline,
                leaderboard=sorted(leaderboard.values(), key=lambda s: (-s['championships'], -s['championship_appearances'], s['user_id'])),
                championship_head_to_head=[dict(user_id=a, opponent_id=b, **stats) for (a, b), stats in sorted(h2h.items())],
                storylines=facts, consolation=consolation_totals(timeline),
                toilet_bowl=toilet_bowl_history(timeline),
                regular_season=regular_season_totals(timeline))
