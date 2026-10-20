"""Audit saved Sleeper snapshots; import fresh sources before running this CLI."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcchickens.championships import championship_report


def audit(data, require_toilet_bowl=False, required_seasons=()):
    errors, warnings, seasons = [], [], []
    coverage = data['coverage']
    if not coverage['imported_seasons']:
        errors.append('No completed championship seasons imported')
    if coverage['missing_seasons']:
        errors.append(f"Missing seasons: {coverage['missing_seasons']}")
    for year in required_seasons:
        if year not in coverage['imported_seasons']:
            errors.append(f'{year}: required season not imported')
    bowl_by_year = {row['season']: row for row in data['toilet_bowl']['history']}
    for item in data['champions_by_season']:
        year = item['season']
        if item['status'] != 'final':
            errors.append(f'{year}: championship unresolved')
        elif any(item[key]['user_id'] is None for key in ('champion', 'runner_up')):
            errors.append(f'{year}: championship owner attribution unresolved')
        checks = []
        for series in item['series']:
            label = f"{year}:winners:{series['match_id']}"
            check = series['score_check']['status']
            if series['status'] != 'final':
                errors.append(f'{label}: {series["status"]}')
            if check == 'observed_disagreement':
                errors.append(f'{label}: observed scores disagree; bracket retained')
            if check in ('unavailable', 'ambiguous_pair'):
                warnings.append(f'{label}: score check {check}')
            checks.append(check)
        warnings.extend(f'{year}:{issue}' for issue in item['issues']
                        if 'score_disagreement' not in issue)
        consolation = item['consolation']
        if consolation['status'] != 'final':
            warnings.append(f'{year}: consolation/toilet-bowl outcome unconfirmed')
        bowl = bowl_by_year[year]
        regular = item['regular_season_standings']
        if regular['status'] != 'final':
            warnings.append(f'{year}: regular-season last-place finish unresolved')
        if require_toilet_bowl:
            if bowl['status'] != 'final':
                errors.append(f'{year}: official Toilet Bowl title unresolved')
            elif (bowl['title_holder'] != bowl['matchup_loser'] or
                  bowl['title_holder']['user_id'] == bowl['matchup_winner']['user_id']):
                errors.append(f'{year}: Toilet Bowl loser-title rule violated')
        seasons.append(dict(season=year,
                            champion=item['champion'], runner_up=item['runner_up'],
                            source_digest=item['source_digest'], fetched_at=item['fetched_at'],
                            championship_score_check=(item['championship_series'] or {}).get('score_check'),
                            consolation_format=consolation['format'],
                            toilet_bowl_last_place=consolation['toilet_bowl_last_place'],
                            toilet_bowl_title_holder=bowl['title_holder'],
                            toilet_bowl_matchup_winner=bowl['matchup_winner'],
                            toilet_bowl_matchup_loser=bowl['matchup_loser'],
                            regular_season_last_place=regular['last_place'],
                            series_score_checks=checks))
    return dict(validation_scope='saved_official_brackets_and_observed_paired_scores',
                schedule_completeness_certified=False,
                errors=errors, warnings=warnings, seasons=seasons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--require-toilet-bowl', action='store_true')
    parser.add_argument('--from-season', type=int, default=2020)
    parser.add_argument('--through-season', type=int)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database not found; import championship history first')
    if args.through_season is not None and args.through_season < args.from_season:
        parser.error('--through-season must be at least --from-season')
    required = range(args.from_season, args.through_season + 1) if args.through_season is not None else ()
    result = audit(championship_report(args.database), args.require_toilet_bowl, required)
    print(json.dumps(result, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
