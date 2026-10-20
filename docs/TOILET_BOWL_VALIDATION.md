# McChickens Toilet Bowl validation - 2026-10-20

Fresh official Sleeper requests were made for the complete league history rooted
at `1312242543550828544`. Completed seasons 2020-2025 were imported into
`data/championship-validation-20261020.db`; active 2026 was skipped. The original
`data/mcchickens.db` was not imported or migrated. Content digests matched the
previously fetched sources; immutable snapshot timestamps retain their first fetch.

## Rule and source interpretation

**The actual final loser receives the Toilet Bowl title. The winner avoids it.**
The title is not a regular-season last-place finish. The final is the unique
validated `p:1` result from the season-specific `losers_bracket` endpoint.
In all six real seasons, source `w` is the lower-scoring advancing roster and
source `l` is the higher-scoring roster. Thus raw source `w` is the actual
**matchup loser** in these snapshots. Simply awarding source `l` would award
each title to the higher-scoring team and violate the official McChickens rule.
Normalized matchup winner/loser fields expose this distinction explicitly.

All finalized consolation series had consistent observed aggregate ordering.
No missing/ambiguous finals, unknown owners or conflicting evidence were found.

## Verified finals

| Season | Final ID | Week(s) | Winner avoiding title | Winner score | Title holder (loser) | Loser score | Holder user ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 3 | 15 | JSmooth96 | 116.82 | LilTubby | 82.80 | 471906508121042944 |
| 2021 | 3 | 15 | LilCornFritter | 118.65 | JuicyBitch69 | 79.95 | 471899303565062144 |
| 2022 | 3 | 16 | PrincessAltaii | 140.05 | Alshara | 109.80 | 469288592523390976 |
| 2023 | 3 | 16 | Alshara52 | 128.05 | BIGHURTZ | 120.85 | 471898992611946496 |
| 2024 | 3 | 16 | Bowtaii | 164.90 | BigMaaz | 123.50 | 471898901524246528 |
| 2025 | 3 | 16 | JuicyBitch69 | 159.60 | BIGHURTZ | 133.25 | 471898992611946496 |

## All-time titles by stable user ID

| Manager (latest source name) | User ID | Titles | Final appearances |
| --- | --- | --- | --- |
| BIGHURTZ | 471898992611946496 | 2 | 2 |
| JuicyBitch69 | 471899303565062144 | 1 | 3 |
| Alshara | 469288592523390976 | 1 | 1 |
| BigMaaz | 471898901524246528 | 1 | 1 |
| LilTubby | 471906508121042944 | 1 | 1 |
| Bowtaii | 471898836202156032 | 0 | 2 |
| Alshara52 | 466750993019695104 | 0 | 1 |
| LilCornFritter | 471899032583663616 | 0 | 1 |
| COCKMOOD | 471899057820790784 | 0 | 0 |
| sharejy | 471899581488033792 | 0 | 0 |

## Reproduce verification

```powershell
.venv/Scripts/python.exe -m pytest -q -W error
.venv/Scripts/python.exe scripts/import_championships.py --database data/championship-validation-20261020.db --league-id 1312242543550828544
.venv/Scripts/python.exe scripts/validate_championships.py --database data/championship-validation-20261020.db --require-toilet-bowl --from-season 2020 --through-season 2025
.venv/Scripts/python.exe scripts/report.py --database data/championship-validation-20261020.db
```

Validation exited 0 with no errors or warnings. Required-year checks prevent
a partial history from silently passing. All six finals in this real dataset
are single-week; multi-week regression tests pass, but a real multi-week
Toilet Bowl season has not been supplied. Observed scores do not independently
certify every expected week. Missing or conflicting outcome evidence remains
unresolved, with no title assigned.

The JSON location for official titles is `championships.toilet_bowl`.
Raw consolation advancement counters remain in `championships.consolation`.
Names are preserved as returned by the historical season endpoint; identities
are keyed by user ID, never by cross-season roster number.


## Preserved data and two-import idempotency verification

Before the fresh imports, SQLite's online backup API preserved the existing
validation data in
`data/championship-validation-20261020.pre-refresh-20261020T172807159183Z.db`.
The backup passed `PRAGMA integrity_check`. Both imports targeted only the
existing `data/championship-validation-20261020.db`; neither targeted the backup
or the original database. Both files are ignored by Git.

The importer was then run twice against fresh official Sleeper responses.
Both runs imported 2020-2025 and skipped active 2026. After each run there were
six immutable snapshots and identical current-season digest pointers. The
complete logical SQLite dump SHA-256 matched after both imports:
`4d03ac6807d8239df66286b5834bc5c64540c0d1c1754d31923ffd3a7e5ceeb3`.
This checks logical contents rather than SQLite file-header byte changes.
Strict validation returned no errors or warnings. Independently checking the raw
season roster owner IDs confirmed both finalists' user IDs for all six seasons;
none of those consolation finalists belongs to its championship bracket.
The full automated suite passed: **49 tests**, with warnings treated as errors.

## Separate regular-season last-place finishes

These standings come from the historical regular-season roster win/loss/tie
records, points for and points against. They do not use playoff results.
Exact ties or incomplete records remain unresolved instead of being assigned a
finish. The default Sleeper overall-standings tiebreak order is used; custom
commissioner seeding or historical manual ranking changes are not reconstructed.

| Season | Regular-season last-place manager | Toilet Bowl title holder |
| --- | --- | --- |
| 2020 | PrincessAltaii | LilTubby |
| 2021 | PrincessAltaii | JuicyBitch69 |
| 2022 | COCKMOOD | Alshara |
| 2023 | Alshara52 | BIGHURTZ |
| 2024 | Bowtaii | BigMaaz |
| 2025 | BIGHURTZ | BIGHURTZ |

The two achievements can belong to different managers or to the same manager;
their counts remain independent in JSON. No real multi-week Toilet Bowl final
appeared in these six seasons; its live verification remains pending.
The original SQLite database still has SHA-256
`41087E003ED08A3B520F74CD6F33AB4CC5D2A64AF0890B0E34B07FEF4623B2E6`.
