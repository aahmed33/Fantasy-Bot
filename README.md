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
they do not resolve multi-week playoff rounds, championships, league-median
bonus wins, or co-owner records. Manager attribution uses each season's Sleeper
owner snapshot; midseason ownership changes cannot be reconstructed from that
snapshot. Streaks span seasons and gaps between eligible games. Statistical
storylines are structured facts, with no generated narrative.

See [progress and continuation notes](docs/PROGRESS.md) for the audit and
milestone status.
