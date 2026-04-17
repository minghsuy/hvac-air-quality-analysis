# Lessons Learned

## July 27, 2025: GitHub Wiki Management

**Problem**: Tried to manage wiki pages from main repository, leading to confusion.

**Discovery**: GitHub Wiki is a completely separate Git repository.
- Main repo: `https://github.com/username/project.git`
- Wiki repo: `https://github.com/username/project.wiki.git`

**Solution**: Clone wiki separately and manage independently.

## July 27, 2025: Plotly Export Issues

**Problem**: Datetime x-axis showing as scientific notation (1.745×10¹⁸) in exported PNGs.

**Discovery**: Kaleido has issues with datetime axes.

**Solution**: Convert datetime to string format before plotting:
```python
x_dates = df.index.strftime('%b %d')
fig.add_trace(go.Scatter(x=x_dates, y=df['value']))
```

## July 27, 2025: Visualization Tools Research

**Problem**: Building custom visualization pipeline when solutions already existed.

**Discovery**: Found excellent existing tools in research:
- **Quarto**: Modern "write once, deploy everywhere"
- **Playwright > Kaleido**: More reliable for Plotly exports
- **nb2hugo**: Direct Jupyter to Hugo integration

**Lesson**: Always check if someone has already solved your problem.

## Aug 8, 2025: Data Collection Outage

**Problem**: Data collection stopped unexpectedly.

**Discovery**: Firmware update removed cron job configuration.

**Solution**: Migrated to systemd user services with linger for true persistence.

## Aug 29, 2025: Filter Efficiency Confusion

**Problem**: 71% efficiency with brand new filter seemed wrong.

**Discovery**: Low outdoor PM2.5 (< 5 μg/m³) makes efficiency % unreliable.

**Solution**: Focus on absolute indoor PM2.5 values when outdoor air is clean.

## Aug 30, 2025: Multi-Sensor Deployment

**Problem**: .local domains don't resolve on some network configurations.

**Discovery**: mDNS support varies by network setup.

**Solution**: Created IP discovery script to update sensors.json with current IPs.

## Aug 30, 2025: Release Process Failure

**Problem**: Released v0.3.0 with 49 linting errors.

**Discovery**: Skipped pre-release quality checks.

**Solution**: Created RELEASE_CHECKLIST.md with mandatory pre-release steps:
1. Run tests first
2. Fix linting issues
3. Format code
4. Then proceed with release

## Package Management Confusion

**Problem**: Suggesting pip install commands when project uses uv.

**Discovery**: This project exclusively uses uv package manager.

**Solution**: Added clear warnings in CLAUDE.md about uv vs pip.

## Not a Python Package

**Problem**: GitHub Actions trying to build Python package.

**Discovery**: This is a collection of scripts, not a package.

**Solution**: Set `package = false` in pyproject.toml, create archives instead.

## Jan 17, 2026: Load-Based Filter Life Prediction Failed

**Problem**: The HVACMonitor v2 code used cumulative load index to predict filter life (maxLoadIndex 500), but the main filter showed 987 cumulative load yet still had 87.3% efficiency - it should have been "dead" by this metric.

**Discovery**: Load-based prediction doesn't correlate with actual filter degradation. Data analysis of 82,791 readings showed:
- Filter at 197% of "max life" still performing well
- ERV filter showed real improvement after replacement (78.4% → 90.9%)
- The calculated "days remaining" was meaningless

**Solution**: Removed load-based calculations entirely. Switched to efficiency-based alerts only:
- Measure actual filter efficiency: `((outdoor_PM25 - indoor_PM25) / outdoor_PM25) * 100`
- Alert when efficiency drops below thresholds (75% warning, 65% critical)
- This measures real performance, not theoretical decay

## Jan 17, 2026: Robust Efficiency Measurement

**Problem**: How to measure filter efficiency reliably when data has outliers and noise?

**Discovery**: Analyzed actual data to validate measurement approach:
- 0% negative readings (no data quality issues)
- 0% readings over 100%
- Median, percentile-95, and trimmed mean all agree within 1.3%
- 48.3% of readings occur when outdoor PM2.5 < 5 μg/m³

**Solution**:
1. Use median for robust central tendency (immune to outliers)
2. Require minimum outdoor PM2.5 threshold for high-confidence readings
3. Store all readings but only alert on high-confidence data

## Jan 17, 2026: Seasonal Measurement Gap

**Problem**: "Will we never change the filter in summer since air quality is so good?"

**Discovery**: Summer has consistently low outdoor PM2.5 (often < 5 μg/m³), making efficiency calculations unreliable. A fixed minimum threshold would either:
- Miss summer measurements entirely (threshold too high)
- Include unreliable data year-round (threshold too low)

**Solution**: Seasonal minOutdoorPM thresholds:
```javascript
minOutdoorPM: {
  winter: 10,  // Dec-Feb: More pollution, higher bar
  summer: 5,   // Jun-Aug: Clean air, lower bar
  default: 7,  // Spring/Fall: Moderate
}
```

Calibrated thresholds from actual data:
- Winter: 74% warning / 62% critical
- Summer: 77% warning / 63% critical
- Default: 70% warning / 59% critical

## Jan 17, 2026: Zone Filters vs Main Filters

**Problem**: Zone filters (12x12x1) protect air blowers but don't affect indoor/outdoor PM2.5 differential.

**Discovery**: These small filters in individual rooms can't be measured by efficiency - they're not in the main air path. They need time-based replacement reminders.

**Solution**: Dual tracking approach:
- **Main/ERV filters**: Efficiency-based alerts (actual performance measurement)
- **Zone filters**: Time-based reminders (90 days default, configurable)

## Jan 17, 2026: Ask Data, Not Assumptions

**Problem**: When asked about robust measurement methods, I asked the user instead of analyzing the data.

**Discovery**: The project has 82,791+ real readings. Running analysis on actual data is more valuable than theoretical discussion.

**Solution**: When there's real data available, analyze it first:
```javascript
// Added analyzeEfficiencyData() function that:
// - Counts readings in different ranges
// - Compares measurement methods (median vs mean vs trimmed)
// - Shows seasonal patterns
// - Validates data quality
```

Always prefer evidence over assumptions.

## Apr 16, 2026: Grep ≠ Render (HTML Chart Verification)

**Problem**: Declared a Plotly-based HTML report "ready for review" after grepping the source for `plotly-graph-div` and seeing two matches. Section 1's chart was blank — load-order bug (`include_plotlyjs=False` on the first chart div, `cdn` on the second) meant Plotly.js wasn't loaded when the first div's init script ran. Only surfaced when the user opened the file in a browser.

**Discovery**: Structural verification (file exists, element count correct, syntax valid) is not rendering verification. Modern web artifacts have client-side execution that only a real browser exercises.

**Solution**: Added `scripts/analysis/screenshot_report.py` — Playwright-based headless rendering that asserts each chart div has bounding-box area ≥100k px². Wired into the pre-push hook to run conditionally when the HTML or its generators change. CLAUDE.md already listed Playwright MCP for this purpose; I just wasn't using it.

## Apr 16, 2026: Verify Hosting Config Before Placing Artifacts

**Problem**: Placed a "shareable" HTML report at `/reports/findings.html` at repo root. GitHub Pages is configured to serve `docs/` only (via `docs/_config.yml`). The artifact was invisible to the web, defeating the entire shareable-URL purpose.

**Discovery**: Before creating any file intended to be hosted, check the actual hosting config. Assuming a generic "generated artifacts" convention (like `dist/`) will be hostable is wrong for Jekyll/GitHub Pages.

**Solution**: Moved `reports/` → `docs/reports/`. Live URL becomes `https://<user>.github.io/<repo>/reports/findings.html`. Kept `reports/screenshots/` (ephemeral verification output) at repo root, gitignored.

## Apr 16, 2026: Sensor-Rounding Artifact ≠ Perfect Filtration

**Problem**: Reported "100.0% median filter efficiency" for the first OEM MERV 13 period. Not a measurement of real filtration — the Airthings indoor PM2.5 sensor rounds to integers, so when actual indoor PM is below 0.5 µg/m³ the sensor reports 0 and efficiency pegs at 100% regardless of physical reality. 64% of the period's valid readings hit this case.

**Discovery**: Before computing on sensor data, understand each value's physical meaning. `Indoor_PM25 = 0` on an integer-rounding sensor isn't "zero PM" — it's "PM below the sensor's resolution." Arithmetic on it produces plausible-looking but meaningless numbers.

**Solution**: Added `indoor_zero_pct` column to the cycles table so rounding exposure is visible per period. Caveat explains the mechanism. Claims are now lower-bounded (the generic substitute's 69% is real with only 4% zeros) rather than pegged to a resolution-limited ceiling.

## Apr 16, 2026: Pre-Push Checklist, Not Ad-Hoc Checks

**Problem**: Three separate CI/review catches in one session: (1) `ruff format --check` failing after I ran only `ruff check --fix` (CLAUDE.md lists both as mandatory), (2) `uv.lock` revision regressed from 3 → 2 because my local uv was old, (3) hardcoded sensor identifiers (device serials, MAC fragments) that bypassed the existing `d8:3b:da` grep because they used different vendor prefixes.

**Discovery**: Individually these are small. Together they're a pattern: I was running checks ad hoc rather than as a disciplined sequence. Every one of them was caught after push by CI or review, when a 10-second local check would have caught it before.

**Solution**: `scripts/hooks/pre-push` runs ruff check + ruff format --check + a broader device-ID grep (sensor-ID patterns for airthings/airgradient/tempstick/ecobee/nest, not only `d8:3b:da`) + conditional screenshot verify. Install via `bash scripts/install-hooks.sh` — sets up symlinks from `.git/hooks/` to the tracked `scripts/hooks/` versions.