# Dashboard Architecture

[Back to index](index.md)

## Why Streamlit Over React

This is a data analysis tool, not a consumer app. The dashboard runs on a home server for a single user inspecting sensor data.

Streamlit delivers the same functionality in 938 lines of Python that would require 3-5x the code in React + API + state management:

| Concern | Streamlit | React Equivalent |
|---------|-----------|------------------|
| Data loading | `pd.read_parquet()` | API endpoint + React Query |
| Caching | `@st.cache_data` | Redis/SWR + invalidation logic |
| UI state | `st.session_state` | Redux/Context + reducers |
| Charts | `st.plotly_chart(fig)` | Plotly.js + React wrapper |
| Multi-page | `st.navigation()` | React Router + layout |

**Tradeoff**: Streamlit is single-user and not embeddable. That's fine for a home server dashboard.

## Parquet Cache Benchmark

The Google Sheets API takes ~3.5 seconds to fetch 98k rows over the network. Local Parquet reads the same data in 18ms.

```
Method              Read      Compute   Total
─────────────────   ───────   ───────   ──────
Google Sheets API   3,500ms   5ms       3,505ms
Parquet (pandas)    18ms      5ms       23ms
Parquet (Polars)    16ms      3ms       19ms
```

**106x faster** with Parquet. The bottleneck is always network I/O — compute is negligible at 98k rows.

### Why Not Polars or cuDF?

We benchmarked Polars and cuDF (GPU-accelerated pandas) against standard pandas:

- **Polars**: 19ms total vs pandas 23ms. At 98k rows, the difference is imperceptible.
- **cuDF**: Requires CUDA setup, adds deployment complexity. Would matter at 10M+ rows.
- **pandas**: Already installed, battle-tested, 5ms compute time. No reason to change.

The benchmark script (`scripts/bench_heatmap.py`) proves this quantitatively.

## 3-Layer Caching Strategy

Each layer solves a different latency problem:

### Layer 1: Parquet on Disk (1-hour TTL)

```python
PARQUET_CACHE = ".cache/air_quality.parquet"

if cache_age < 3600:  # 1 hour
    df = pd.read_parquet(PARQUET_CACHE)  # 18ms
else:
    df = _fetch_from_sheets()  # 3.5s
    df.to_parquet(PARQUET_CACHE)
```

**Why**: Eliminates network latency on page reload. The 1-hour TTL balances freshness (data collected every 5 min) with performance (most analysis sessions are <1 hour).

### Layer 2: Session State (per-session)

```python
if "_cached_raw" not in st.session_state:
    raw = load_raw()
    st.session_state["_cached_raw"] = raw
```

**Why**: Streamlit reruns the entire script on every widget interaction. Without session state, even Parquet reads would happen on every click.

### Layer 3: Pre-aggregated Dictionaries

```python
@st.cache_data(ttl=600)
def precompute(df_raw):
    hourly = {}  # (room, metric) → Series
    daily = {}   # (room, metric) → DataFrame[mean, min, max]
    for room in rooms:
        for metric in metrics:
            hourly[(room, m)] = s.resample("1h").mean()
            daily[(room, m)] = s.resample("1D").agg(["mean", "min", "max"])
    return hourly, daily
```

**Why**: Pages use rolling averages and daily aggregates, not raw 5-minute readings. Computing these once avoids redundant resampling across 7 pages.

## Column Shift Fix

A real data engineering problem. Before September 2025, the collector wrote 17 columns. After adding Airthings radon and outdoor sensors, it writes 18 columns. The same Google Sheet contains both formats.

When a 17-column row is read against an 18-column header, every column after the missing one shifts left. Temperature appears in the humidity column, humidity in the radon column, etc.

**Solution**: Track the original column count per row and NaN affected columns:

```python
df["_orig_cols"] = [len(row) for row in raw_rows]

shifted = df["_orig_cols"] < 18
for col in ["Indoor_Temp", "Indoor_Humidity", "Indoor_Radon",
            "Outdoor_CO2", "Outdoor_Temp", "Outdoor_Humidity",
            "Outdoor_VOC", "Outdoor_NOX"]:
    df.loc[shifted, col] = np.nan
```

This preserves the columns that are correctly positioned (PM2.5, CO2, VOC, NOX) while NaN-ing the ones that would be misaligned.
