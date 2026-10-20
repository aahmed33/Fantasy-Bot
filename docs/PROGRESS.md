# FantasyBot engine progress

## Scope and initial audit

Work only on `codex/fantasybot-engine`; do not push or merge. AGENTS.md was
empty at inspection. All source, scripts, README, requirements and ignore rules
were inspected. Existing scripts named test_* are manual diagnostics, not tests.
SQLite schema and manager imports exist; matchup ingestion lacked finality,
playoff classification and custom scores. No analytics existed.

## Milestones

- [x] M1: Safe historical matchup ingestion, configurable database/client,
  migrations, completed-week filtering, corrections and rollback tests.
- [x] M2: Validated paired results, career/season statistics and head-to-head.
- [x] M3: Streaks, records, milestones and deterministic statistical storylines.
- [x] M4: CLI/report documentation and full offline regression suite.

## Statistical policy

Count only completed weeks; zero scores are valid. Pair exactly two rosters by
season/week/matchup ID. Exclude byes, incomplete scores and unmapped owners.
Use stable user IDs across seasons. Default analytics to regular season;
playoff flags mean weeks at/after playoff_start (including consolation games).
Weekly results do not claim to resolve aggregate multi-week playoff rounds.

## Validation and continuation

All four milestones implemented. Validation on 2026-10-20:
`.venv/Scripts/python.exe -m pytest -q`: **14 passed**.
The suite covers ingestion idempotency, commissioner zero overrides, score
corrections, stale rows, full matchup rollback, invalid scores, duplicate
rosters, season boundaries, byes, incomplete/unmapped groups, identity across
roster changes, owner replacement, display-name refresh, schema migration,
history cycles, HTTP errors, analytics, storylines and the JSON CLI.

Initial regression failures were fixed: explicitly close a test database on
Windows, and retain last-known names for managers removed from season snapshots.
The global Python has no pytest; use the existing `.venv`, or run
`python -m unittest discover -s tests -v`. No dependencies were installed.
No live database import, push or merge has been performed. On continuation,
verify branch first, read this file, run tests and complete unchecked milestones.
Sleeper response semantics checked against https://docs.sleeper.com/.


## Delivered interfaces and operational limits

- `scripts/import_matchups.py [--database PATH] [--league-id ID]` imports manager
  history and completed matchup weeks; `scripts/report.py [--database PATH]
  [--season YEAR] [--include-playoffs]` prints JSON.
- `mcchickens.analytics` exposes paired results, manager statistics,
  head-to-head, streaks, records, milestone crossings and structured storylines.
- Legacy rows default to unverified; rerun ingestion before reporting on an
  existing database. Current-week results deliberately wait until next NFL week.
- Manager import commits independently before matchup refresh. A matchup API
  failure leaves previous matchup data intact but may leave refreshed names.
- Playoff results are weekly and include consolation. Multi-week round results,
  championship history, median bonuses and midseason owner reconstruction are
  outside the weekly engine; do not infer these from current reports.
- AI agents, LLMs, Hermes and social publishing were not implemented.

## Continuation instructions

The planned engine milestones are complete. Next operational verification is
an import against a selected real Sleeper league/database and review of its JSON
report. Tests use isolated temporary databases and mock API responses; no live
league import was run in this session. Verify branch and worktree first. Do not
push or merge without approval. Git requires per-command
`-c safe.directory=C:/Users/darkm/Desktop/FantasyBot` in this environment due to
workspace ownership; no global Git configuration was changed.

## Pre-live Git review and pytest cache investigation (2026-10-20)

Reviewed the complete implementation diff, new analytics/report/test files,
tracked file list and ignore rules on `codex/fantasybot-engine`. No live import
or migration was run. The existing `data/mcchickens.db` is preserved; SHA-256
was recorded before verification and matched afterward:
`41087E003ED08A3B520F74CD6F33AB4CC5D2A64AF0890B0E34B07FEF4623B2E6`.
Final validation: `.venv/Scripts/python.exe -m pytest -q -W error` passed all
14 tests without warnings; `git diff --check` passed. Representative database,
sidecar, cache and credential paths are ignored; `.env.example` stays eligible.

The `.pytest_cache` directory and its `v/cache` subdirectory are owned by
`Adams_PC\CodexSandboxOffline`. Their protected ACLs grant access to OWNER
RIGHTS, SYSTEM and Administrators, with no grant to the normal `darkm` user.
The repository root, by comparison, grants `darkm` full control. This explains
why tests can pass in the sandbox while local pytest warns when writing cache.
No ownership, ACL or cache files were changed. `pytest.ini` now disables only
the optional cacheprovider plugin, avoiding disk-cache writes for both accounts;
test warnings remain enabled. Cached options such as `--lf` and `--ff` are
unavailable with this configuration. If disk caching is needed later, use a
writable per-user cache directory and explicitly re-enable the plugin.

Ignore rules now cover Python/test/tool caches, coverage output, SQLite files
and sidecars at any depth, environment files (except `.env.example`), local AWS
credentials, common credential JSON/private-key files and secret directories.
Ignore checks include synthetic paths without creating credential files.
Ignore rules do not scan or redact secrets in arbitrary source files; review
staged content before any future commit. No database or credentials should be
staged. The pre-existing empty untracked `AGENTS.md` is left unmodified and is
not part of the implementation commit.

Remaining operational issues: live Sleeper responses are not yet validated;
weekly playoff/consolation policy and separate manager/matchup transactions
remain as documented above. The existing cache ACL remains restricted, but the
default test command no longer uses it. Git's ownership exception is still
needed for sandbox Git commands; no global setting was changed.
