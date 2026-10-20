# McChickens Fantasy Bot

An AI-powered fantasy football analytics and media agent built for the McChickens Fantasy League.

## Project Goals

The application will:

- Retrieve current and historical league data from Sleeper.
- Build a persistent database of league history.
- Track manager records, rivalries, streaks, milestones, and league records.
- Discover interesting statistical storylines automatically.
- Use an AI agent to research fantasy matchups.
- Generate entertaining NFL-style weekly previews and recaps.
- Eventually publish approved content to X/Twitter.

## Development Roadmap

### V0.1 - League Historian
- Sleeper API integration
- Historical season discovery
- SQLite database
- Manager identity tracking
- Historical matchup collection

### V0.2 - Analytics Engine
- Career statistics
- Head-to-head records
- Streaks
- League records
- Milestones

### V0.3 - AI Agent
- Tool calling
- Matchup research
- Statistical storyline discovery
- Weekly analysis

### V0.4 - Media Engine
- Weekly previews
- Weekly recaps
- NFL-style writing
- Historical storylines

### V1.0 - Deployment
- X/Twitter integration
- Human approval workflow
- Automated scheduling
- Cloud deployment

## Non-AI analytics engine

The local engine imports Sleeper league history and computes deterministic
statistics without AI or publishing integrations.

```powershell
.venv/Scripts/python.exe scripts/import_matchups.py
.venv/Scripts/python.exe scripts/report.py
.venv/Scripts/python.exe scripts/report.py --season 2025
.venv/Scripts/python.exe scripts/report.py --include-playoffs
.venv/Scripts/python.exe -m pytest -q
```

Both import and report accept `--database PATH`. The import accepts `--league-id
ID`; otherwise it uses `src/mcchickens/config.py`. It imports manager history
automatically. The report prints JSON; redirect it to a file to save a snapshot.
Tests also run with `python -m unittest discover -s tests -v` using the standard
library test runner and the requests runtime dependency.

The importer applies Sleeper commissioner score overrides, refreshes completed
weeks on every run and rolls back matchup changes on failure. Manager-history
refresh is a separate transaction. Existing databases migrate automatically;
legacy matchup rows remain unverified until reimported. Current NFL week is
excluded conservatively. Completed seasons use 17 weeks before 2021 and 18 weeks
thereafter. The API source for paired matchup IDs and custom score fields is
[Sleeper documentation](https://docs.sleeper.com/).

Reports contain manager totals, directional head-to-head totals, streaks,
highest/lowest scores, largest/closest margins, exact game/win milestone
crossings at 10/25/50/100, and structured statistical storylines for the latest
week. Use `--season` to scope every statistic to one season. Ties count as half a
win for win percentage and interrupt win/loss streaks. Zero and negative scores
are valid. Records retain tied holders. Unpaired rosters, null matchup IDs,
missing scores and unknown owners do not produce results. Scores are counted
only in valid paired contests, so bye-week points are excluded from totals.

Regular season is the default. `--include-playoffs` includes every week from the
configured playoff start, including consolation contests. Results are weekly;
the separate `championships` section resolves authoritative playoff series and
titles. Weekly totals do not include league-median bonus wins or co-owner records. Manager attribution uses each season's Sleeper
owner snapshot; midseason ownership changes cannot be reconstructed from that
snapshot. Streaks span seasons and gaps between eligible games. Statistical
storylines are structured facts, with no generated narrative.

See [progress and continuation notes](docs/PROGRESS.md) for the audit and
milestone status.


## Championship history (report schema v1)

Championship ingestion follows each completed season's official winners and
losers bracket endpoints from 2020 onward. It freezes league settings, roster
owners, names returned by that season's endpoint, raw brackets and playoff
matchup scores. User IDs identify managers; roster IDs stay scoped to a season.
Content-addressed snapshots retain previous corrections; a separate pointer
selects the current revision. The importer fetches all sources before publishing
any changes, and does not modify weekly matchup/manager tables.

A unique, finalized `p: 1` winners-bracket series determines the title. Scores
never invent a missing winner or override an official result. Graph references,
roster membership, rounds and duplicate slots are validated. All observed paired
weeks for a unique series are aggregated once, including commissioner overrides.
Two weekly games in a final therefore produce one championship and one series
result. Missing scores, repeated pairs and score disagreements are visible.

`playoff_week_start` controls score collection; `playoff_teams` cross-checks
participants. All settings, including `playoff_round_type`, are preserved in
JSON. Undocumented round-type encodings are not guessed: score cross-checks
report **observed paired weeks**, not a certification that every scheduled week
exists. A known bracket result can remain authoritative without scores. A
multi-week fixture verifies aggregation for both semifinals and finals; the
current real league history contains single-week formats only.

Title-advancement series determine playoff W/L by round. Placement games inside
the winners bracket and every losers-bracket series are reported separately.
Losers-bracket `w`/`l` can represent toilet-bowl advancement; they do not become
championships or inferred league-wide placements. Explicit consistent winners
bracket `p` results provide final placements. See the
[JSON contract and statistical definitions](docs/CHAMPIONSHIPS.md).

### Validate real history without modifying the original database

Run these commands from the repository root in PowerShell. The championship
importer requires a separate database and rejects `data/mcchickens.db`, including
aliases to that file. Generated databases remain ignored by Git.

```powershell
.venv/Scripts/python.exe -m pytest -q -W error
.venv/Scripts/python.exe scripts/import_championships.py --database data/championship-validation-20261020.db --league-id 1312242543550828544
.venv/Scripts/python.exe scripts/validate_championships.py --database data/championship-validation-20261020.db
.venv/Scripts/python.exe scripts/report.py --database data/championship-validation-20261020.db
.venv/Scripts/python.exe scripts/report.py --database data/championship-validation-20261020.db --season 2020
```

`validate_championships.py` audits saved sources and exits 1 for missing seasons,
unresolved finals/owners, incomplete winners-bracket results or observed score
conflicts; exit 0 does not certify schedule completeness. Import again to fetch
fresh sources. Reports work on an older database without playoff tables and
return an empty championship section until sources are imported. Season filters
apply to championship totals too; `--include-playoffs` affects weekly statistics
only. This standalone championship import does not populate weekly statistics.

Live verification on 2026-10-20 imported 2020-2025, skipped active 2026, resolved
all six titles and cross-checked all 42 winners-bracket series (including
placement games) with observed scores. The audit returned no errors or warnings.
Original database SHA-256 was unchanged. This is live verification of the
current league's single-week history, not live acceptance of multi-week formats.
Use a completed real multi-week league with `--league-id` and a different
validation database to finish that acceptance case.


### Toilet-bowl and consolation history

Reports now expose `championships.champions_by_season[].consolation` for each
season and `championships.consolation` for manager totals and statistical facts.
These include entrants, final series, toilet-bowl last-place finishes,
consolation winners, appearances, source advancement results by round, and
observed higher/lower-score series records. Multi-week final scores are summed
before recording one finish. Championship records remain independent.

The format is classified from consistent observed aggregate score ordering;
undocumented settings codes are not guessed. Missing, tied, ambiguous or mixed
score evidence leaves the format/outcome unconfirmed. Source w/l is preserved
regardless. This deliberately separates advancement toward last place from
winning a higher-score game. The validation CLI surfaces unconfirmed outcomes.
Saved live 2020-2025 snapshots yield six confirmed-by-observed-score toilet-bowl
last-place outcomes. Real multi-week toilet-bowl acceptance remains pending.


### Official McChickens Toilet Bowl rule

The **loser of the finalized Toilet Bowl final receives the title**. The actual
matchup winner avoids it. Use `championships.toilet_bowl.history` for the history
table and `championships.toilet_bowl.leaderboard` for all-time titles, final
appearances, final wins/losses and normalized series records. These are distinct
from championship statistics and regular-season last-place finishes.

Raw Sleeper w/l can encode advancement toward the bottom of the bracket, not
ordinary matchup victory. Reports preserve the raw final and explicitly expose
`matchup_winner`, `matchup_loser` and `title_holder`; the title holder always
matches the normalized loser. Unreliable final identity, owner attribution or
outcome orientation leaves the result unresolved. No title is inferred from
scores without a finalized bracket. Multi-week scores are aggregated once.

Fresh Sleeper validation covers every completed season 2020-2025. The strict
command is:

```powershell
.venv/Scripts/python.exe scripts/validate_championships.py --database data/championship-validation-20261020.db --require-toilet-bowl --from-season 2020 --through-season 2025
```

See [the actual-season validation table](docs/TOILET_BOWL_VALIDATION.md) for
winner/loser identities, final scores, user IDs and the all-time leaderboard.
All six finals resolve; actual multi-week verification remains pending.


### Regular-season last place is a separate achievement

`championships.regular_season.history` reports historical standings and the
regular-season last-place manager; its separate `leaderboard` counts those
finishes. This uses Sleeper roster regular-season records and the default
record/PF/higher-PA ranking order, never Toilet Bowl results. Missing records or
an exact unresolved bottom tie do not produce an invented last-place finish.
Custom commissioner rankings are not reconstructed. Toilet Bowl final losses
remain counted only as `championships.toilet_bowl.leaderboard[].titles`.
See the validation document for the side-by-side 2020-2025 history.

The latest live refresh was run twice after preserving a SQLite backup.
Snapshot counts, season digest pointers and the full logical database hash
were identical after both imports. **49 tests pass**. All six actual finals
are single-week; real multi-week acceptance remains pending. The original
`data/mcchickens.db` was not modified or migrated.
