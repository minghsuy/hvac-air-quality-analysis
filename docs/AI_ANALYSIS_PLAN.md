# AI-Powered Air Quality Analysis with RAPIDS AI & Ollama

> **Status: aspirational plan document from late 2025, partially superseded.**
> The alerts, ERV-state inference, and anomaly attribution described below were
> implemented in [`HVACMonitor_v3.gs`](https://github.com/minghsuy/hvac-air-quality-analysis/blob/main/HVACMonitor_v3.gs) (Google Apps Script) and the
> [Streamlit dashboard](dashboard-architecture.md). The RAPIDS/cuDF GPU path was
> not built — production analysis uses pandas + scipy. The example CLI outputs
> below (efficiencies, replacement dates) are **illustrative mockups**, not
> findings from real data. For actual measured findings see
> [findings.md](findings.md) and the [verification report](reports/findings.html).

## Overview

Build an analysis system for historical air quality data that:
1. Uses **cuDF/RAPIDS AI** for GPU-accelerated data processing (learning opportunity)
2. Uses **Ollama** (OSS 120B, fallback: Mistral) for natural language explanations
3. Provides filter replacement predictions, anomaly detection, and health impact analysis
4. **Actionable alerts for your wife** - real-time notifications with specific actions (e.g., "Turn OFF ERV")

## Goals

- **Primary**: Learn NVIDIA's data science toolkit (cuDF, RAPIDS) hands-on
- **Secondary**: Actionable alerts for family (especially wife) about air quality
- **Tertiary**: Create reusable analysis pipeline

## Key Features

### 1. Filter Change Tracking (Google Sheets Tab)
Track multiple filter types:
- **Zone filters** (bedroom HVAC units)
- **Main MERV 15 filter** (whole house)
- **ERV filter**

New tab: `Filter_Changes` with columns:
| Date | Filter_Type | Location | Notes |
|------|-------------|----------|-------|
| 2025-12-01 | zone | master_bedroom | Replaced with MERV 13 |
| 2025-11-15 | main | whole_house | MERV 15 installed |
| 2025-10-01 | erv | erv_unit | Cleaned filter |

### 2. Smart ERV State Detection
Infer if ERV is ON/OFF from sensor data:
```
ERV ON indicators:
- CO2 decreasing or stable (fresh air coming in)
- Indoor/outdoor temp converging
- Indoor humidity tracking outdoor

ERV OFF indicators:
- CO2 steadily rising (no fresh air)
- Indoor temp stable (no heat exchange)
- Indoor humidity diverging from outdoor
```

### 3. Actionable Wife-Friendly Alerts
**Example alert when outdoor air is bad:**
```
🔴 HIGH OUTDOOR PM2.5 - ACTION NEEDED

Outdoor PM2.5: 85 μg/m³ (unhealthy - wildfire smoke)
Indoor PM2.5: 12 μg/m³ (moderate but rising)

⚠️  ERV appears to be ON (CO2 dropping)

RECOMMENDED ACTION:
→ Turn OFF the ERV NOW to stop smoke infiltration
→ Your MERV 15 will clean existing indoor air

I'll notify you when outdoor air is safe again.
```

**Example alert for cooking spike (no action needed):**
```
🟡 INDOOR PM2.5 SPIKE - NO ACTION NEEDED

Indoor PM2.5: 28 μg/m³ (elevated)
Outdoor PM2.5: 5 μg/m³ (excellent)

LIKELY CAUSE: Indoor activity (cooking/cleaning)
→ This is temporary, will clear in 15-30 minutes
→ Range hood recommended if cooking
```

### 4. Anomaly Attribution Logic
```
IF indoor spike AND outdoor normal → Activity (cooking/cleaning)
IF indoor spike AND outdoor spike → Outdoor infiltration
IF efficiency declining over 7+ days → Filter degradation
IF efficiency suddenly drops AND stays low → HVAC problem
IF CO2 rising + outdoor PM2.5 high + indoor PM2.5 rising → ERV is ON, should be OFF
```

## Architecture

```
Google Sheets (18 columns, <10K rows)
         │
         ▼
┌─────────────────────────┐
│   Data Fetcher          │  (pandas → cuDF conversion)
│   read_google_sheets    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   RAPIDS Analysis       │  (cuDF DataFrames, GPU-accelerated)
│   ├─ Filter Predictor   │  (cuML linear regression)
│   ├─ Anomaly Detector   │  (cuML isolation forest)
│   └─ Health Analyzer    │  (cuDF groupby/aggregations)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Ollama LLM            │  (llama3.2 or mistral)
│   ├─ Explain results    │
│   ├─ Recommendations    │
│   └─ Interactive Q&A    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Output                │
│   ├─ CLI report         │
│   ├─ Markdown file      │
│   └─ Interactive mode   │
└─────────────────────────┘
```

## File Structure

```
hvac-air-quality-analysis/
├── ai_analysis/                    # New module
│   ├── __init__.py
│   ├── analyzer.py                 # Main orchestrator
│   ├── data_loader.py              # Sheets → cuDF conversion
│   ├── filter_predictor.py         # cuML linear regression
│   ├── anomaly_detector.py         # cuML isolation forest
│   ├── health_analyzer.py          # cuDF aggregations
│   ├── llm_explainer.py            # Ollama integration
│   └── prompts/
│       ├── summary.txt
│       ├── recommendations.txt
│       └── qa.txt
├── ai_analyze.py                   # CLI entry point
└── reports/                        # Generated reports
    └── .gitkeep
```

## Key RAPIDS Concepts to Learn

### 1. cuDF Basics (data_loader.py)
```python
import cudf
import pandas as pd

# Convert pandas to cuDF (GPU DataFrame)
pdf = pd.read_csv("data.csv")
gdf = cudf.DataFrame.from_pandas(pdf)

# cuDF operations (same API as pandas, but GPU-accelerated)
gdf['efficiency_rolling'] = gdf['Filter_Efficiency'].rolling(window=12).mean()
hourly_avg = gdf.groupby(gdf['Timestamp'].dt.hour)['Indoor_PM25'].mean()
```

### 2. cuML for Predictions (filter_predictor.py)
```python
from cuml.linear_model import LinearRegression

# GPU-accelerated linear regression
model = LinearRegression()
model.fit(X_gpu, y_gpu)
predictions = model.predict(future_X)
```

### 3. cuML for Anomaly Detection (anomaly_detector.py)
```python
from cuml.ensemble import RandomForestClassifier
from cuml.preprocessing import StandardScaler

# GPU-accelerated anomaly detection
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features_gpu)
# Use isolation forest or statistical methods
```

## Implementation Steps

### Phase 1: Setup & Data Loading
1. Add RAPIDS dependencies to pyproject.toml
2. Create `ai_analysis/data_loader.py`:
   - Fetch data from Google Sheets (existing SecureGoogleSheetsReader)
   - Convert pandas DataFrame to cuDF
   - Handle data cleaning on GPU
   - Add helper for pandas fallback if no GPU

### Phase 2: Filter Prediction with cuML
3. Create `ai_analysis/filter_predictor.py`:
   - Use cuML LinearRegression for trend analysis
   - Calculate degradation rate per room
   - Predict replacement dates
   - Compare GPU vs CPU performance (learning)

### Phase 3: Anomaly Detection with cuML
4. Create `ai_analysis/anomaly_detector.py`:
   - Detect PM2.5 spikes (cooking events)
   - Detect sensor issues (stuck values)
   - Detect HVAC problems (sudden efficiency drops)
   - Use cuDF for fast rolling statistics

### Phase 4: Health Analysis with cuDF
5. Create `ai_analysis/health_analyzer.py`:
   - Hourly patterns (cuDF groupby)
   - Room comparisons
   - WHO guideline compliance
   - Exposure time calculations

### Phase 5: Ollama Integration
6. Create `ai_analysis/llm_explainer.py`:
   - Connect to local Ollama
   - Format analysis results for LLM context
   - Generate natural language summaries
   - Interactive Q&A mode

### Phase 6: CLI & Integration
7. Create `ai_analysis/analyzer.py` (orchestrator)
8. Create `ai_analyze.py` (CLI entry point)
9. Add report generation (markdown, JSON)

## Dependencies to Add

As of [RAPIDS 24.12](https://developer.nvidia.com/blog/rapids-24-12-introduces-cudf-on-pypi-cuda-unified-memory-for-polars-and-faster-gnns/), cuDF is available directly on PyPI - no extra index needed!

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    "ollama>=0.4.0",
    "cudf-cu12>=24.12",      # GPU DataFrame (CUDA 12)
    "cuml-cu12>=24.12",      # GPU ML algorithms
]
```

**Installation via uv**:
```bash
# Simply run:
uv add ollama cudf-cu12 cuml-cu12

# Or sync after editing pyproject.toml:
uv sync
```

Your system: **NVIDIA GB10** (Grace Blackwell, compute 12.1) with CUDA 12 - fully supported!

## CLI Usage Examples

```bash
# Full analysis with GPU + LLM
python ai_analyze.py --days 30

# Quick analysis without LLM
python ai_analyze.py --days 7 --no-llm

# Interactive Q&A mode
python ai_analyze.py --interactive

# Save report
python ai_analyze.py --output markdown --save reports/analysis_2025-12-01.md

# Force CPU mode (for comparison/fallback)
python ai_analyze.py --cpu-only
```

## Example Output

```
================================================================================
           AI-POWERED AIR QUALITY ANALYSIS (RAPIDS + Ollama)
                      Generated: 2025-12-01 21:30:00
           Processing: GPU (cuDF) | Model: llama3.2:3b
================================================================================

📊 SUMMARY (AI Generated)
─────────────────────────
Your indoor air quality is excellent. The master bedroom filter maintains 87%
efficiency after 45 days - well above the 80% threshold. Based on the current
degradation rate of 0.3% per week, replacement is recommended around mid-January.

🔧 FILTER STATUS
────────────────
  Room              Efficiency   Age    Predicted Replacement   Confidence
  ─────────────────────────────────────────────────────────────────────────
  Master Bedroom    87.2%        45d    Jan 15, 2026 (45 days)  HIGH
  Second Bedroom    84.1%        45d    Jan 02, 2026 (32 days)  MEDIUM

⚠️  ANOMALIES DETECTED (Last 24h)
─────────────────────────────────
  • 18:32 - Cooking spike in Master Bedroom (PM2.5: 28 → 3 μg/m³, 25 min)
  • 07:15 - Morning activity spike (CO2: 890 → 650 ppm, 45 min)

💚 HEALTH METRICS
─────────────────
  WHO Guideline Compliance: 97.7% (excellent)
  Average Indoor PM2.5: 4.2 μg/m³ (target: <15)
  Best Hours: 02:00-06:00 (avg 1.2 μg/m³)
  Worst Hours: 18:00-19:00 (avg 8.5 μg/m³)

🎯 RECOMMENDATIONS (AI Generated)
─────────────────────────────────
  1. [LOW] Use range hood during cooking to reduce PM2.5 spikes
  2. [INFO] Schedule filter replacement for early January
  3. [INFO] Current ventilation is adequate - CO2 levels healthy

⚡ Performance: Processed 8,432 rows in 0.12s (GPU) vs 0.45s (CPU estimate)
================================================================================
```

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `ai_analysis/__init__.py` | Create | Package init |
| `ai_analysis/data_loader.py` | Create | Sheets → cuDF |
| `ai_analysis/filter_predictor.py` | Create | cuML predictions |
| `ai_analysis/anomaly_detector.py` | Create | Spike detection |
| `ai_analysis/health_analyzer.py` | Create | Health metrics |
| `ai_analysis/llm_explainer.py` | Create | Ollama integration |
| `ai_analysis/analyzer.py` | Create | Orchestrator |
| `ai_analyze.py` | Create | CLI entry point |
| `pyproject.toml` | Modify | Add ollama dep |
| `reports/.gitkeep` | Create | Reports directory |

## Questions Resolved

- ✅ Data volume: <10K rows (good for learning, fast iterations)
- ✅ Analysis goals: Filter predictions, anomaly detection, health impact
- ✅ LLM usage: OSS 120B (fallback: Mistral) for full assistant
- ✅ GPU learning: Use cuDF/RAPIDS even for small data to learn APIs
- ✅ Filter tracking: Google Sheets tab `Filter_Changes`
- ✅ Alerts: Email-based, immediate, with ERV state detection
- ✅ iOS app: Deferred - start with email alerts

## Implementation Order

### Step 1: Google Sheets Setup
- Create `Filter_Changes` tab with schema above
- Test reading from both data tab and filter tab

### Step 2: Dependencies & Structure
- Add cudf-cu12, cuml-cu12, ollama to pyproject.toml via uv
- Create ai_analysis/ module structure

### Step 3: Data Loader (cuDF learning)
- Fetch from Google Sheets
- Convert to cuDF DataFrame
- Learn cuDF basics: dtypes, column ops, filtering

### Step 4: ERV State Detector
- Analyze CO2 trends (rising = ERV off, stable/dropping = ERV on)
- Correlate with outdoor conditions

### Step 5: Anomaly Detection
- Spike detection with cuDF rolling stats
- Classify: activity vs outdoor vs equipment issue

### Step 6: Filter Predictor
- cuML linear regression for degradation trends
- Use filter change dates from Sheets tab

### Step 7: Health Analyzer
- WHO guideline compliance
- Hourly/daily patterns

### Step 8: LLM Integration
- Ollama with OSS 120B
- Generate actionable recommendations

### Step 9: Alert System
- Enhanced Apps Script OR Python email sender
- Wife-friendly messages with clear actions

### Step 10: CLI & Integration
- ai_analyze.py entry point
- Interactive mode for Q&A
