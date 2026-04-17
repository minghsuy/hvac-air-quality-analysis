---
title: Monitoring sprint — extract shared loader, dedup collector, fix alerts
type: fix
status: active
date: 2026-04-17
deepened: 2026-04-17
origin:
  - https://github.com/minghsuy/hvac-air-quality-analysis/issues/25
  - https://github.com/minghsuy/hvac-air-quality-analysis/issues/26
  - https://github.com/minghsuy/hvac-air-quality-analysis/issues/27
  - https://github.com/minghsuy/hvac-air-quality-analysis/issues/28
---

# Monitoring sprint — extract shared loader, dedup collector, fix alerts

## Overview

A diagnostic pass triggered by the user reporting a missed alert on 2026-04-16 surfaced four connected issues across the monitoring stack: two Python data-pipeline bugs (collector polling redundancy, parquet shift-repair clobbering Temp Stick rows) and two Apps Script alerting bugs (data-gap detection window too narrow, no absolute indoor-PM alert). This sprint closes all four in three focused PRs, landing Phase 1 (pure Python, low risk) before the `wife-surgery` hard cap in ~2 weeks and Phase 2 (Apps Script deploy) in the same window.

## Problem Frame

Four open issues:

- **#25 (P1 bug)** — `HVACMonitor_v3.gs::checkDataCollection()` scans only last 50 rows, narrower than the 2-hour `DATA_GAP_HOURS` threshold. A stopped sensor falls out of the scan window before becoming stale, so alerts never fire. This bug hid the attic Temp Stick outage for 3+ days.
- **#26 (P2 enhancement)** — Collector polls Temp Stick every 5 min, but the sensor only updates hourly (battery conservation). 11 of every 12 attic rows are identical duplicates. Cosmetic today, but wastes API calls (risking future WAF re-block) and masks the Sheet's true per-sensor cadence.
- **#27 (P1 bug)** — No alert fires when indoor PM is elevated (3-5 µg/m³ for 6 hours yesterday) if the delta to outdoor is small and outdoor is mildly polluted. The scenario falls in a blind spot between `checkIndoorSpike` (requires +5 delta) and `checkEfficiency` (requires outdoor ≥ 7 µg/m³).
- **#28 (P1 bug)** — `refresh_cache.py` and `dashboard.py` apply a "column-shift repair" to any row with <18 columns. Meant for pre-Sep 2025 legacy rows, but also triggers on modern Temp Stick rows that Sheets trims for trailing empties. Result: every attic temp/humidity value has been NaN'd in parquet since Feb 2026 (~15k rows silently wrong).

These four issues share one thread: the multi-sensor, multi-cadence architecture has gaps at every layer — collector writes redundantly, loader clobbers honest cadence variation, monitor assumes uniform rates, alerts assume uniform signals. Fixing all four together restores coherence.

## Requirements Trace

From the four origin issues:

- **R1 (#28)**: Historical attic temp/humidity must become visible in parquet after the fix (retroactive recovery of 15k+ rows by re-reading the Sheet).
- **R2 (#28)**: Pre-Sep 2025 rows with <18 columns must still receive the shift repair (don't regress the legitimate case).
- **R3 (#28)**: The three copies of sheets-fetch logic (`refresh_cache.py`, `dashboard.py`, `bench_heatmap.py`) must share a single implementation.
- **R4 (#26)**: Collector must skip the Sheet write when Temp Stick's `last_checkin` hasn't changed since the last successful write.
- **R5 (#26)**: After 24 hours of operation, attic row count should be 20-30/day (not 288/day).
- **R6 (#25)**: A sensor that stops writing must be alerted within `maxGapHours + 1 trigger tick`. Triggers are hourly, so the actual max is `maxGapHours + 1h`: ≤ 4h for Temp Stick (1h cadence, `maxGapHours = 3`), ≤ 2h for Airthings/AirGradient (5-min cadence, `maxGapHours = 1`).
- **R7 (#25)**: An hourly-cadence sensor (Temp Stick) must not false-alert on normal late check-ins.
- **R8 (#27)**: Using Apr 16 hourly data as historical replay, a new absolute-threshold alert must fire WARNING between 18:15-18:45.
- **R9 (#27)**: The new check must not false-alert on Apr 15 (outdoor similar, indoor stayed at 0).
- **R10 (all)**: Preserves existing behavior that is intentional — `test()` function as Apps Script verification harness, seasonal efficiency `minOutdoorPM` gate, "alert once per gap" script-property semantics.

## Scope Boundaries

- **No changes to collector's core API-fetch logic** — #24 (UA header) already landed; nothing else about the HTTP call changes.
- **No changes to `HVACMonitor_v3.gs`'s pressure, AQI, CO2, efficiency, or zone-filter checks** — they work correctly for their intended scenarios.
- **No changes to the 18-column Sheet schema** — the repair stays in place for legacy rows; only the gating changes.
- **No changes to `pyproject.toml`, `systemd/`, or the DGX deployment path** — collector stays at repo root per #23 plan's hard constraint.

### Deferred to Separate Tasks

- **Dashboard UI changes** to visualize the new `checkIndoorBaseline` alert history: separate post-surgery work.
- **Adaptive baseline** (rolling 30-day median instead of hardcoded 3 µg/m³ threshold): Phase 2b enhancement; ship the simpler fixed-threshold version first per #27.
- The alert body for `checkIndoorBaseline` IS in scope (see Unit 10 Approach). The `sendAlerts` wiring is reused as-is.

## Context & Research

### Relevant Code and Patterns

- **`scripts/refresh_cache.py:62-102`** — primary fetch function; has explicit `SHIFTED_COLS` list and `EXPECTED_COLS=18`. Inlined comment already flags the TODO: *"extract scripts/_sheets_loader.py to dedupe this, dashboard.py, and bench_heatmap.py (three near-identical copies of the same fetch pipeline)."*
- **`scripts/dashboard.py:60-110`** — parallel copy under a streamlit `@st.cache_data` decorator. Imports streamlit at module scope, which is why the extraction was deferred originally.
- **`scripts/bench_heatmap.py:23-95`** — third copy; drops the `_orig_cols` column before returning. Less recently touched.
- **`collect_with_sheets_api_v2.py:310-346`** — `get_tempstick_data()`; was updated for the UA header in #24 commit `4e27780`. Next change (dedup) should preserve the structured return shape so `build_temp_only_row()` at line 388 continues to work.
- **`HVACMonitor_v3.gs:36-100`** — `CONFIG` dict; hierarchical sensor/threshold structure. New `INDOOR_BASELINE` config and `EXPECTED_SENSORS` dict fit here.
- **`HVACMonitor_v3.gs:664-728`** — `checkDataCollection()`; the 50-row window bug lives here. `checkIndoorSpike` at 476-538 is the pattern to mirror for the new `checkIndoorBaseline`.
- **`HVACMonitor_v3.gs:127-183`** — `runAllChecks()`; the wiring point for the new check.
- **`HVACMonitor_v3.gs` test/calibration functions at 1509+** — pattern for adding new `test()` assertions.
- **`scripts/hooks/pre-push`** — enforces `ruff check` + `ruff format --check` + secrets scan + root-junk guard. All three Python PRs must pass this.
- **`tests/test_collect_air_quality.py`** — existing pytest target; new dedup logic needs at least one unit test here.

### Institutional Learnings

- **From the #24 session** (`docs/LESSONS_LEARNED.md`-worthy): WAFs silently dropping default `python-requests` UAs cost 3 days of data loss. Collector changes should now include a User-Agent audit any time new endpoints are added.
- **From the #28 discovery (this session)**: "column-shift repair" has been silently zeroing attic values for 3+ months. Lesson: data-repair logic that operates on all rows must have timestamp gates or explicit boundary conditions. When a repair targets a historical schema change, encode the cutoff date in the code, not in the comment.
- **From #23 (tidy-pass)**: collector's absolute path is pinned in DGX systemd. The Phase 1 PRs must not touch the collector's filename or entrypoint.
- **Apps Script testability** (from earlier sessions): copy-paste deployment means unit tests can't assert in the normal CI sense. The `test()` function is the harness; every new check needs a matching test-function branch.

### External References

Not needed — all four issues have concrete, locally-grounded fixes. The Temp Stick API surface is already characterized from #24 (`last_checkin`, `last_temp`, `last_humidity`, `battery_pct`, `offline` fields). Apps Script API semantics are well-documented in the existing HVACMonitor_v3.gs.

## Key Technical Decisions

| Decision | Rationale |
|---|---|
| Extract to `scripts/_sheets_loader.py` (leading underscore) and import as `from _sheets_loader import ...` | Scripts invoked via `python scripts/foo.py` or `streamlit run scripts/foo.py` get `scripts/` as `sys.path[0]`, so `_sheets_loader` is directly importable as a sibling module — no `scripts.` prefix, no `__init__.py`, no sys.path manipulation. Leading underscore signals private/internal module. Root-level placement is blocked by PR #23's root-junk guard. |
| Gate shift-repair with `Timestamp < pd.Timestamp("2025-09-01")` | The schema stabilized Sep 2025 (verified: last 17-col master_bedroom rows in Aug 2025). Timestamp-based gate is correct; row-length alone is too loose. |
| Keep dedup state in `.cache/tempstick_last_checkin` (flat file) | `.cache/` already gitignored; plain-text file is trivially inspectable and portable; avoids introducing a new SQLite or database dependency. |
| Dedup: skip entire `build_temp_only_row` call when `last_checkin` unchanged | Cleaner than writing a "null row" — the Sheet reflects true cadence. Matches #25's new monitor which scans by timestamp, not row count. |
| `EXPECTED_SENSORS` as dict with per-sensor `maxGapHours`, not a flat list | Allows 1h cadence (Temp Stick) to coexist with 5-min cadence (Airthings/AirGradient) without false-alerting. Directly addresses #25 Bug 2. |
| Scan window = `max(maxGapHours) × 2` hours, not 50 rows | Decouples scan size from write rate. After #26 dedup cuts Temp Stick to 24/day, row-based scanning would break. |
| `checkIndoorBaseline` uses fixed threshold `3 µg/m³` sustained 30 min, not rolling baseline | Per #27 acceptance criterion — simpler, ships today. Rolling baseline is deferred enhancement. Threshold chosen because master-bedroom baseline is effectively 0 (Airthings rounds to int). |
| Include directional context in #27 alert body (indoor vs outdoor) | Adds diagnostic value without more thresholds: "indoor > outdoor" suggests filtration failure; "indoor < outdoor" suggests infiltration overwhelming filter. |
| Three small PRs, not one | Matches prior sprint discipline (#23 had one commit per unit, clean reverts). Each PR shippable independently; reviewer can land Phase 1 while Phase 2 is drafted. |
| Phase 2 bundles #25 and #27 in one Apps Script commit | Both modify `HVACMonitor_v3.gs` and share `EXPECTED_SENSORS` / `CONFIG` expansion. Deployment is copy-paste — bundling saves one deploy cycle. |

## Open Questions

### Resolved During Planning

- **Should `_sheets_loader.py` be under `scripts/` or a new `src/`?** → Under `scripts/`. Project has no `src/` convention (CLAUDE.md: "flat structure required"), and the tidy-pass in #23 established `scripts/utils/` / `scripts/collectors/` / `scripts/analysis/` as the nesting pattern. `scripts/_sheets_loader.py` at the scripts root makes it a peer of the 3 callers.
- **Should the cache file survive across collector upgrades?** → Yes. The cache is content-addressed by `last_checkin`, which never regresses. No migration concerns.
- **Should `checkIndoorBaseline` fire CRITICAL, WARNING, or INFO?** → WARNING. CRITICAL is reserved for filter-failing and sensor-stopped alerts. This is "something is elevated, investigate" — WARNING matches the severity.
- **Should the new check run in the wife's alert stream too (`ALERT_EMAIL_2`)?** → No. It's a household-health signal, not a pressure/nerve-pain signal. Goes to `ALERT_EMAIL` only.
- **Do we need to migrate historical duplicate tempstick rows once #26 ships?** → No. Duplicates in the Sheet are harmless (medians unaffected). Forward dedup is sufficient.

### Deferred to Implementation

- **Exact pytest fixture shape for dedup testing** — the test needs to simulate two `get_tempstick_data()` calls with same `last_checkin`; leave fixture design to the implementer but confirm second call returns `None`.
- **Apps Script test-function wiring** — read against the live Sheet, not synthetic injection (see Unit 11).
- **Whether Apps Script deploy happens in-session or deferred** — user-side decision. Plan treats the deploy step as user-driven.

### Locked-in decisions (user approved 2026-04-17)

- **Backtest before Phase 2**: yes. A new Unit 7.5 runs `P(30-min rolling median of master_bedroom Indoor_PM25 > 3)` across the 9-month parquet before Phase 2 commits. If base rate >1-2 events/week, tune threshold before merging.
- **bench_heatmap.py**: migrate (not delete).
- **Phase 2 bundling**: #25 and #27 ship together in PR 3.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

Three isolated change surfaces, executed in dependency order:

```
PR 1 — Phase 1a  (Python, code-only)
┌──────────────────────────────────────────────────────────────────┐
│  scripts/_sheets_loader.py  (NEW)                                │
│    ├── load_sheet_as_df(sheet_tab, creds_path, spreadsheet_id)   │
│    │     └── applies SHIFTED_COLS repair ONLY when               │
│    │         Timestamp < SCHEMA_STABILIZED                       │
│    └── CONSTANTS: EXPECTED_COLS, SHIFTED_COLS, NUMERIC_COLS,     │
│                   SCHEMA_STABILIZED                              │
│                                                                  │
│  3 callers migrate to the shared loader:                         │
│    scripts/refresh_cache.py  ──┐                                 │
│    scripts/dashboard.py      ──┼──> from scripts._sheets_loader  │
│    scripts/bench_heatmap.py  ──┘      import load_sheet_as_df    │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼  (merge, pull to DGX, verify historical attic in parquet)
          │
PR 2 — Phase 1b  (collector, code-only)
┌──────────────────────────────────────────────────────────────────┐
│  collect_with_sheets_api_v2.py::get_tempstick_data                │
│    state: .cache/tempstick_last_checkin (gitignored flat file)   │
│    logic: if response last_checkin == cached → return None       │
│           else → write new cache, return dict (current behavior) │
│                                                                  │
│  tests/test_collect_air_quality.py                                │
│    test_dedup_skips_unchanged_checkin                             │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼  (merge, pull to DGX, observe 24h: attic ≤ 30 rows/day)
          │
PR 3 — Phase 2  (Apps Script, bundled)
┌──────────────────────────────────────────────────────────────────┐
│  HVACMonitor_v3.gs                                                │
│    CONFIG {                                                       │
│      EXPECTED_SENSORS: {                                          │
│        airthings:   { maxGapHours: 1 },                           │
│        airgradient: { maxGapHours: 1 },                           │
│        tempstick:   { maxGapHours: 3 },                           │
│      },                                                           │
│      INDOOR_BASELINE: {                                           │
│        absoluteThreshold: 3,                                      │
│        sustainedMinutes: 30,                                      │
│        cooldownMinutes: 60,                                       │
│      },                                                           │
│    }                                                              │
│                                                                   │
│    checkDataCollection():  rewrite to time-window scan            │
│      scan rows where Timestamp >= now - max(maxGapHours)*2        │
│      iterate EXPECTED_SENSORS (dict, not lastSeen keys)           │
│      flag as stopped if !lastSeen[type] OR hoursSince > spec      │
│                                                                   │
│    checkIndoorBaseline():  NEW                                    │
│      filter rows where room == 'master_bedroom' (NOT mirror       │
│        checkIndoorSpike which doesn't filter by room)             │
│      take last 6 filtered rows; skip if < 4 (sensor gap)          │
│      if median(indoor) > absoluteThreshold and not in cooldown:   │
│        alert WARNING with indoor/outdoor directional context      │
│                                                                   │
│    MONITOR_VERSION constant — logged per runAllChecks()           │
│    runAllChecks():  wire checkIndoorBaseline in                   │
│    test():  gap + baseline assertions against live Sheet          │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼  (user copy-pastes to Apps Script editor, runs test(), saves)
```

**Commit ordering matters**: Phase 1a must land before Phase 1b so the monitor (Phase 2, using the Sheet directly) and the analysis layer (parquet, via Phase 1a) both see honest per-sensor cadence when dedup ships in Phase 1b.

## Implementation Units

### Phase 1a — PR 1: Shared loader + #28 fix

- [ ] **Unit 1: Create `scripts/_sheets_loader.py`**

**Goal:** Single source of truth for Sheets → DataFrame conversion with correct shift-repair gating.

**Requirements:** R1, R2, R3

**Dependencies:** None

**Files:**
- Create: `scripts/_sheets_loader.py`
- Test: add `TestSheetsLoader` class to existing `tests/test_collect_air_quality.py` — don't create a new test file (the single-file convention matches the repo's pattern).

**Approach:**
- Expose `load_sheet_as_df(spreadsheet_id, sheet_tab, creds_path) -> pd.DataFrame`.
- Factor into `_fetch_values(...)` (API call, returns `list[list[str]]`) and `_values_to_df(values)` (pure transform). This gives a clean mock boundary — tests can call `_values_to_df` directly with synthetic row lists, no API mocking chain needed.
- Export constants: `EXPECTED_COLS = 18`, `SHIFTED_COLS` (the 8-column list), `NUMERIC_COLS`, `SCHEMA_STABILIZED = pd.Timestamp("2025-09-01")`.
- Apply shift-repair: `shifted = (orig_cols < EXPECTED_COLS) & (df["Timestamp"] < SCHEMA_STABILIZED)`.
- Do not bake in `.env` loading — each caller loads its own (`refresh_cache.py` uses explicit path, `dashboard.py` uses default). Loader takes parameters, doesn't read env.
- Drop `_orig_cols` before returning (all 3 callers drop it; no one needs it externally).

**Patterns to follow:**
- `scripts/refresh_cache.py:62-102` is the reference implementation; it's the most recently touched and has the clearest structure.

**Test scenarios:**
- Happy path: 3 synthetic rows, 2 modern (18-col, varied content) + 1 Sep 2025 row → all three return with correct numeric columns, no values nulled.
- Edge case: row with timestamp `2025-08-15`, 17 columns → `Indoor_Temp` is NaN (legacy shift-repair applies).
- Edge case: row with timestamp `2026-02-10`, 12 columns (Temp Stick pattern) → `Indoor_Temp` preserved (modern schema).
- Edge case: header mismatch (sheet returns 17 col headers instead of 18) → gracefully pad or surface error.
- Error path: empty Sheet response → raises `RuntimeError` with clear message.

**Verification:**
- `uv run pytest tests/test_collect_air_quality.py -v` passes (existing 22 + new `TestSheetsLoader` scenarios).
- `ruff check` + `ruff format --check` clean on the new module.

- [ ] **Unit 2: Migrate `scripts/refresh_cache.py` to use the shared loader**

**Goal:** Replace the inlined fetch with a one-line import.

**Requirements:** R1, R3

**Dependencies:** Unit 1

**Files:**
- Modify: `scripts/refresh_cache.py`

**Approach:**
- Delete the inlined `fetch_from_sheets` body (lines 62-102); replace with a call to `scripts._sheets_loader.load_sheet_as_df`.
- Keep `scripts/refresh_cache.py`'s own env loading and path setup — the loader doesn't own those.
- Remove the `TODO` comment about extraction (lines 5-6) — it's now done.

**Patterns to follow:**
- Keep the script's CLI entry point (`main()` + exit codes) unchanged. Only the fetch body shrinks.

**Test scenarios:**
- Happy path: run `uv run python scripts/refresh_cache.py` against live Sheet → parquet rebuild succeeds, row count matches prior run.
- Integration: `df[df['Room']=='attic'].Indoor_Temp.notna().any()` is True on a row after 2026-02-01 (#28 retroactive fix).

**Verification:**
- Manual run produces parquet; running `parse last_seen per room` query shows attic with non-NaN temp.

- [ ] **Unit 3: Migrate `scripts/dashboard.py` to use the shared loader**

**Goal:** Same replacement in the streamlit dashboard's fetch path.

**Requirements:** R3

**Dependencies:** Unit 1

**Files:**
- Modify: `scripts/dashboard.py`

**Approach:**
- Replace the `_fetch_from_sheets` body (lines 60-110). The streamlit `@st.cache_data` decorator stays on the wrapper; only the inner fetch goes to the shared loader.
- Preserve the `_save_parquet` helper and the `load_raw(force_refresh=...)` wrapping logic. The loader is a pure function; caching stays where it is.

**Patterns to follow:**
- Leave `dashboard.py`'s streamlit imports untouched — module-scope `import streamlit` is why the loader had to be a separate file in the first place.

**Test scenarios:**
- Integration: `streamlit run scripts/dashboard.py` — dashboard loads without error, attic charts render temp/humidity (they currently render NaN).
- Edge case: force-refresh (cache miss) → same code path executes; parquet writes correctly.

**Verification:**
- Dashboard loads; attic page shows non-NaN values.

- [ ] **Unit 4: Migrate `scripts/bench_heatmap.py` to use the shared loader**

**Goal:** Same replacement in the benchmark script.

**Requirements:** R3

**Dependencies:** Unit 1

**Files:**
- Modify: `scripts/bench_heatmap.py`

**Approach:**
- Replace the `fetch_from_sheets` body (lines 23-95). Preserve the benchmark's timing harness and CLI.
- **Full Phase 1a verification + PR lands in this unit** (collapsed from the old orchestration-only Unit 5):
  - `uv run ruff check .` + `uv run ruff format --check .` → clean.
  - `uv run pytest -q` → all 22+ existing + new `TestSheetsLoader` scenarios pass.
  - Manually run `scripts/refresh_cache.py` → parquet rebuilds. Query: `df[(df.Room=='attic') & (df.Indoor_Temp.notna())].shape[0]` should be >> 0 (before fix: 0).
  - **Pre-fix diagnostic** (adversarial F3): before rebuilding parquet, query the *old* cache: `df_pre[(df_pre.Timestamp >= '2025-09-01') & (df_pre._orig_cols < 18)].groupby('Sensor_Type').size()`. If any sensor_type besides `tempstick` shows up, investigate before shipping — the cutoff may not be clean.
  - Spot-check: at least one post-Feb-2026 attic row's `Indoor_Temp` value is within expected attic-temperature range (e.g., 10-40°C).
  - `rm .cache/air_quality.parquet` before final verification run so streamlit cache-key changes on next dashboard load (documents the fact that the fix requires a cache blow-away, not just a code revert).
  - Commit as `refactor: extract scripts/_sheets_loader.py and fix shift-repair date gate (#28)`.
  - Open PR 1 targeting `main`. Body references #28, notes retroactive historical data recovery + pre-fix diagnostic result.

**Patterns to follow:**
- Same as Unit 2.

**Test scenarios:**
- Happy path: `uv run python scripts/bench_heatmap.py` runs end-to-end; timing output shows ballpark-same numbers as pre-refactor.

**Verification:**
- PR 1 open, `mergeable: MERGEABLE`, CI green.
- Pre-fix diagnostic confirms only `tempstick` rows had shifted false positives post-Sep-2025 (if other sensors appear, block the PR and investigate).

### Phase 1b — PR 2: Collector dedup (#26)

- [ ] **Unit 6: Add `last_checkin` dedup to `get_tempstick_data`**

**Goal:** Skip Sheet writes when Temp Stick has no new reading since last successful fetch.

**Requirements:** R4, R5

**Dependencies:** Phase 1a merged (so historical verification works against a clean parquet)

**Files:**
- Modify: `collect_with_sheets_api_v2.py` — `get_tempstick_data()` function, ~line 310.
- Modify: `tests/test_collect_air_quality.py` — add `test_dedup_skips_unchanged_checkin`.
- Optional: `.gitignore` — already covers `.cache/`, but confirm `.cache/tempstick_last_checkin` is not accidentally re-exposed.

**Approach:**
- Read the API response as today; extract `checkin = data.get("last_checkin")`.
- Before returning the dict, compare `checkin` against `.cache/tempstick_last_checkin` file contents. If equal → return `None` (caller skips write).
- If different: write `checkin` to the cache file **atomically** via `.tmp` + `os.replace` to prevent torn writes on SIGTERM during systemd shutdown.
- If `last_checkin` field is missing from the 200 response (API schema drift): still return the dict, but **do NOT touch the cache file**. This prevents empty-string state that would starve all subsequent calls.
- If cache write itself fails (disk full, permission denied): log a warning to stderr + return the dict anyway. Better to have occasional duplicate rows than silently drop readings.
- **Observability**: emit a stderr warning line if the cache has been unreadable for more than one consecutive invocation — otherwise a broken dedup is invisible until the user notices the row count hasn't dropped. Track this via a small counter in a sibling file (`.cache/tempstick_dedup_health`) or simply log every cache-read failure with a clear tag that `grep`-able from the collector log.
- Keep other error paths unchanged: 429, `requests.RequestException`, non-200 → `return None` (already the case).
- Preserve the UA header and request structure from #24.

**Execution note:** Write the failing pytest first (given a fresh cache directory, call `get_tempstick_data` twice with same `last_checkin` → second call returns `None`), then implement.

**Patterns to follow:**
- Read/write state to `.cache/` using `pathlib.Path` (existing convention — `.cache/air_quality.parquet`).
- Keep the `try/except` structure; add cache IO inside the happy path.

**Test scenarios:**
- Happy path: `get_tempstick_data()` on empty cache → writes cache file, returns dict with real values.
- Happy path: second call with same `last_checkin` → returns `None`, cache file unchanged.
- Edge case: cache file exists but contains a different timestamp → returns dict (new reading), overwrites cache.
- Edge case: cache file deleted mid-run (race condition) → recovers gracefully, writes fresh cache.
- Edge case: cache file contains corrupt/torn bytes (interrupted SIGTERM during write) → comparison treats it as "different value", collector writes one duplicate row this cycle, cache re-seeds successfully.
- Error path: API returns 429 (or raises `requests.RequestException`) → returns `None`, cache file not touched (don't corrupt state on transient failure).
- Error path: API returns 200 but `last_checkin` field missing → still returns dict (don't starve the Sheet of data on API schema drift); cache file NOT touched.
- Error path: cache write fails (disk full / permission error) → stderr warning logged, dict still returned; test simulates by making `.cache/` read-only.

**Verification:**
- `uv run pytest -q tests/test_collect_air_quality.py -v` → new test passes alongside existing 22.
- Manual probe on DGX (via user, since production-collector-run is blocked): after 24h, attic row count in the Sheet for the day is 20-30 (not 288).
- **PR 2 lands here** (collapsed from old orchestration-only Unit 7):
  - Full ruff + pytest pass.
  - Commit as `feat(collector): dedup Temp Stick writes by last_checkin (#26)`.
  - Open PR 2 referencing #26. Body includes the "observe 24h on DGX" verification note.
  - PR 2 open, `MERGEABLE`, CI green.

### Phase 2 — PR 3: Apps Script monitor upgrade (#25 + #27)

- [ ] **Unit 8: Expand `CONFIG` with `EXPECTED_SENSORS`, `INDOOR_BASELINE`, and `MONITOR_VERSION`**

**Goal:** Add the new config surfaces; keep existing config unchanged.

**Requirements:** R6, R7, R8

**Dependencies:** Phase 1b merged (soft — test signals reflect honest cadence). Unit 8 itself is code-only and can be drafted pre-merge.

**Files:**
- Modify: `HVACMonitor_v3.gs` — `CONFIG` dict at lines 36-100, plus a top-of-file `MONITOR_VERSION` constant.

**Approach:**
- Add a top-of-file constant: `const MONITOR_VERSION = "v3.2026-04-17";` — bumped on every repo edit. `runAllChecks` logs it once per run so the Apps Script execution log grep-ably reveals which repo version is actually deployed (no deploy-drift mystery).
- Add new top-level CONFIG key `EXPECTED_SENSORS`: dict keyed by sensor_type (`airthings`, `airgradient`, `tempstick`) with `{ maxGapHours: N }` entries. Values per Key Technical Decisions table.
- Add new top-level CONFIG key `INDOOR_BASELINE`: `{ absoluteThreshold: 3, sustainedMinutes: 30, cooldownMinutes: 60, room: "master_bedroom" }`. Explicit room scoping — this check reads only the canonical indoor sensor, not all rooms.
- Leave `DATA_GAP_HOURS: 2` in place as a legacy key; mark with a comment that it's deprecated in favor of per-sensor `EXPECTED_SENSORS[type].maxGapHours`.

**Patterns to follow:**
- Indentation + comment style of the existing CONFIG keys (`OUTDOOR_AQI`, `PRESSURE`, `EFFICIENCY`).

**Test scenarios:**
- Test expectation: none — config-only change. Validated by downstream units.

**Verification:**
- Apps Script syntax check via the editor's linter (manual user step) passes.

- [ ] **Unit 9: Rewrite `checkDataCollection` to use time-window scan + per-sensor thresholds**

**Goal:** Fix #25 — detect multi-day outages regardless of write rate.

**Requirements:** R6, R7

**Dependencies:** Unit 8

**Files:**
- Modify: `HVACMonitor_v3.gs` — `checkDataCollection()` at lines 664-728.

**Approach:**
- Compute `maxGap = max(CONFIG.EXPECTED_SENSORS[*].maxGapHours)`. Scan rows where `Timestamp >= now - 2 * maxGap` (hours).
- Build `lastSeen` map as today.
- Replace `Object.entries(lastSeen)` iteration with iteration over `CONFIG.EXPECTED_SENSORS` entries:
  - If sensor not in `lastSeen` → treat as stopped (`hoursSince = Infinity` or the full scan window).
  - Else if `hoursSince > spec.maxGapHours` → stopped.
  - Else: check for resumption (existing logic: if script property `DATA_GAP_<type>` is set, clear it and emit INFO).
- Preserve `props.setProperty(gapKey, ...)` and `props.deleteProperty(gapKey)` semantics — the "alert once per gap" behavior is a feature, not a bug.
- Alert message wording: include the specific `hoursSince` and `maxGapHours` for the stopped sensor.

**Patterns to follow:**
- Line 690-708 iteration pattern; keep the same conditional structure, swap data source from `lastSeen` keys to `CONFIG.EXPECTED_SENSORS` keys.

**Test scenarios:**
- Happy path: all sensors writing within their cadence → no alerts.
- Edge case: Temp Stick silent 2h 45min → no alert (below 3h `maxGapHours`).
- Edge case: Temp Stick silent 3h 15min → CRITICAL alert "SENSOR(S) STOPPED: attic (tempstick): 3.3h ago".
- Edge case: all sensors silent 6h (collector down) → CRITICAL for all three, one merged alert.
- Integration: simulated resumption after a gap → emits INFO "SENSOR(S) RESUMED" once and clears script property.

**Verification:**
- `test()` function (Unit 11) exercises the new branches. Manual historical replay: feed Apr 13-17 tempstick data through the function; confirm alert would have fired on Apr 13 22:00 (3h after the last valid row at 21:02, plus one hourly trigger tick).

- [ ] **Unit 10: Add new `checkIndoorBaseline` function**

**Goal:** Fix #27 — alert when indoor PM is elevated on absolute scale, independent of outdoor or spike delta.

**Requirements:** R8, R9

**Dependencies:** Unit 8 (uses `CONFIG.INDOOR_BASELINE`)

**Files:**
- Modify: `HVACMonitor_v3.gs` — add function after `checkIndoorSpike` at line 538.

**Approach:**
- **CRITICAL — do NOT copy-paste-mirror `checkIndoorSpike`'s row-reading logic.** That function reads the last 6 rows regardless of sensor and silently pins `indoor` to 0 when the latest row happens to be a Temp Stick attic row (empty `Indoor_PM25`). Replicating that pattern would make this check accidentally blind, exactly like today's `checkIndoorSpike`.
- Instead: pull enough recent rows (scan a window of 60 min with safe margin — e.g., last 30 sheet rows) and **filter to `row[COLS.ROOM] === CONFIG.INDOOR_BASELINE.room`** ('master_bedroom') BEFORE any math.
- After filtering, take the most recent 6 master_bedroom rows. If fewer than 4 rows remain (sensor gap), skip the check entirely and log that this tick had insufficient data — do not alert on 1-2 data points.
- Compute `median(Indoor_PM25)` over those filtered rows only.
- If `median > CONFIG.INDOOR_BASELINE.absoluteThreshold` and not in cooldown (`INDOOR_BASELINE_ALERTED` script property within `cooldownMinutes` of now):
  - Emit WARNING alert with body:
    - Indoor PM2.5 (current reading + 30-min median from master bedroom)
    - Outdoor PM2.5 (current reading from outdoor sensor)
    - Delta interpretation: `indoor > outdoor` → "filtration failure suspected (indoor exceeds outdoor)"; `indoor < outdoor` → "outdoor infiltration exceeding filter capacity"
    - Suggested action: "Turn on main HVAC fan to circulate air through MERV 13 return filter"
  - Set `INDOOR_BASELINE_ALERTED` script property (timestamp).
- Cooldown is **time-based only** (matches `CONFIG.INDOOR_BASELINE.cooldownMinutes = 60`). No condition-based clearing. This is the same semantic as `checkIndoorSpike`'s cooldown — don't introduce a second pattern.

**Patterns to follow:**
- `checkIndoorSpike` at 476-538 is the template ONLY for the cooldown + alert-object + `props.setProperty` lifecycle. Do NOT copy its row-reading logic; build fresh filtering on `COLS.ROOM`.

**Test scenarios:**
- Happy path: indoor 0 µg/m³ (normal) → no alert.
- Happy path: indoor 2.5 µg/m³ (below threshold) → no alert.
- Edge case: indoor 3.1 µg/m³ for 30+ min → WARNING alert fires with directional context.
- Edge case: indoor 5, outdoor 4.5 (Apr 16 19:00 scenario) → fires with "indoor > outdoor: filtration failure suspected" subtext.
- Edge case: indoor 5, outdoor 100 (hypothetical wildfire) → fires with "infiltration exceeding filter capacity" subtext; `checkAQI` also fires; both are independently useful.
- Edge case: cooldown suppresses re-alert within 60 min; allows re-alert after cooldown expires.
- **Critical: filter correctness** — scan window contains 3 master_bedroom + 2 second_bedroom + 1 attic row → only the 3 master_bedroom rows participate in the median; attic/second_bedroom excluded. The test asserts `attic row's Indoor_PM25 = "" (or NaN)` does not appear in the computed median.
- Edge case: fewer than 4 master_bedroom rows in the window (sensor gap) → check skips silently, no alert (don't fire on 1 data point).
- Integration: historical replay of Apr 16 18:00-23:59 → alert fires between 18:15-18:45 (R8). No alert on Apr 15 under same outdoor conditions (R9).

**Verification:**
- `test()` assertions added in Unit 11 confirm Apr 16 and Apr 15 replay outcomes, and confirm the sensor-filter test case.

- [ ] **Unit 11: Wire new check into `runAllChecks` + extend `test()`**

**Goal:** Make the new check fire in production; expose it via the testing harness.

**Requirements:** R8, R9

**Dependencies:** Units 9, 10

**Files:**
- Modify: `HVACMonitor_v3.gs` — `runAllChecks()` at lines 127-183, and the `test()` function at ~line 1509.

**Approach:**
- In `runAllChecks()`, call `checkIndoorBaseline()` after `checkIndoorSpike`. Push its alerts to `alerts.you`.
- Add `console.log(\`Monitor version: ${MONITOR_VERSION}\`);` as the first line of `runAllChecks()` so the Apps Script execution log records which code version actually fired each tick.
- In `test()`, add assertion groups using **Sheet-reading pattern, not synthetic injection** (Apps Script functions read `SpreadsheetApp.getActiveSpreadsheet()` directly — synthetic injection isn't practical without a test spreadsheet):
  - `testDataGap`: use the existing Sheet's data; run `checkDataCollection()` and inspect the return value. Assert that if an `EXPECTED_SENSORS` entry has `lastSeen > maxGapHours` ago, it appears in `stoppedSensors`. Temp Stick's historical Apr 13-17 outage (now in git history) can be used as the anchor case.
  - `testIndoorBaseline`: run `checkIndoorBaseline()` against the current live Sheet. Print the computed median + alert decision. For Apr 16 replay, a manual verification step: set the Sheet's read-range temporarily to a date range where indoor was elevated, rerun, confirm alert fires.
- Keep the existing `test()` structure (console.log per branch, no assertion library); this matches the Apps Script idiom.

**Patterns to follow:**
- `testIndoorSpike()` already reads from the live Sheet via `SpreadsheetApp.getActiveSpreadsheet()`. Same mechanism.

**Test scenarios:**
- Test expectation: the `test()` output in the Apps Script editor must show `testDataGap` and `testIndoorBaseline` branches running to completion, printing computed values + alert decisions.

**Verification + PR 3** (collapsed from old orchestration-only Unit 12):
- User runs `test()` in Apps Script editor after deploy; console output shows new branches without errors and the `Monitor version: vX.YYYY-MM-DD` line prints.
- Commit as `feat(monitor): cadence-aware data-gap check + indoor baseline alert (#25, #27)`.
- Open PR 3 referencing #25 and #27. Body includes:
  - Summary of the config + check + wiring + `MONITOR_VERSION` changes.
  - Explicit deploy checklist for the user: "After merge: open Apps Script editor, paste entire file, save, set new Script Properties if needed, run `test()` function, confirm version line matches the PR's `MONITOR_VERSION` bump, optionally trigger a canary data-gap by pausing the collector briefly."
  - Historical replay results from Unit 10's Apr 16/Apr 15 test scenarios.
- No auto-merge. User reviews, merges, deploys.

## System-Wide Impact

- **Interaction graph:**
  - `scripts/_sheets_loader.py` (new) → imported by `refresh_cache.py`, `dashboard.py`, `bench_heatmap.py`. No other callers should emerge from this sprint.
  - `.cache/tempstick_last_checkin` — new file; read + written only by `collect_with_sheets_api_v2.py`. No other readers.
  - `HVACMonitor_v3.gs::runAllChecks` — existing orchestrator; gains one call to `checkIndoorBaseline`.
  - Script Properties: new key `INDOOR_BASELINE_ALERTED`. Existing `DATA_GAP_<type>` keys remain compatible (same lifecycle semantics).
- **Error propagation:**
  - Shared loader: raises `RuntimeError` on missing creds / empty sheet (matches current behavior). Callers handle; no new swallowing.
  - Collector dedup: cache-IO failures log to stderr but don't block returning the dict (worse to drop a reading than write a duplicate). A "dedup unhealthy" counter tracks consecutive read failures so a broken dedup doesn't stay silent for weeks.
  - Monitor: Apps Script exceptions in new checks propagate to the existing try/catch in `runAllChecks` (if present) or log-and-continue.
- **State lifecycle risks:**
  - `.cache/tempstick_last_checkin` missing → self-heals (next call writes it). ✓
  - `.cache/tempstick_last_checkin` corrupted (partial write) → mitigated by atomic write (`.tmp` + `os.replace`). Worst case if replace itself tears: one duplicate row, next run reseeds. ✓
  - `.cache/tempstick_dedup_health` counter → observable via collector log tail; stale cache surfaces as a daily-ish warning, not a silent failure. ✓
  - Apps Script Script Properties leak across script runs — `INDOOR_BASELINE_ALERTED` cooldown is self-clearing on median-below-threshold. ✓
- **API surface parity:**
  - No external-facing API changes. `dashboard.py`'s streamlit cache key unchanged (`load_raw`). Public function signatures in new loader match existing callers' expectations.
- **Integration coverage:**
  - Cross-layer: `checkDataCollection` now depends on Sheet data honestly reflecting sensor cadence. After #26 dedup ships, Temp Stick writes are sparse; the new time-window scan must handle this correctly. Unit 9's integration test exercises this.
- **Unchanged invariants:** Sheet schema (18 col), DGX collector path pin, hourly trigger, alert-email routing, all existing check functions. See Scope Boundaries for the full list — not duplicated here.

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Shared loader refactor introduces subtle behavior drift | Unit 1 test scenarios cover the schema-gate boundary explicitly. Unit 4 pre-fix diagnostic checks whether non-tempstick sensors are affected. Revert note: `rm .cache/air_quality.parquet` after `git revert` so streamlit's cached DataFrame also invalidates. |
| Dedup cache-file IO on DGX fails silently | Atomic writes via `.tmp` + `os.replace`. Stderr warning on read failure. `.cache/tempstick_dedup_health` counter makes prolonged breakage observable (daily-ish grep-able log line). User observes 24h row counts post-deploy to confirm. |
| `INDOOR_BASELINE.absoluteThreshold = 3` produces false alerts during cooking / candles / vacation / wildfire | `checkIndoorSpike` catches true spikes (+5 delta) first. Cooldown 60min. **Pre-Phase-2 backtest unit (optional, see Open Questions)** measures the 9-month base rate of "30-min rolling median > 3" to validate the threshold before ship. If base rate >1-2/week, tune before merging. |
| Re-alert thrashing if indoor PM oscillates around threshold | 60-min cooldown. If thrash observed post-deploy, add hysteresis (exit below a lower threshold). Defer unless observed. |
| User runs `test()` with stale `Script Properties` from prior experiments | Deploy checklist: "Optional — clear all `DATA_GAP_*` and `INDOOR_BASELINE_ALERTED` properties before first test run." |
| #28 retroactive data recovery surprises the dashboard — new non-NaN values in historical charts | Positive surprise, matches R1. Dashboard handles gracefully. |
| Wife's surgery window compresses Phase 2 deploy timing | Phase 1 (PRs 1 + 2) delivers data-integrity + dedup wins independently. Phase 2 PR can sit open for days with no risk — #27 fix for yesterday's scenario waits, but the sprint closure doesn't block the surgery window. |
| Apps Script deploy drift — repo version ≠ running version | `MONITOR_VERSION` constant logged per `runAllChecks()` invocation. Future drift is grep-able from execution log, not a mystery. |

Deployment procedure (moved out of the risk register — this is a checklist, not a risk):
- Paste entire file when deploying Apps Script changes. Partial pastes can throw at runtime; no code-level guard covers that fully.

## Documentation / Operational Notes

- **Changelog**: Three entries for v0.6.0-dev (one per PR). Each entry should reference the fixing issue number.
- **`docs/LESSONS_LEARNED.md`**: After Phase 1a merge, add a lessons entry about date-gating data-repair logic (from #28).
- **`HVACMonitor_v3.gs` top comment block**: Update the "KEY CONCEPTS" section to mention per-sensor cadence and indoor baseline check.
- **Monitoring**: No new operational dashboards. Existing collector logs + email alerts are sufficient. User reviews 24h post-Phase-1b merge to confirm dedup worked (row count).
- **Rollback paths**: Each PR is a clean revert if problems emerge. Apps Script: user re-pastes prior `HVACMonitor_v3.gs` version from git history.

## Sources & References

- **Origin issues:**
  - #25 — https://github.com/minghsuy/hvac-air-quality-analysis/issues/25
  - #26 — https://github.com/minghsuy/hvac-air-quality-analysis/issues/26
  - #27 — https://github.com/minghsuy/hvac-air-quality-analysis/issues/27
  - #28 — https://github.com/minghsuy/hvac-air-quality-analysis/issues/28
- **Related PRs (merged this week):**
  - #24 — collector UA fix (precondition — attic API access restored)
  - #23 — repo tidy-pass + anti-regrowth pre-push guardrail (provides the `scripts/hooks/pre-push` discipline these PRs must pass)
- **Critical code paths:**
  - `collect_with_sheets_api_v2.py:310-346` (`get_tempstick_data`)
  - `collect_with_sheets_api_v2.py:388` (`build_temp_only_row`) — row-shape invariant to preserve
  - `scripts/refresh_cache.py:62-102` — reference for the shared loader
  - `scripts/dashboard.py:60-110` — streamlit-wrapped copy
  - `scripts/bench_heatmap.py:23-95` — third copy
  - `HVACMonitor_v3.gs:36-100` (`CONFIG`)
  - `HVACMonitor_v3.gs:127-183` (`runAllChecks`)
  - `HVACMonitor_v3.gs:476-538` (`checkIndoorSpike` — pattern for `checkIndoorBaseline`)
  - `HVACMonitor_v3.gs:664-728` (`checkDataCollection` — rewrite target)
- **Session context:** This plan was built immediately after filing #27 and #28 in the same conversation where #25, #26, #23, and #24 were filed or merged. Fresh knowledge of every code path cited.
