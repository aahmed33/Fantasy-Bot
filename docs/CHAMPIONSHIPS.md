# Championship JSON contract (version 1)

The report keeps its original `managers`, `head_to_head`, `streaks`, `records`,
`milestones` and `storylines` fields. It adds a `championships` object. Consumers
should tolerate additional fields; incompatible changes require a new
`championships.schema_version`. Arrays use deterministic ordering. Empty lists
and nulls retain their types when sources are absent. JSON is UTF-8 compatible.

## Championship object

| Field | Type / meaning |
| --- | --- |
| `schema_version` | Integer, currently 1 |
| `record_unit` | String, always `playoff_series` |
| `coverage` | Imported/missing/unresolved season integer arrays; `live_verification` is always `not_certified_by_report` |
| `champions_by_season` | Season timeline array, ascending year, including unresolved imported seasons |
| `leaderboard` | Manager totals array, championships descending, appearances descending, user ID ascending |
| `championship_head_to_head` | Directional championship series records, sorted by user ID/opponent ID |
| `storylines` | Structured championship facts, independent of weekly storylines |

`coverage.missing_seasons` checks 2020 through the latest imported completed
season. With `--season`, it checks only the requested season. With no imported
sources, arrays are empty and the validation CLI returns an error. The report
does not assume the current calendar season is finished. It cannot detect an
unlinked completed season later than the latest source; verify the root league
ID/history chain yourself. `--season` scopes all championship calculations;
filtered totals/runs/droughts describe that subset rather than an unfiltered
career. `--include-playoffs` does not change championship results.

## Season timeline entry

- `season` (integer), `league_id` (string), `status` (`final` or `unresolved`).
- `champion`, `runner_up`: manager objects or null. A valid roster with an
  unknown owner retains a manager object with a null `user_id`; no title is
  assigned to an invented manager.
- `championship_series`: unique `p:1` winners series or null. An incomplete
  final can retain known entrants but has no champion/runner-up.
- `participants`: known winners-bracket entrants, once per roster; includes
  bye teams resolved through later rounds. A count mismatch with
  `settings.playoff_teams` is diagnostic, not filled with inferred qualifiers.
- `series`: all winners-bracket series. `consolation_series`: all losers-bracket
  series; kept out of league-title and advancement W/L totals.
- `placements`: `{place: integer, manager: object, bracket: "winners"}` array.
  Only finalized, explicit, nonconflicting `p` results assign positions. No
  global positions are inferred from consolation/toilet-bowl bracket labels.
- `settings`: unmodified season league settings object.
- `issues`: sorted diagnostic string array. Unknown data is surfaced here.
- `managers`: season roster/owner snapshot, including non-playoff managers.
- `source_digest`: SHA-256 of canonical raw source JSON; `fetched_at`: first
  retrieval timestamp for that source revision in UTC ISO 8601 format.

Manager objects always contain `roster_id` (integer or null), `user_id` (string
or null), `display_name` and `team_name` (string or null). Owner IDs are read
from the **same season's** roster endpoint. Ambiguous roster/owner mappings
produce null identities. Missing user metadata does not erase a known owner ID.
Names are the values returned by the season endpoint at import time; earlier
renames cannot be reconstructed. Raw previous snapshots remain available.

## Series object

`bracket` is `winners` or `losers`; `match_id` and `round` are the official `m`
and `r` values (an invalid round becomes null). Match IDs are scoped to season
and bracket. `placement` is official `p` or null. `category` is `advancement`,
`placement` or `consolation`. `outcome_semantics` is `official_bracket_w_l`.
`teams` is an ordered pair of manager objects. `winner_roster_id` and
`loser_roster_id` preserve official w/l only when the validated result is final;
otherwise both are null. `status` is `final`, `pending` or `invalid`.

A unique title final must be on the advancement path. Pending/missing fields,
unknown teams, duplicate IDs/round slots, cycles, contradictory references and
invalid winner/loser pairs cannot manufacture a champion. A tie in observed
scores does not override an official winner (Sleeper can resolve playoff ties).
In the toilet bowl, source w/l may describe lower-score advancement. These
values must not be interpreted as championship victories or global placement.

`score_check` contains:

- `status`: `unavailable`, `ambiguous_pair`, `observed`, `observed_agreement`,
  `observed_disagreement`, `observed_tie`, `observed_source_w_higher`, or
  `observed_source_l_higher`. The last two are descriptive consolation checks.
- `weeks`: observed paired week integer array, ascending. A pair must occur
  only once in its bracket to associate weekly scores with that series.
- `totals`: two aggregated numeric scores in team order, or null. Use
  commissioner `custom_points` when present, including zero; otherwise use
  `points`. Non-finite/missing scores and non-paired groups are excluded.
- `scope`: always `observed_paired_weeks_only`. All playoff weeks from the
  season-specific start through the NFL regular-season end are fetched. No
  undocumented `playoff_round_type` mapping is assumed. Expected week counts
  and schedule completeness are deliberately not certified. Review the weeks
  against Sleeper, especially when diagnosing missing scores or repeat pairs.

## Manager and head-to-head totals

Each leaderboard item contains `user_id`, `latest_display_name`,
`last_active_season`, `championships`, `championship_appearances`,
`runner_up_finishes`, `playoff_appearances`, `series_wins`, `series_losses`,
`by_round`, `longest_consecutive_championships`,
`current_consecutive_championships`, `championship_drought`, and
`drought_known_lower_bound`.

An appearance needs known entrants in a pending or finalized unique final.
Titles and runner-up finishes require a finalized valid result. Playoff
appearances count known winners-bracket participation once per season, including
byes. Series wins/losses count only finalized title-advancement series; placement
and consolation are excluded. `by_round` maps official round numbers, encoded
as string keys, to `{wins: integer, losses: integer}`. Round numbers are
format-specific; round 1 in a four-team bracket differs from round 1 in a
six-team bracket. Weekly W/L fields in the existing report remain weekly.

Consecutive titles are confirmed adjacent calendar seasons. Unknown or missing
years break confirmed runs. Current runs are null when the latest champion's
identity is unknown. Drought is the number of known active seasons without a
title after the latest title (or since first observed membership for a manager
without a title), through that manager's last active completed season. Departed
managers do not accrue seasons after leaving. An unknown winner or missing
season since the last title makes exact drought null;
`drought_known_lower_bound` counts known active non-title seasons after the last
unknown. This is bounded by imported history, not a claim about pre-2020 titles.

Head-to-head items contain `user_id`, `opponent_id`, `appearances`, `wins`,
`losses` and ascending `seasons`. They count finalized title series with both
owner identities known, once per final, regardless of its weekly duration.

Storyline kinds are `championship_won` (user ID, season),
`consecutive_championships` (user ID, count >=2), and `championship_drought`
(user ID, known exact count >=3). No narrative model is involved.

## Source and operational validation

The official endpoint reference is [Sleeper API brackets](https://docs.sleeper.com/#getting-the-playoff-bracket).
[Sleeper describes aggregate two-week finals](https://sleeper.com/blog/how-do-fantasy-playoffs-work/)
and [different consolation/toilet-bowl advancement](https://support.sleeper.com/en/articles/2203534-consolation-bracket-vs-toilet-bowl).
We preserve the official results rather than reconstruct winners from scores.

Use the import/report/validation commands in README. To independently inspect
an imported season's official bracket and settings in PowerShell:

```powershell
$history = (& .venv/Scripts/python.exe scripts/report.py --database data/championship-validation-20261020.db | ConvertFrom-Json)
$seasonSource = $history.championships.champions_by_season | Where-Object season -eq 2020
$seasonLeagueId = $seasonSource.league_id
Invoke-RestMethod "https://api.sleeper.app/v1/league/$seasonLeagueId/winners_bracket"
Invoke-RestMethod "https://api.sleeper.app/v1/league/$seasonLeagueId/losers_bracket"
Invoke-RestMethod "https://api.sleeper.app/v1/league/$seasonLeagueId"
Invoke-RestMethod "https://api.sleeper.app/v1/league/$seasonLeagueId/matchups/16"
```

For another season/format, select its year and the weeks listed in
`championship_series.score_check.weeks`. Inspect raw `t1`/`t2`, `w`/`l`, `p:1`,
settings and aggregate scores. The validation CLI audits saved snapshots rather
than making new HTTP requests: reimport to refresh the evidence. It never marks
schedule completeness or human acceptance as certified.


## Additive toilet-bowl/consolation fields (schema version 1)

Each season adds `consolation`: `format` (`toilet_bowl`, `consolation`, `unknown`),
`format_basis` (`observed_aggregate_score_order`),
`source_settings_are_preserved` (true), `status` (`final` or `unresolved`),
`participants`, `final_series`, `toilet_bowl_last_place`, `consolation_winner`
and `issues`. Final/outcome fields are objects or null. The raw source and
season settings remain available in the snapshot and timeline.

Only consistent, decisive observed aggregate scores across all finalized
losers-bracket series classify the format. Source w consistently representing
the lower-scoring team identifies observed toilet-bowl advancement; consistently
higher scores identify observed consolation advancement. Unknown numeric
`playoff_type` codes are not translated into an assumed format. This is an
explicit evidence-based classification, not independent certification of the
league's configuration. Ties/missing/mixed evidence leave format unknown and
award neither a last-place finish nor a consolation win. A unique finalized
`p:1` source-w outcome is required for either terminal outcome. No global rank
number is inferred for side games. Raw source w/l remains available throughout.

`championships.consolation` adds `schema_version:1`, `record_unit:playoff_series`,
`leaderboard` and `storylines`. Leaderboard items contain `user_id`,
`latest_display_name`, `appearances` (all losers-bracket seasons),
`toilet_bowl_appearances` (classified seasons), `last_place_finishes`,
`consolation_wins` (final bracket outcomes), `source_w_results`,
`source_l_results`, `higher_score_series_wins`, `lower_score_series_finishes`,
and `by_round` (round string to source-w/source-l integer totals).
Series counters include every finalized losers-bracket series, including its
side-placement games; they are separate from championship advancement records.
Score-based counters require decisive aggregate score evidence. No tied or
missing score is called a higher-score win. Appearances count once per season;
terminal finishes count once per final, regardless of weekly duration. All
manager keys use season-specific roster-to-user mappings.

Storyline kinds are `toilet_bowl_last_place` and `consolation_won`, each with
`season` and `user_id`. These are kept under the consolation object, separate
from championship storylines. Existing report fields retain their meanings.


## Official McChickens loser-title object (additive v1)

`championships.toilet_bowl` is the authoritative report location for the
McChickens rule: **the final loser holds the title; the winner avoids it**.
It contains `schema_version:1`, `rule:mcchickens_final_loser`,
`record_unit:playoff_series`, `regular_season_last_place_included:false`,
`history`, `leaderboard` and directional final `head_to_head` records.

Each history row contains `season`, `league_id`, `status`, `rule`, `final_series`,
`matchup_winner`, `matchup_loser`, `title_holder`, `outcome_basis` and `issues`.
`final_series` retains raw bracket source semantics; normalized winner/loser
and holder fields are historical manager objects or null. For a resolved row,
`title_holder == matchup_loser` and its user ID differs from `matchup_winner`.
`outcome_basis` is `official_bracket_with_observed_orientation`. The format
requires a unique validated finalized consolation `p:1` and confirmed source
orientation; ties, missing/mixed evidence and unknown final owners do not
produce a title. Known final entrants may still receive appearance records.

In the actual McChickens snapshots, source w advances as the losing team toward
last place. That source-w roster is normalized to `matchup_loser`; source l is
the actual matchup winner. In an ordinary higher-score source-w encoding, the
source-l roster is normalized to the loser. This prevents awarding titles to
actual winners simply because of misleading raw field names. A source outcome
without sufficient orientation evidence stays unresolved rather than guessed.
The generic `consolation` object retains its previous source-based meanings;
use the new rule-specific object for official McChickens titles.

Leaderboard entries contain stable `user_id`, `latest_display_name`, `titles`,
`bracket_appearances`, `final_appearances`, `final_wins`, `final_losses`,
`series_wins`, `series_losses` and `by_round` (string round to actual wins/losses).
All finalized losers-bracket series, including side games, contribute to series
records when their orientation is confirmed. Final losses, not wins, accrue
titles. No regular-season rank or last-place statistic is inferred. Leaderboard
order is titles descending, final appearances descending, user ID ascending.

Head-to-head entries contain `user_id`, `opponent_id`, `finals`, `wins`, `losses`
and `titles`; they count finals once even if played over multiple weeks.
Historical names/owner attribution use each season's frozen source snapshot.

`validate_championships.py --require-toilet-bowl` fails if an imported season's
rule-specific title is unresolved or violates the loser-title invariant.
`--from-season 2020 --through-season 2025` additionally requires every specified
year, so a shortened history cannot silently pass. The original database is
never needed for these checks. Actual-season evidence and reproducible commands
are in [TOILET_BOWL_VALIDATION.md](TOILET_BOWL_VALIDATION.md).


## Independent regular-season standings (additive v1)

`championships.regular_season` has `schema_version:1`,
`record_unit:regular_season_standings`, `history` and `leaderboard`.
Each season's existing timeline also exposes `regular_season_standings`.
These are separate from `championships.toilet_bowl` and all championship titles.

Each regular-season history entry contains `season`, `status`, `basis`,
`ranking_rule`, `standings`, `last_place` (manager object or null) and `issues`.
Standing rows contain the historical `manager`, `wins`, `losses`, `ties`,
`points_for`, `points_against` and competition `rank`. Finalized roster records
are sorted by record (wins plus half ties), then points for, then higher points
against. Whole and hundredths point fields are combined exactly before ranking.
All rosters must have complete, finite records and equal positive game counts.
When the league supplies its team count, that count must match. Exact bottom
ties, missing owners, partial records or unequal games leave last place
unresolved. No tie is broken by user ID, roster ID or playoff performance.

The regular-season leaderboard contains `user_id`, `latest_display_name`,
`seasons` (seasons with usable standings rows) and `last_place_finishes`.
The Toilet Bowl leaderboard's `titles` counts only final losses; it does not
read these standings fields. The standard Sleeper overall-record/PF/PA rules
are described in the [official standings reference](https://support.sleeper.com/en/articles/2203518-how-do-playoff-teams-get-determined).
Commissioner-specific manual seeding/rank changes are not reconstructed by this
default standings derivation. Existing raw roster snapshots retain the evidence.
