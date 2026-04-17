# Reports

Self-contained, shareable artifacts served by GitHub Pages. Live URL:

```
https://minghsuy.github.io/hvac-air-quality-analysis/reports/findings.html
```

Regenerate with:

```
uv run python scripts/analysis/verify_findings.py
uv run python scripts/analysis/screenshot_report.py   # optional visual check
```

Each artifact is a single HTML file with Plotly loaded from CDN — works in any browser with internet access. Commit updates when the underlying claims change.

| File | Purpose |
|---|---|
| `findings.html` | Reproduces the headline findings from `docs/findings.md` and the Feb 7-8 2026 alert case study against 142k+ parquet rows. Citable evidence pack. |
