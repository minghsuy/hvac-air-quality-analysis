# HVAC Air Quality Project - Backlog

> Prioritized task list for Claude Code and human collaboration
>
> Last updated: February 2026
> Target: LinkedIn post in March 2026

## Priority Legend

- 🔴 P0: Must do before LinkedIn post
- 🟡 P1: Should do, high impact
- 🟢 P2: Nice to have
- ⚪ P3: Future / someday

---

## Completed (Feb 2026)

### ✅ Interactive Dashboard (was P0/P1)

- [x] **Streamlit + Plotly dashboard** (`scripts/dashboard.py`)
  - 7-page multi-page app hosted on DGX Spark (port 8501)
  - Pages: Overview, CO₂ Compare, Heatmaps, VOC & NOX, Filter & PM2.5, Environment, Correlations
  - 4 visualization styles: rolling avg + band, heatmap, box plots, LOWESS + anomaly detection
  - Heatmaps for all 14 metrics organized by Indoor Air / Outdoor / Comfort
  - Weekday vs weekend profiles, monthly profiles
  - Parquet cache: 18ms load vs 3.5s Google Sheets API (106x faster)
  - Pre-aggregation: hourly + daily summaries cached in session state
  - Date range picker with presets (7d/30d/90d/All)

- [x] **Multivariate correlation analysis**
  - Spearman rank correlation (default) — robust to outliers, captures monotonic relationships
  - Pearson available as toggle for comparison
  - 14-metric correlation matrix with notable pairs highlighted
  - Outdoor → Indoor scatter plots with trend lines
  - ERV tradeoff visualization (CO₂ vs PM2.5 dual axis)

- [x] **Data quality fixes**
  - Column shift bug (pre-Sep 2025, 17-col rows) — NaN affected columns via `_orig_cols` tracking
  - Second bedroom sensor = near kitchen (cooking spike context)
  - Oct 2025 data gap (migration from UI cloud to DGX Spark)

### Key Findings from Correlation Analysis (Spearman)

| Pair | ρ | Insight |
|------|---|---------|
| Indoor PM2.5 ↔ Filter Efficiency | -0.96 | Near-perfect inverse, validates data |
| CO₂ ↔ VOC | 0.65 | Both rise with low ventilation — ERV signal |
| Outdoor PM2.5 ↔ Radon | 0.59 | Atmospheric stagnation drives both |
| Outdoor Temp ↔ Outdoor CO₂ | -0.59 | Winter inversions trap CO₂ |
| Outdoor VOC ↔ Outdoor NOX | -0.45 | Different sources, opposite seasonality |

---

## Phase 1: Polish for LinkedIn (Target: March 2026)

### 🔴 P0: README Restructure

- [ ] **Surface the "Why" story in README**
  - Copy opening paragraph from Wiki "Why This Project Matters"
  - Add link to full Wiki story
  - Move technical content below the human story

- [ ] **Add "Results" section to README**
  - Update row count to 98k+ readings
  - Include correlation findings (CO₂ ↔ VOC, ERV tradeoff)
  - Add dashboard screenshots

- [ ] **Add architecture diagram to README**
  - Show sensor → collection → sheets → dashboard → alerting flow
  - Include DGX Spark as compute node
  - Mermaid diagram preferred (renders on GitHub)

### 🔴 P0: Static Visualizations for README/LinkedIn

- [ ] **Export key charts as PNG from dashboard**
  - CO₂ heatmap showing ERV flow change (before/after Thanksgiving)
  - Filter efficiency over time (>85% past 120 days)
  - Correlation matrix (Spearman) — shows all metric relationships
  - ERV tradeoff chart (CO₂ vs PM2.5)
  - Indoor vs outdoor PM2.5 during high AQI event

### ~~🔴 P0: PR for Dashboard Work~~ ✅

- [x] **Create PR with dashboard + benchmark + analysis**
  - `scripts/dashboard.py` — multi-page Streamlit dashboard
  - `scripts/bench_heatmap.py` — performance benchmark
  - `.cache/` in `.gitignore`
  - Update dependencies in `pyproject.toml` (streamlit, statsmodels, polars)

### 🟡 P1: Documentation

- [ ] **Add dashboard section to README**
  - Screenshots of key pages
  - How to run locally
  - Architecture: Sheets API → Parquet cache → Streamlit

- [ ] **Sync Wiki with current state**
  - Analysis Techniques page: add Spearman correlation, LOWESS, heatmap methodology
  - Add dashboard as primary analysis tool

---

## Phase 2: Deeper Analysis (Target: April 2026)

### 🟡 P1: ERV Decision Engine

- [ ] **Build ERV flow recommendation logic**
  - Use CO₂ + VOC as "need more air" signal (ρ=0.65, both rise together)
  - Check Outdoor PM2.5 + Outdoor NOX before recommending high flow
  - Outdoor VOC as "smell risk" indicator (wife's complaint)
  - Seasonal thresholds (winter inversions vs summer clean air)

- [ ] **Add recommendation panel to dashboard**
  - Current ERV flow recommendation based on latest readings
  - "Turn up" when CO₂ > X AND Outdoor PM2.5 < Y
  - "Keep low" when Outdoor NOX > Z (smell/pollution risk)

### 🟡 P1: Cooking Event Detection

- [ ] **Identify cooking events from PM2.5 spikes**
  - Second bedroom (kitchen) sensor as primary detector
  - Time-of-day patterns (dinner hours)
  - Separate cooking spikes from actual air quality events
  - Quantify: how long does PM2.5 stay elevated after cooking?

### 🟡 P1: Weather Correlation

- [ ] **Integrate weather API data**
  - Rain events → outdoor PM2.5 suppression (observed Nov 2025)
  - Temperature inversions → elevated outdoor CO₂ and PM2.5
  - Wind speed/direction → outdoor VOC/NOX variations
  - Correlate with existing sensor data

### 🟢 P2: Anomaly Detection

- [ ] **Automated anomaly alerts**
  - LOWESS baseline + threshold detection (already prototyped in CO₂ Compare)
  - Alert when CO₂ + VOC both elevated (ventilation insufficient)
  - Alert when Outdoor PM2.5 + Radon both elevated (atmospheric stagnation)
  - Push notifications (email, Slack, or dashboard toast)

### 🟢 P2: Attic Monitoring Analysis

- [ ] **Tempstick data analysis**
  - Attic temp vs outdoor temp → insulation effectiveness
  - Humidity trends → moisture/mold risk detection
  - Seasonal patterns

---

## Phase 3: Automation (Target: Later 2026)

### 🟢 P2: ERV Control

- [ ] **Research ERV control options**
  - Smart relay on ERV power?
  - Integration with existing switches?
  - Home Assistant bridge?

- [ ] **Implement automated ERV control**
  - Based on decision engine from Phase 2
  - CO₂ + VOC + Outdoor PM2.5 + Outdoor NOX as inputs
  - Cooldown periods to avoid cycling
  - Override for manual control

### 🟢 P2: Carrier Integration

- [ ] **Research Carrier Infinity API**
  - Côr thermostat API?
  - Local control vs cloud?

- [ ] **Implement filter status sync**
  - Read filter runtime from Carrier
  - Correlate with efficiency data

---

## Phase 4: Make it Deployable (Target: 2027)

### ⚪ P3: Simplified Setup

- [ ] One-click sensor discovery
- [ ] Configuration wizard
- [ ] Pre-built Docker containers
- [ ] Setup documentation for non-engineers

### ⚪ P3: Multi-family Support

- [ ] Support different sensor combinations
- [ ] Configurable alerting rules
- [ ] Dashboard templates

---

## Wiki Repository Management

The GitHub Wiki is a **separate git repository**. Handle it carefully:

```bash
# Wiki repo location (on DGX Spark)
~/hvac-air-quality-analysis/wiki-repo/

# Clone if not exists
git clone https://github.com/minghsuy/hvac-air-quality-analysis.wiki.git wiki-repo

# NEVER do this (embeds git repo in git repo):
git add wiki-repo  # NO!
```

**Wiki is in .gitignore** - this is correct, keep it that way.

---

## Notes for Claude Code

When working on this project:

1. **Read CLAUDE.md first** - contains git workflow, security checks, package management rules
2. **Use feature branches** - never push to main directly
3. **Run security grep before commits** - check for IPs, emails, credentials
4. **Use uv, not pip** - this project uses uv package manager
5. **Wiki is separate** - don't try to git add wiki-repo

When creating visualizations:
- Use Plotly (interactive) for dashboard, Matplotlib for static PNGs
- Use Spearman correlation for sensor data (robust to outliers, non-linear relationships)
- Keep it simple - one insight per chart
- Add annotations to highlight key points
- Pre-aggregate data to avoid browser performance issues
