# Methodology

[Back to index](index.md)

## Why Spearman Over Pearson

Pearson correlation assumes three things about the data: **normality** (variables follow a normal distribution), **linearity** (relationships are straight lines), and **homoscedasticity** (constant variance). Environmental sensor data violates all three.

### Where Pearson's Assumptions Break Down

1. **Non-normal distributions**: PM2.5 jumps from 3 to 80 ug/m3 during cooking events, creating heavy right tails. NOX index has a mean of ~1.06 with minimal variance, concentrating nearly all values near zero. Neither is normally distributed.
2. **Non-linear relationships**: Outdoor VOC and NOX have an inverse seasonal pattern — the relationship is monotonic but not linear. Pearson reports near-zero; Spearman correctly identifies the trend (rho = -0.45).
3. **Heteroscedastic variance**: Sensor noise increases with magnitude — a PM2.5 reading of 50 ug/m3 has more absolute error than a reading of 5 ug/m3. This violates Pearson's constant-variance assumption.

Spearman rank correlation operates on ranks, not raw values, making it robust to all three violations. It captures monotonic relationships regardless of distribution shape or outliers.

### Illustration: PM2.5 vs Filter Efficiency

| Method | Correlation | Why |
|--------|-------------|-----|
| Spearman | rho = -0.96 | Ranks are unaffected by cooking spike magnitudes |
| Pearson | r = -0.72 | Cooking spikes and outliers pull the linear fit away from the true relationship |

The difference isn't that Spearman gives "bigger numbers" — it's that Pearson underestimates the strength of relationships when its assumptions are violated. For data that meets Pearson's assumptions, both methods converge.

The dashboard defaults to Spearman with a toggle to Pearson for comparison.

## LOWESS Anomaly Detection

LOcally WEighted Scatterplot Smoothing (LOWESS) fits a local regression at each point, creating an adaptive trend line that follows seasonal and daily patterns.

### Parameters

```python
from statsmodels.nonparametric.smoothers_lowess import lowess

smoothed = lowess(values, x_numeric, frac=0.08, return_sorted=False)
residuals = values - smoothed
anomalies = residuals > 1.5 * residuals.std()
```

- **frac=0.08**: Each point uses 8% of surrounding data for its local fit. Small enough to track weekly patterns, large enough to smooth noise.
- **6-hour resampling**: Raw data at 5-minute intervals is too noisy. 6-hour means preserve daily patterns while reducing data points from ~16k to ~700.
- **1.5x std threshold**: Points where the actual value exceeds the LOWESS trend by 1.5 standard deviations of the residuals. Identifies genuine spikes (ventilation changes, cooking events) while ignoring normal variance.

### Why Not Z-score or IQR?

- **Z-score**: Assumes global mean/variance. A CO2 spike during winter (when baseline is higher) looks normal against the global distribution.
- **IQR**: Better than Z-score but still uses a single baseline. LOWESS adapts to seasonal and weekly patterns.
- **LOWESS residuals**: The anomaly threshold is relative to the local trend, not the global distribution. A 900ppm reading is normal in winter but anomalous in summer.

## Pre-aggregation Strategy

Raw data: 98,000+ rows at 5-minute intervals. Pages need rolling averages and daily ranges, not individual readings.

### Aggregation Levels

```
Raw (5-min)  →  Hourly mean  →  Daily mean/min/max
  98,000         ~16,000          ~200 per metric
```

All aggregations are computed once on data load and stored in dictionaries keyed by `(room, metric)`:

```python
hourly[(room, metric)] = series.resample("1h").mean()
daily[(room, metric)] = series.resample("1D").agg(["mean", "min", "max"])
```

### Why This Structure?

- **Rolling averages**: Use daily means (e.g., 3-day or 7-day rolling) — 200 points instead of 98k.
- **Min/max bands**: Daily min and max create the "range band" visualizations showing variance.
- **Heatmaps**: Use raw data filtered to the selected date range, then pivot by hour x date.
- **Correlation matrix**: Uses raw data (Spearman rank doesn't benefit from aggregation).

## Filter Efficiency Formula

```
Efficiency = ((Outdoor_PM25 - Indoor_PM25) / Outdoor_PM25) * 100%
```

### When It Works

When outdoor PM2.5 provides a meaningful baseline (> 5 ug/m3). The MERV 13 filter reduces PM2.5 by capturing particles as air passes through the HVAC system.

### When It Fails

- **Outdoor PM2.5 < 5 ug/m3**: Division by a small number amplifies noise. A reading of outdoor=3, indoor=1 gives 67% efficiency, but the absolute difference is within sensor error.
- **Indoor sources active**: Cooking, cleaning, or candles generate PM2.5 that bypasses the filter entirely. Efficiency can go negative.
- **ERV running**: The energy recovery ventilator brings outdoor air directly into the house. Higher ERV flow means more outdoor particles bypass the filter.

The dashboard and alerting system use seasonal minimum outdoor PM2.5 thresholds to avoid false readings:

| Season | Min Outdoor PM2.5 |
|--------|-------------------|
| Winter (Dec-Feb) | 10 ug/m3 |
| Summer (Jun-Aug) | 5 ug/m3 |
| Spring/Fall | 7 ug/m3 |
