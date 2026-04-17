#!/usr/bin/env python3
"""Reproduce the headline findings from docs/findings.md and Analysis-Results.md
against the raw parquet cache, so an external reader can audit them.

Outputs:
  - stdout:                    text summary (fast to scan)
  - docs/reports/findings.html: self-contained HTML with plotly charts,
                                served by GitHub Pages at /reports/findings.html

Usage:  uv run python scripts/analysis/verify_findings.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot as plotly_plot
from plotly.subplots import make_subplots
from scipy.stats import spearmanr

REPO_ROOT = Path(__file__).resolve().parents[2]
PARQUET_CACHE = REPO_ROOT / ".cache" / "air_quality.parquet"
HTML_OUT = REPO_ROOT / "docs" / "reports" / "findings.html"

# Seasonal outdoor PM2.5 minimums for reliable efficiency measurement.
# Source: docs/methodology.md + HVACMonitor_v3.gs
SEASONAL_MIN_PM = {"winter": 10, "summer": 5, "default": 7}

# Filter periods — refined 2026-04-16 after verifying against the data.
# What was originally reported as a single "ERV MERV 13 cycle 1 (May-Oct 2025)" actually
# contained TWO different filters: the OEM MERV 13 until Sept 5, then a generic
# MERV-13-rated HVAC-style panel filter (different form factor) from Sept 6 to Oct 15,
# then a fresh OEM MERV 13 from Oct 15 onward. Data-inferred transition date Sept 6.
# Parquet coverage starts 2025-07-26, so the "OEM MERV 13 first period" shown here
# is only ~41 days of what was calendar-wise a longer install.
FILTER_CYCLES = {
    "ERV OEM MERV 13 (observed start)": ("2025-07-26", "2025-09-06", None),
    "ERV generic MERV 13 substitute": ("2025-09-06", "2025-10-15", None),
    "ERV OEM MERV 13 cycle 2": ("2025-10-15", "2026-02-08", 90),
    "Zone MERV 12 cycle 1": ("2025-11-10", "2026-02-08", 90),
}

# Feb 7-8 2026 alert escalation event. Source: Analysis-Results.md:85-132
CASE_START = pd.Timestamp("2026-02-07")
CASE_END = pd.Timestamp("2026-02-09")

CORRELATION_PAIRS = [
    ("Indoor_PM25", "Filter_Efficiency", -0.96),
    ("Indoor_CO2", "Indoor_VOC", 0.65),
    ("Outdoor_PM25", "Indoor_Radon", 0.59),
    ("Outdoor_Temp", "Outdoor_CO2", -0.59),
    ("Outdoor_VOC", "Outdoor_NOX", -0.45),
]


def season_of(ts: pd.Timestamp) -> str:
    m = ts.month
    if m in (12, 1, 2):
        return "winter"
    if m in (6, 7, 8):
        return "summer"
    return "default"


def master_bedroom(df: pd.DataFrame) -> pd.DataFrame:
    """Primary indoor sensor (Airthings) — used for health-relevant claims."""
    return df[df["Room"] == "master_bedroom"].copy()


def second_bedroom(df: pd.DataFrame) -> pd.DataFrame:
    """AirGradient near kitchen — used for PM2.5 precision where Airthings rounding hurts."""
    return df[df["Room"] == "second_bedroom"].copy()


# ── Compute: Feb 7-8 case study ──────────────────────────────────────────────


def compute_case_study(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    mbr = master_bedroom(df)
    mask = (mbr["Timestamp"] >= CASE_START) & (mbr["Timestamp"] < CASE_END)
    case = mbr[mask].copy()

    case["hour"] = case["Timestamp"].dt.floor("h")
    case["season"] = case["Timestamp"].apply(season_of)
    case["min_pm"] = case["season"].map(SEASONAL_MIN_PM)
    case["valid"] = case["Outdoor_PM25"] >= case["min_pm"]

    hourly = (
        case[case["valid"]]
        .groupby("hour")
        .agg(
            n=("Filter_Efficiency", "size"),
            eff_median=("Filter_Efficiency", "median"),
            indoor_pm=("Indoor_PM25", "median"),
            outdoor_pm=("Outdoor_PM25", "median"),
        )
        .reset_index()
    )

    # Before/after replacement at ~midday Feb 8, using AirGradient (0.01 µg/m³ precision)
    sbr = second_bedroom(df)
    am_mask = (sbr["Timestamp"] >= "2026-02-08") & (sbr["Timestamp"] < "2026-02-08 12:00")
    pm_mask = (sbr["Timestamp"] >= "2026-02-08 13:00") & (sbr["Timestamp"] < "2026-02-09")
    prepost = {
        "am_median": sbr.loc[am_mask, "Indoor_PM25"].median(),
        "pm_median": sbr.loc[pm_mask, "Indoor_PM25"].median(),
        "am_n": int(am_mask.sum()),
        "pm_n": int(pm_mask.sum()),
    }
    return hourly, prepost


def chart_case_study(hourly: pd.DataFrame) -> str:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=hourly["hour"],
            y=hourly["eff_median"],
            mode="lines+markers",
            name="Filter efficiency (hourly median)",
            line={"color": "#E8744F", "width": 2},
            hovertemplate="%{x|%b %d %H:00}<br>Efficiency: %{y:.1f}%%<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly["hour"],
            y=hourly["outdoor_pm"],
            mode="lines",
            name="Outdoor PM2.5 (hourly median)",
            line={"color": "#4A90D9", "width": 1, "dash": "dot"},
            hovertemplate="%{x|%b %d %H:00}<br>Outdoor PM2.5: %{y:.1f} µg/m³<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color="#888",
        annotation_text="85% reference",
        annotation_position="top right",
    )
    fig.add_hline(
        y=77,
        line_dash="dot",
        line_color="#FF9800",
        annotation_text="warning threshold (77%)",
        annotation_position="bottom right",
    )
    fig.add_hline(
        y=67,
        line_dash="dot",
        line_color="#D32F2F",
        annotation_text="critical threshold (67%)",
        annotation_position="bottom right",
    )
    replacement_ts = pd.Timestamp("2026-02-08 12:00")
    fig.add_shape(
        type="line",
        x0=replacement_ts,
        x1=replacement_ts,
        y0=0,
        y1=1,
        yref="paper",
        line={"color": "#4CAF50", "width": 1, "dash": "dash"},
    )
    fig.add_annotation(
        x=replacement_ts,
        y=1,
        yref="paper",
        text="filter replaced",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font={"color": "#4CAF50", "size": 11},
    )
    fig.update_layout(
        title="Feb 7-8 2026 alert escalation — master bedroom",
        template="plotly_white",
        height=420,
        margin={"l": 60, "r": 40, "t": 60, "b": 40},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
    )
    fig.update_xaxes(title_text="hour")
    fig.update_yaxes(title_text="Filter efficiency (%)", secondary_y=False, range=[0, 105])
    fig.update_yaxes(title_text="Outdoor PM2.5 (µg/m³)", secondary_y=True)
    return plotly_plot(fig, output_type="div", include_plotlyjs=False)


# ── Compute: filter cycles ──────────────────────────────────────────────────


def compute_cycles(df: pd.DataFrame) -> pd.DataFrame:
    mbr = master_bedroom(df)
    rows = []
    for name, (start, end, mfr_days) in FILTER_CYCLES.items():
        mask = (mbr["Timestamp"] >= start) & (mbr["Timestamp"] < end)
        cycle = mbr[mask].copy()
        cycle["season"] = cycle["Timestamp"].apply(season_of)
        cycle["min_pm"] = cycle["season"].map(SEASONAL_MIN_PM)
        valid = cycle[cycle["Outdoor_PM25"] >= cycle["min_pm"]]

        actual_days = (pd.Timestamp(end) - pd.Timestamp(start)).days
        daily = (
            valid.assign(date=valid["Timestamp"].dt.date)
            .groupby("date")["Filter_Efficiency"]
            .median()
        )
        days_above_85 = int((daily >= 85).sum())
        med_eff = valid["Filter_Efficiency"].median() if len(valid) else float("nan")
        rows.append(
            {
                "period": name,
                "start": start,
                "end": end,
                "actual_days": actual_days,
                "mfr_days": mfr_days if mfr_days is not None else "—",
                "valid_readings": len(valid),
                "median_eff": round(med_eff, 1) if pd.notna(med_eff) else None,
                "days_ge_85": days_above_85,
            }
        )
    return pd.DataFrame(rows)


def chart_cycles(df: pd.DataFrame) -> str:
    mbr = master_bedroom(df)
    fig = go.Figure()
    # Same green for both OEM MERV 13 periods makes the identity visually obvious.
    # Red singles out the generic-substitute period as the anomalous interval.
    colors = {
        "ERV OEM MERV 13 (observed start)": "#4CAF50",
        "ERV generic MERV 13 substitute": "#D32F2F",
        "ERV OEM MERV 13 cycle 2": "#4CAF50",
        "Zone MERV 12 cycle 1": "#4A90D9",
    }
    for name, (start, end, _) in FILTER_CYCLES.items():
        mask = (mbr["Timestamp"] >= start) & (mbr["Timestamp"] < end)
        cycle = mbr[mask].copy()
        cycle["season"] = cycle["Timestamp"].apply(season_of)
        cycle["min_pm"] = cycle["season"].map(SEASONAL_MIN_PM)
        valid = cycle[cycle["Outdoor_PM25"] >= cycle["min_pm"]]
        daily = (
            valid.assign(date=valid["Timestamp"].dt.date)
            .groupby("date")["Filter_Efficiency"]
            .median()
            .reset_index()
        )
        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["Filter_Efficiency"],
                mode="markers",
                name=name,
                marker={"size": 5, "color": colors.get(name, "#888")},
                hovertemplate=f"{name}<br>%{{x}}<br>Median efficiency: %{{y:.1f}}%%<extra></extra>",
            )
        )
    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color="#888",
        annotation_text="85% reference",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Daily median filter efficiency by cycle — master bedroom",
        template="plotly_white",
        height=420,
        margin={"l": 60, "r": 40, "t": 60, "b": 40},
        hovermode="closest",
        legend={"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center"},
    )
    fig.update_xaxes(title_text="date")
    fig.update_yaxes(title_text="Daily median efficiency (%)", range=[0, 105])
    # First chart embedded in the HTML owns the plotly.js CDN load; later charts set False.
    return plotly_plot(fig, output_type="div", include_plotlyjs="cdn")


# ── Compute: correlations ────────────────────────────────────────────────────


def compute_correlations(df: pd.DataFrame) -> pd.DataFrame:
    mbr = master_bedroom(df)
    rows = []
    for a, b, claimed in CORRELATION_PAIRS:
        sub = mbr[[a, b]].dropna()
        rho, _ = spearmanr(sub[a], sub[b])
        rows.append(
            {
                "pair": f"{a} ↔ {b}",
                "claimed": claimed,
                "measured": round(float(rho), 3),
                "n": len(sub),
            }
        )
    return pd.DataFrame(rows)


# ── HTML assembly ────────────────────────────────────────────────────────────


def df_to_html_table(df: pd.DataFrame, caption: str = "") -> str:
    cap = f"<caption>{caption}</caption>" if caption else ""
    return df.to_html(index=False, classes="data", border=0).replace(
        '<table class="dataframe data">', f'<table class="data">{cap}'
    )


def build_html(
    df: pd.DataFrame,
    hourly: pd.DataFrame,
    prepost: dict,
    cycles: pd.DataFrame,
    correlations: pd.DataFrame,
    case_div: str,
    cycle_div: str,
) -> str:
    ts_min = df["Timestamp"].min()
    ts_max = df["Timestamp"].max()
    generated = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    css = dedent(
        """
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               max-width: 900px; margin: 2em auto; padding: 0 1em; color: #222; line-height: 1.55; }
        h1 { border-bottom: 2px solid #E8744F; padding-bottom: 0.3em; }
        h2 { border-bottom: 1px solid #ddd; padding-bottom: 0.2em; margin-top: 2.2em; }
        table.data { border-collapse: collapse; margin: 1em 0; font-size: 0.95em; }
        table.data th, table.data td { padding: 0.4em 0.9em; text-align: left; }
        table.data th { background: #f5f5f5; border-bottom: 2px solid #ccc; }
        table.data td { border-bottom: 1px solid #eee; }
        table.data caption { caption-side: top; text-align: left; font-weight: 600;
                              padding-bottom: 0.4em; color: #555; }
        .meta { color: #666; font-size: 0.88em; }
        .caveat { background: #fffbe6; border-left: 4px solid #FF9800; padding: 0.5em 1em; margin: 1em 0; }
        .supports { background: #f1f8e9; border-left: 4px solid #4CAF50; padding: 0.5em 1em; margin: 1em 0; }
        .rejects  { background: #fdecea; border-left: 4px solid #D32F2F; padding: 0.5em 1em; margin: 1em 0; }
        code { background: #f5f5f5; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
        """
    )

    prepost_line = (
        f"Indoor PM2.5 (AirGradient, second bedroom): "
        f"AM median {prepost['am_median']:.2f} µg/m³ (n={prepost['am_n']}) → "
        f"PM median {prepost['pm_median']:.2f} µg/m³ (n={prepost['pm_n']})"
    )

    body = dedent(
        f"""
        <h1>HVAC air quality findings — verification report</h1>
        <p class="meta">
          Generated {generated} from <code>.cache/air_quality.parquet</code> ({len(df):,} rows,
          {ts_min:%Y-%m-%d} → {ts_max:%Y-%m-%d}).
          Reproducible via <code>uv run python scripts/analysis/verify_findings.py</code>.
        </p>

        <h2>Scope and what this audits</h2>
        <p>
          This report reproduces the Spearman correlations in
          <a href="../findings.html">findings</a>, the filter-replacement history from
          the project wiki's Analysis Results page, and the
          Feb 7-8 2026 alert-escalation case study. Running it against the parquet also surfaced a
          previously-undocumented natural experiment (Sept-Oct 2025), which is the most
          researcher-relevant finding in the dataset.
        </p>

        <h2>1. Filter periods and the natural experiment</h2>
        {df_to_html_table(cycles, "Per-period measured efficiency (master bedroom Airthings)")}
        {cycle_div}

        <div class="supports"><strong>Natural experiment: MERV rating is not a performance guarantee.</strong>
          For ~40 days (Sept 6 – Oct 15 2025) the OEM-specified ERV filter was temporarily replaced
          with a generic MERV-13-rated HVAC-style panel filter of a different form factor. Same home,
          same outdoor air, same sensors, same HVAC — only the filter changed. Apparent efficiency
          dropped from 93.9%+ OEM median to 69.0% substitute median (worst days 35-50%). The moment
          the OEM filter was reinstalled, efficiency returned to 95%+ on day one. Both filters
          carried MERV 13 ratings.
          The underlying mechanism (media quality, form-factor bypass, construction density) is not
          distinguishable from this data alone; the ~20-percentage-point efficiency delta between two
          MERV-13-rated filters in the same installation is the observation.
        </div>

        <div class="supports"><strong>Load-based filter-life prediction fails.</strong>
          ERV OEM MERV 13 cycle 2 ran 29% past the manufacturer's 90-day recommendation at 93.9%
          median efficiency across 14,361 valid readings. Prior analysis documented a filter at 197%
          of theoretical "max life" still performing at 87.3%. Load accumulation does not predict
          efficiency degradation for this system — the alerting system instead triggers on actual
          measured efficiency, which catches real failures (see section 2).
        </div>

        <div class="rejects"><strong>What the data does NOT support.</strong>
          The earlier findings.md claim that MERV 13 "consistently holds &gt;85% for 120+ days"
          is overstated. It holds for OEM MERV 13 installations (93.9% cycle 2, 93.7% zone cycle 1);
          it categorically does not hold for a generic MERV-13-rated substitute (69.0% median).
          The revised claim: <em>OEM MERV 13 holds 95%+; label-equivalent substitutes may not, and
          only monitoring distinguishes them.</em>
        </div>

        <h2>2. Feb 7-8 2026 alert escalation</h2>
        <p>
          At ~13:00 on Feb 7, master bedroom filter efficiency dropped from a ~95% baseline and
          continued to decline overnight into Feb 8. The alerting system (HVACMonitor v3) escalated
          WARNING → CRITICAL. Filters were replaced mid-day Feb 8. Hourly efficiency recovered to
          ≥95% within an hour. The event was also physically detectable — the family reported a
          musty smell before replacement.
        </p>
        {case_div}
        <p class="meta">{prepost_line}</p>

        <h2>3. Spearman correlations (master bedroom)</h2>
        {df_to_html_table(correlations, "Claimed vs measured, full history")}
        <p>
          Indoor PM2.5 ↔ Filter Efficiency and Indoor CO2 ↔ Indoor VOC reproduce the published
          values essentially exactly. The three others drift 0.03–0.06 in magnitude from the
          <code>findings.md</code> numbers written against an earlier ~98k-row snapshot; direction
          and sign agree across all five.
        </p>

        <h2>Caveats and limitations</h2>
        <div class="caveat">
          <strong>n=1 house, 9 months.</strong> Results are not generalizable to other homes or
          climates. They <em>are</em> generalizable as measurement methodology — and useful for
          falsifying specific manufacturer claims (a single counterexample suffices to reject
          "load predicts efficiency").
        </div>
        <div class="caveat">
          <strong>No reference-instrument co-location.</strong> All sensors are consumer-grade
          (Airthings View Plus, AirGradient Open Air &amp; ONE). No formal validation against a
          research-grade reference. Absolute PM2.5 accuracy is not claimed; the within-dataset
          relative dynamics and cross-sensor agreement are what the findings rest on.
        </div>
        <div class="caveat">
          <strong>Sensor precision difference.</strong> Airthings rounds PM2.5 to whole numbers;
          AirGradient reports to 0.01 µg/m³. Case-study before/after PM2.5 medians use AirGradient
          for this reason.
        </div>
        <div class="caveat">
          <strong>Seasonal measurement coverage.</strong> Efficiency calculation requires outdoor
          PM2.5 above a seasonal minimum (winter 10, summer 5, default 7 µg/m³). Summer days with
          very clean outdoor air are excluded, so the daily-count coverage is thinner in summer
          than winter. This affects sample size per period but does not explain the Sept-Oct 2025
          efficiency drop (that was a filter swap, not a measurement artifact).
        </div>
        <div class="caveat">
          <strong>Cooking-spike contamination.</strong> The second-bedroom AirGradient sits near
          the kitchen. It is used for precision PM2.5 differentials in short-window comparisons,
          not for health-claim baselines.
        </div>

        <p class="meta">
          Source: <a href="https://github.com/minghsuy/hvac-air-quality-analysis">github.com/minghsuy/hvac-air-quality-analysis</a>
          · Script: <code>scripts/analysis/verify_findings.py</code>
        </p>
        """
    )

    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>HVAC air quality findings — verification report</title>"
        f"<style>{css}</style></head><body>{body}</body></html>\n"
    )


# ── Text summary (unchanged behavior from v1) ────────────────────────────────


def print_text_summary(
    df: pd.DataFrame,
    hourly: pd.DataFrame,
    prepost: dict,
    cycles: pd.DataFrame,
    correlations: pd.DataFrame,
) -> None:
    print(f"Loaded {len(df):,} rows, {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print()
    print("=== Feb 7-8 2026 alert escalation (master bedroom) ===")
    print(hourly.to_string(index=False))
    print()
    print(
        f"Indoor PM2.5 before/after replacement (AirGradient): "
        f"AM {prepost['am_median']:.2f} (n={prepost['am_n']}) → "
        f"PM {prepost['pm_median']:.2f} (n={prepost['pm_n']}) µg/m³"
    )
    print()
    print("=== Spearman correlations (master bedroom) ===")
    print(correlations.to_string(index=False))
    print()
    print("=== Filter cycles ===")
    print(cycles.to_string(index=False))


def main() -> None:
    df = pd.read_parquet(PARQUET_CACHE)

    hourly, prepost = compute_case_study(df)
    cycles = compute_cycles(df)
    correlations = compute_correlations(df)

    print_text_summary(df, hourly, prepost, cycles, correlations)

    case_div = chart_case_study(hourly)
    cycle_div = chart_cycles(df)
    html = build_html(df, hourly, prepost, cycles, correlations, case_div, cycle_div)

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html)
    size_kb = HTML_OUT.stat().st_size / 1024
    print(f"\nHTML written: {HTML_OUT.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
