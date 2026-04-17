# Project Structure

## Directory layout

```
.
├── README.md                           # Overview and quick start
├── CLAUDE.md                           # AI-assistant guardrails for this repo
├── CHANGELOG.md                        # Version history (kept at root by convention)
├── LICENSE
├── HVACMonitor_v3.gs                   # Apps Script source (copy/paste into Google Sheets)
├── collect_with_sheets_api_v2.py       # Main collector — DGX systemd pins this absolute path
├── collect_multi_fixed.py              # Local-only collector variant (gitignored; real sensor IDs)
├── pyproject.toml                      # uv-managed dependencies (package = false)
├── uv.lock
├── cliff.toml                          # git-cliff config for CHANGELOG generation
├── filter_changes_template.csv         # Template: filter-replacement log
├── sensors.template.json               # Template: sensor config
│
├── .env.example                        # Copy to .env and fill in
├── .gitignore
├── .pre-commit-config.yaml
│
├── data/                               # Local CSV exports (gitignored)
├── .cache/                             # Parquet cache for dashboard (gitignored)
├── reports/                            # Screenshot artifacts from CI verify (gitignored)
│
├── docs/                               # GitHub Pages content + reference docs
│   ├── index.md                        # Landing page
│   ├── what-my-homes-air-taught-me.md  # Long-form findings piece
│   ├── ARCHITECTURE.md
│   ├── BACKLOG.md
│   ├── CLAUDE_CODE_CONTEXT.md
│   ├── DATA_DICTIONARY.md
│   ├── LESSONS_LEARNED.md
│   ├── PROJECT_STRUCTURE.md            # This file
│   ├── RELEASE_CHECKLIST.md
│   ├── TROUBLESHOOTING.md
│   ├── findings.md
│   ├── methodology.md
│   ├── dashboard-architecture.md
│   ├── data-quality.md
│   ├── 5_MINUTE_INTERVALS.md
│   ├── AI_ANALYSIS_PLAN.md
│   ├── _config.yml                     # Jekyll config
│   ├── charts/                         # Generated Plotly HTML
│   └── reports/                        # Generated findings.html + embedded charts
│
├── scripts/
│   ├── dashboard.py                    # Streamlit dashboard entry point
│   ├── fix_cron.sh                     # Cron repair helper
│   ├── install-hooks.sh                # Install git hooks from scripts/hooks/
│   ├── refresh_cache.py                # Manual parquet refresh from Sheets
│   ├── setup_google_sheets_api.py      # First-time Sheets API config
│   ├── read_sheets_simple.py
│   ├── update_airgradient_ips.py
│   ├── analysis/                       # Analysis + verification scripts
│   │   ├── verify_findings.py          # Regenerates docs/reports/findings.html
│   │   └── screenshot_report.py        # Playwright visual verify (CI + pre-push)
│   ├── collectors/                     # Non-production collector variants
│   │   └── collect_multi_fixed.template.py
│   ├── utils/                          # Reusable utilities
│   │   ├── analyze_historical.py
│   │   ├── check_timestamps.py
│   │   ├── generate_wiki_images.py
│   │   ├── read_google_sheets.py
│   │   └── read_google_sheets_secure.py
│   └── hooks/
│       └── pre-push                    # ruff + secrets + uv.lock + root-junk guardrail
│
├── systemd/                            # DGX systemd unit + timer for the collector
├── tests/                              # pytest suite
└── wiki-repo/                          # Separate git repo for GitHub Wiki (gitignored)
```

## What stays at root on purpose

| File | Reason |
|---|---|
| `collect_with_sheets_api_v2.py` | DGX `systemd/air-quality-collector.service` hardcodes its absolute path. Moving it breaks production on the next pull. |
| `HVACMonitor_v3.gs` | Copy-paste-ready Apps Script source; README surfaces it as a top-level artifact. |
| `README.md`, `CLAUDE.md`, `LICENSE`, `CHANGELOG.md` | GitHub and tooling conventions expect these at root. |
| `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, `cliff.toml`, `.pre-commit-config.yaml` | Tooling config files; tooling looks for them at repo root. |
| `*.template.csv`, `*.template.py`, `*.template.json` | Templates allowed at root under the `!*_template.*` gitignore rule; copies become gitignored real files. |

## Where new files should land

| Kind | Directory |
|---|---|
| Analysis / verification scripts | `scripts/analysis/` |
| Collector variants (non-production) | `scripts/collectors/` |
| Reusable helpers | `scripts/utils/` |
| Reference docs, long-form writeups | `docs/` |
| Local data exports | `data/` (gitignored) |
| One-off debug output | `.cache/` or out of repo entirely |

The `scripts/hooks/pre-push` guardrail (Section 8) enforces this: any new `.py`, `.csv`, `.json`, or debug-pattern file pushed to root is rejected, with the one exception of the DGX-pinned collector.

## Data flow

```
Sensors (Airthings, AirGradient, Temp Stick)
        │  5-minute systemd timer on DGX
        ▼
collect_with_sheets_api_v2.py  ──► Google Sheets (source of truth)
                                         │
                                         ├──► HVACMonitor_v3.gs  (hourly alerts, email)
                                         │
                                         └──► scripts/refresh_cache.py  ──► .cache/air_quality.parquet
                                                                                   │
                                                                                   ▼
                                                                          scripts/dashboard.py (Streamlit)
                                                                          scripts/analysis/verify_findings.py (HTML)
```

## Storage

| Data | Location | Persistence |
|---|---|---|
| Raw sensor readings | Google Sheets | Permanent |
| Analytical cache | `.cache/air_quality.parquet` | Local, regenerated on demand |
| Collector logs | `journalctl --user -u air-quality-collector` (DGX) | System-managed |
| Published findings | `docs/reports/findings.html` (GitHub Pages) | Versioned in repo |

## Reminders

- Never commit: `.env`, `google-credentials.json`, `sensors.json` (real IPs), `collect_multi_fixed.py` (non-template).
- Use `uv`, never `pip`.
- `pyproject.toml` sets `package = false` — no `*.egg-info/` should ever exist.
