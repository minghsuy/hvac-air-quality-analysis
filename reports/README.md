# Reports

Self-contained, shareable artifacts generated from the parquet cache. Regenerate with:

```
uv run python scripts/analysis/verify_findings.py
```

Each artifact is a single HTML file with embedded Plotly charts — viewable in any browser, no server required. Commit updates when the underlying claims change.

| File | Purpose |
|---|---|
| `findings.html` | Reproduces the headline findings from `docs/findings.md` and the Feb 7-8 2026 alert case study against 142k+ parquet rows. Citable evidence pack. |
