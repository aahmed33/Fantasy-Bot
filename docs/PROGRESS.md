# FantasyBot engine progress

## PAUSED - handoff checkpoint (2026-10-20)

Development is paused at the user's request. Do not start new work until the
user requests resumption. This section is the current handoff state; dated
sections below preserve the implementation history and earlier test counts.
Earlier statements that changes were uncommitted describe those earlier points;
this handoff is being saved in the checkpoint commit containing this section.

### Completed features

- Sleeper league-history discovery, cycle detection, users/rosters, matchups,
  NFL state and official winners/losers bracket endpoints.
- SQLite schema/migrations and configurable database paths; stable user-ID
  attribution within each season, historical names and departed managers.
- Historical weekly ingestion, completed-week filtering, score overrides,
  corrections, idempotency, invalid-score checks and transactional rollback.
- Weekly career/season statistics, head-to-head, ties, streaks, scoring/margin
  records, game/win milestones and deterministic statistical storylines.
- Completed-season playoff snapshots from 2020, frozen settings/owners/brackets/
  scores, content digests, retained revisions and atomic current pointers.
- Championship finalists/champions, explicit reliable placements, participation,
  validated bracket graphs, by-round advancement series W/L, championship H2H,
  title runs, droughts, timeline, leaderboard and structured facts.
- Multi-week series aggregation counted once, separate championship placement
  and consolation results, and observed-score cross-check diagnostics.
- Official McChickens Toilet Bowl rule: final LOSER receives the title. Raw
  source w/l and normalized actual winner/loser stay separate. History, titles,
  final appearances, normalized series/round records and H2H are reported.
- Independent regular-season standings and last-place counts from roster
  records with default record/PF/higher-PA tiebreaks, never playoff results.
- Additive JSON schema v1, import/report/strict validation CLIs, documented
  contracts, durable validation evidence and an offline regression suite.
- No Hermes, AI agents, LLM integration or social publishing was implemented.

### Implementation versus live acceptance

Championship and Toilet Bowl implementations are tested and live-validated for
McChickens 2020-2025. All six championship and six Toilet Bowl finals resolve.
All 42 winners-bracket series agree with observed scores. Season-specific
ownership was checked; no missing/ambiguous outcome was found in those years.
The actual Toilet Bowl final loser receives each title; the winner avoids it.
Regular-season last-place finishes are recorded independently.

The importer was run twice on fresh Sleeper data: six snapshots, identical
current pointers, identical full logical database hash, and no duplicate titles.
Active 2026 was skipped. Live evidence, score tables, stable IDs and leaderboards
are in `docs/TOILET_BOWL_VALIDATION.md`; schema definitions are in
`docs/CHAMPIONSHIPS.md`. Do not repeat this completed verification needlessly.

Full multi-week LIVE acceptance is unfinished: every observed final was a
single-week series. Synthetic tests cover multi-week championships and Toilet
Bowls, but no real multi-week league was supplied. This limitation is not a
failing test and does not invalidate the verified single-week seasons.

### Test and operation state at pause

`.venv/Scripts/python.exe -m pytest -q -W error`: **49 passed** on 2026-10-20.
No running import, background operation or unfinished file mutation remains.
No new API calls/imports were started for handoff. All implementation changes,
tests and permanent documentation are included in the checkpoint commit;
no database, backup, environment, credential, cache or temporary report belongs
in that commit. The pre-existing empty `AGENTS.md` is intentionally unmodified
and untracked. No push or merge is authorized or performed.

### Preserved data (local only, intentionally ignored by Git)

- Use only `data/championship-validation-20261020.db` for the existing live
  validation. It contains the raw 2020-2025 snapshots; do not discard them.
- Pre-refresh backup:
  `data/championship-validation-20261020.pre-refresh-20261020T172807159183Z.db`.
  It was made with SQLite backup and passed integrity checking.
- Validation logical dump SHA-256 after both imports:
  `4d03ac6807d8239df66286b5834bc5c64540c0d1c1754d31923ffd3a7e5ceeb3`.
- Original `data/mcchickens.db` was NOT imported, migrated or overwritten.
  Expected original SHA-256:
  `41087E003ED08A3B520F74CD6F33AB4CC5D2A64AF0890B0E34B07FEF4623B2E6`.
- These databases/backups are not in Git. Keep the local workspace or preserve
  those files separately when moving machines; a checkout alone lacks live data.

### Known limitations and environment issues

No known failing regression or unresolved result in verified 2020-2025 data.
Remaining limits: observed paired scores cannot certify all expected schedule
weeks; undocumented playoff type/round codes are not guessed. Toilet Bowl
outcome orientation needs consistent decisive observed evidence, so missing,
tied, mixed or ambiguous data can remain unresolved even with raw source fields.
Do not invent winners, losers or missing owners to fill those gaps.

Names are frozen as returned by season endpoints, not reconstructed historical
renames. Midseason ownership changes, co-owner records, custom commissioner
ranking/seeding, exact standings ties and unequal/missing game records are not
reconstructed. Weekly game records and playoff series records have distinct
units; the standalone bracket importer does not populate weekly matchup data.
The weekly manager import is a separate transaction from weekly matchup import.

Pytest disk caching is disabled because the existing `.pytest_cache` ACL belongs
to the sandbox account; its permissions were not changed. Test warnings are
still enabled, but cache-dependent `--lf`/`--ff` options are unavailable. Use the
existing `.venv`; global Python has no pytest. Git in the sandbox requires the
per-command safe.directory exception below; no global Git config was changed.

### Exact resumption steps (only after the user resumes work)

First inspect the checkpoint and rerun local checks without refreshing sources:

```powershell
Set-Location C:/Users/darkm/Desktop/FantasyBot
git -c safe.directory=C:/Users/darkm/Desktop/FantasyBot branch --show-current
git -c safe.directory=C:/Users/darkm/Desktop/FantasyBot status --short
git -c safe.directory=C:/Users/darkm/Desktop/FantasyBot log -1 --oneline
.venv/Scripts/python.exe -m pytest -q -W error
.venv/Scripts/python.exe scripts/validate_championships.py --database data/championship-validation-20261020.db --require-toilet-bowl --from-season 2020 --through-season 2025
.venv/Scripts/python.exe scripts/report.py --database data/championship-validation-20261020.db
Get-FileHash -LiteralPath data/mcchickens.db -Algorithm SHA256
```

Confirm the branch is `codex/fantasybot-engine`; compare the original file hash
with the value above. Do not run `init_database.py`, `import_history.py` or
`import_matchups.py` with their default database paths: those target the original.
Do not migrate or modify the original database without explicit approval.

Next unfinished acceptance task: obtain a completed real multi-week season
from the user, inspect official bracket/settings and all final weeks, and agree
on its validation destination before importing. No suitable league ID is known;
do not guess one or claim live multi-week acceptance from mock tests.

If the user requests a fresh McChickens refresh instead, preserve the existing
validation database again with SQLite backup before running this known command:

```powershell
.venv/Scripts/python.exe scripts/import_championships.py --database data/championship-validation-20261020.db --league-id 1312242543550828544
```

Then repeat the strict validation/report commands above. Keep prior snapshots
and backups. Do not repeat implementation milestones or push/merge without
approval. There are no additional feature tasks in progress.

---

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

Initial weekly-engine milestones implemented. Initial validation on 2026-10-20:
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
At the initial weekly milestone no live import, push or merge had been performed. On continuation,
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
  median bonuses and midseason owner reconstruction remain outside weekly
  statistics. The championship extension below now supplies authoritative series
  and title history separately from these weekly results.
- AI agents, LLMs, Hermes and social publishing were not implemented.

## Continuation instructions

The initial weekly-engine milestones are implemented. Championship history is
mandatory; implementation and partial live verification are recorded below. Next operational verification is
an import against a selected real Sleeper league/database and review of its JSON
report. Initial tests used isolated temporary databases and mock API responses.
The championship extension below records subsequent live verification. Verify branch and worktree first. Do not
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

At that initial review, live Sleeper responses were not yet validated;
weekly playoff/consolation policy and separate manager/matchup transactions
remain as documented above. The existing cache ACL remains restricted, but the
default test command no longer uses it. Git's ownership exception is still
needed for sandbox Git commands; no global setting was changed.


## Championship extension - implementation tested; live acceptance partial

- [x] C1: Official winners/losers bracket snapshots, season settings, frozen
  owner identities and correction history, completed seasons from 2020.
- [x] C2: Authoritative series results, separate consolation/placement games,
  multi-week score cross-checks with uncertainty reported explicitly.
- [x] C3: Championship timeline, leaderboard, playoff rounds, head-to-head,
  streaks, droughts and deterministic championship storylines in versioned JSON.
- [x] C4: Regression coverage, schema/CLI docs, full test run and original DB hash.
- [ ] C5: Live-data acceptance against Sleeper (separate from mock tests).

Do not use `data/mcchickens.db` for development or validation. Championship CLI
will require an explicit separate database and reject the original path.


### Delivered championship behavior

`playoff_snapshots` preserves content-addressed raw league/settings, user/roster,
winners/losers and matchup sources. `playoff_seasons` selects the current
revision; corrected/duplicate imports are atomic and retain prior evidence.
No weekly rows or season-manager identities are changed by this importer.
The JSON report adds `championships` with schema_version 1; its timeline,
leaderboard, by-round series W/L, championship H2H, confirmed title runs, active
season droughts and structured facts are documented in `docs/CHAMPIONSHIPS.md`.
Missing/ambiguous finals remain unresolved; scores never create champions.

### Live evidence - 2026-10-20

After the sandbox blocked sockets, an approved network run used:

```powershell
.venv/Scripts/python.exe scripts/import_championships.py --database data/championship-validation-20261020.db --league-id 1312242543550828544
.venv/Scripts/python.exe scripts/validate_championships.py --database data/championship-validation-20261020.db
```

Completed seasons 2020-2025 were imported; 2026 was skipped as in progress.
There were no missing/unresolved seasons, and all 42 winners-bracket series had
observed score agreement. The saved-source audit returned no errors or warnings.
Each imported season used six playoff teams and playoff_round_type 0; the start
week was 14 in 2020/2021 and 15 thereafter. Finals were single-week series.

| Season | Champion (source display name) | Runner-up | Final week |
| --- | --- | --- | --- |
| 2020 | BigMaaz | chamwowzers | 16 |
| 2021 | Alshara52 | chamwowzers | 16 |
| 2022 | LilCornFritter | BIGHURTZ | 17 |
| 2023 | BigMaaz | PrincessAltaii | 17 |
| 2024 | LilCornFritter | chamwowzers | 17 |
| 2025 | chamwowzers | COCKMOOD | 17 |

Live data exposed reversed advancement in the toilet bowl. The implementation
now preserves official consolation w/l and labels observed score ordering
without treating lower-score advancement as a championship discrepancy.
A regression test covers this behavior. The validation DB is ignored by Git.
The original database SHA-256 remains
`41087E003ED08A3B520F74CD6F33AB4CC5D2A64AF0890B0E34B07FEF4623B2E6`.

### Acceptance limits and continuation

Implementation tests include single/multi-week finals and all-round two-week
series, 4/6/8-team formats, byes, graph references, malformed/missing/ambiguous
brackets, correction history, fetch rollback, names/owner changes, console
output, protected-original-path checks and schema keys. Run:
`.venv/Scripts/python.exe -m pytest -q -W error`: **36 passed**, including
all 14 existing weekly-engine tests. `git diff --check` passed.

C5 remains unchecked: a completed real multi-week league has not been supplied
or verified. Do not declare full championship acceptance from synthetic tests.
Use the README commands with a completed multi-week league ID and a different
validation DB, inspect final score weeks and raw brackets, and confirm outcomes
in Sleeper. Source settings are retained, but undocumented round-type codes are
not decoded; observed score totals cannot certify completeness of every expected
week. Historical names are frozen as returned by season endpoints at import
time; names from before the first snapshot cannot be reconstructed.

No original DB migration/import was run. No championship changes were committed,
pushed or merged. Verify branch, rerun tests and inspect the separate validation
DB before continuing; preserve raw snapshots and original DB.


## Explicit toilet-bowl tracking (2026-10-20)

Added per-season consolation/toilet-bowl summaries and a separate manager
leaderboard with appearances, last-place finishes, consolation bracket wins,
source-w/source-l records by round and observed higher/lower-score series
records. Structured last-place/consolation facts are reported separately from
championship facts. Multi-week aggregation produces one terminal finish.

Format classification is based on consistent observed aggregate score order,
not an undocumented settings enum. Tied, absent, mixed or ambiguous evidence
leaves outcomes unresolved; raw source results remain tracked. The validation
CLI now warns on unresolved toilet-bowl/consolation outcomes. Schema additions
and statistical definitions are documented in `docs/CHAMPIONSHIPS.md`.

Full suite: **40 passed**, with warnings treated as errors. New coverage checks
multi-round loser advancement, multi-week finals whose weekly winners differ,
repeat imports, corrected outcomes, ties, pending/ambiguous finals, manager
counters and separation from championships. A read-only audit of the previously
fetched live 2020-2025 snapshots resolves six toilet-bowl last-place outcomes.
No additional network import or original database write was needed. Real
multi-week toilet-bowl verification remains part of pending live acceptance.


## Official McChickens final-loser title rule (2026-10-20)

Implemented `championships.toilet_bowl`: a dedicated history table, all-time
leaderboard, final appearances/wins/losses, normalized round records and final
H2H keyed by historical user IDs. The title is awarded to the actual final
loser, never the winner, independently of regular-season last-place finishes.
The old generic consolation/source-advancement fields retain their meanings.
A unique finalized bracket is mandatory; unknown source orientation or owner
identity, missing finals and ambiguous results remain unresolved.

Sleeper's real McChickens losers-bracket w field advances the lower-scoring
team. The implementation preserves it as source data and normalizes that team
to the actual matchup loser. Ordinary winner-w encoding instead selects source
l as the loser. Regression tests cover both encodings, prove the actual winner
receives zero titles, aggregate multi-week finals once, preserve departed owner
identity, handle corrections and require all requested seasons in validation.

Fresh live API import was approved and completed for every season 2020-2025;
active 2026 was skipped. All six Toilet Bowl finals resolved. Strict validation
exited 0 with no errors or warnings. Exact identities, scores, user IDs and
reproduction commands are in `docs/TOILET_BOWL_VALIDATION.md`. Re-fetched payloads
matched existing source digests, so immutable first-fetch timestamps remain.

Full regression suite: **46 passed** with warnings treated as errors. Actual
history has single-week finals; real multi-week verification remains pending.
The separate ignored validation DB was refreshed. The original database hash
remains unchanged. No commit, push or merge was performed for this extension.


## Preserved validation refresh and independent regular-season standings

On 2026-10-20, preserved the existing validation database using SQLite backup:
`data/championship-validation-20261020.pre-refresh-20261020T172807159183Z.db`.
Backup integrity check passed. Both fresh read-only API imports targeted only
the existing `data/championship-validation-20261020.db`, not the original or
backup file. All prior snapshots remain preserved.

Two live import runs produced identical logical database contents: six
snapshots, unchanged current pointers, and logical dump SHA-256
`4d03ac6807d8239df66286b5834bc5c64540c0d1c1754d31923ffd3a7e5ceeb3`.
Strict required-season/loser-title validation passed for every year 2020-2025
with no errors or warnings. Raw source roster ownership and bracket membership
were independently checked. Actual final weeks are 15 in 2020/2021 and 16 in
2022-2025; no actual multi-week final exists in this dataset.

Added independently derived regular-season standings and last-place counts
under `championships.regular_season`. Record/PF/higher-PA ranking uses frozen
roster settings, not playoff outcomes. Incomplete, tied or inconsistent data
remain unresolved. Custom manual commissioner ranking is not reconstructed.
Side-by-side live standings/Toilet Bowl results and the historical title
leaderboard are in `docs/TOILET_BOWL_VALIDATION.md`.

Full automated suite: **49 passed**, including independence, standings point
tiebreaks, incomplete records and repeated import checks. Original database
hash is unchanged. No push or merge occurred. Continue with a supplied real
multi-week league if further format acceptance is needed; preserve the original
and validation backups. All changes remain uncommitted.
