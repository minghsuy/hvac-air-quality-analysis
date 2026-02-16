#!/usr/bin/env python3
"""
Create interactive Plotly HTML visualizations for GitHub Pages.

Pulls data from Parquet cache (or Google Sheets API fallback) and generates:
1. CO2 before/after ERV chart (bedrooms)
2. Filter efficiency over time
3. Indoor vs outdoor PM2.5 during high AQI events

Output: docs/charts/*.html (lightweight — Plotly.js loaded from CDN)
"""

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "docs", "charts")
CACHE_PATH = os.path.join(BASE_DIR, ".cache", "air_quality.parquet")

LIGHT_LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "Inter, system-ui, sans-serif"},
    "margin": {"l": 60, "r": 30, "t": 60, "b": 40},
    "hovermode": "x unified",
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
}

COLORS = {
    "master": "#4A90D9",
    "second": "#E8744F",
    "outdoor": "#F44336",
    "indoor": "#4CAF50",
    "threshold": "#D32F2F",
    "good": "#4CAF50",
    "warn": "#FF9800",
    "rolling": "#1565C0",
}


def fetch_data():
    """Fetch air quality data from Parquet cache or Google Sheets."""
    if os.path.exists(CACHE_PATH):
        print(f"Reading from Parquet cache: {CACHE_PATH}")
        df = pd.read_parquet(CACHE_PATH)
        df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp")
        print(f"Loaded {len(df):,} rows from cache")
        return df

    print("No Parquet cache found, fetching from Google Sheets...")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    sheet_tab = os.getenv("GOOGLE_SHEET_TAB", "")

    credentials = service_account.Credentials.from_service_account_file(
        "google-credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    range_name = f"{sheet_tab}!A:R" if sheet_tab else "A:R"
    print(f"Fetching data from '{range_name}'... (this may take a moment)")

    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

    values = result.get("values", [])
    if not values:
        print("No data found!")
        sys.exit(1)

    headers = values[0]
    df = pd.DataFrame(values[1:], columns=headers)
    print(f"Fetched {len(df):,} rows")

    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    for col in [
        "Indoor_PM25",
        "Outdoor_PM25",
        "Filter_Efficiency",
        "Indoor_CO2",
        "Outdoor_CO2",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    return df


def chart_co2_bedroom(df):
    """Chart 1: CO2 levels by bedroom showing ERV impact."""
    co2 = df[df["Indoor_CO2"].notna() & (df["Indoor_CO2"] > 0)].copy()

    master = co2[co2["Room"] == "master_bedroom"].copy()
    second = co2[co2["Room"] == "second_bedroom"].copy()

    master_daily = (
        master.set_index("Timestamp")["Indoor_CO2"]
        .resample("1D")
        .agg(["mean", "min", "max"])
        .dropna()
    )
    second_daily = (
        second.set_index("Timestamp")["Indoor_CO2"]
        .resample("1D")
        .agg(["mean", "min", "max"])
        .dropna()
    )

    fig = go.Figure()

    for daily, color, name in [
        (master_daily, COLORS["master"], "Master"),
        (second_daily, COLORS["second"], "Second Bedroom"),
    ]:
        if daily.empty:
            continue
        r_mean = daily["mean"].rolling(3, min_periods=1).mean()
        r_min = daily["min"].rolling(3, min_periods=1).min()
        r_max = daily["max"].rolling(3, min_periods=1).max()

        hex_c = color
        rgba = f"rgba({int(hex_c[1:3], 16)},{int(hex_c[3:5], 16)},{int(hex_c[5:7], 16)},0.12)"

        # Band (max/min)
        fig.add_trace(
            go.Scatter(
                x=r_max.index,
                y=r_max.values,
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=r_min.index,
                y=r_min.values,
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=rgba,
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Rolling mean
        fig.add_trace(
            go.Scatter(
                x=r_mean.index,
                y=r_mean.values,
                mode="lines",
                name=f"{name} (avg {daily['mean'].mean():.0f} ppm)",
                line={"color": color, "width": 2.5},
                hovertemplate=f"%{{y:.0f}} ppm<extra>{name}</extra>",
            )
        )

    fig.add_hline(
        y=1000,
        line_dash="dash",
        line_color=COLORS["threshold"],
        annotation_text="1000 ppm — cognitive impairment threshold",
        annotation_position="top left",
    )
    fig.add_hline(
        y=600,
        line_dash="dot",
        line_color=COLORS["good"],
        annotation_text="600 ppm — target with ERV",
        annotation_position="bottom left",
        opacity=0.5,
    )

    pct_above_1000 = (co2["Indoor_CO2"] > 1000).mean() * 100
    fig.add_annotation(
        text=(
            f"Only {pct_above_1000:.1f}% of readings exceed 1000 ppm"
            f"<br>({len(co2):,} total readings)"
        ),
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.02,
        showarrow=False,
        font={"size": 11, "color": "#555"},
        align="right",
        xanchor="right",
        yanchor="bottom",
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        title={
            "text": "Indoor CO\u2082 Levels — ERV Keeps Bedrooms Below Impairment Threshold",
            "font": {"size": 16},
        },
        yaxis_title="CO\u2082 (ppm)",
        yaxis={"range": [300, 1200]},
        height=500,
    )

    path = os.path.join(OUTPUT_DIR, "co2_bedroom_levels.html")
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"Saved: {path}")


def chart_filter_efficiency(df):
    """Chart 2: Filter efficiency over time — lasting well past manufacturer recommendation."""
    eff = df[df["Filter_Efficiency"].notna() & (df["Filter_Efficiency"] > 0)].copy()

    eff_master = eff[eff["Room"] == "master_bedroom"].copy()
    if eff_master.empty:
        eff_master = eff.copy()

    eff_daily = (
        eff_master.set_index("Timestamp")["Filter_Efficiency"]
        .resample("1D")
        .agg(["mean", "min", "max"])
        .dropna()
    )

    # 6-hourly scatter points (faded)
    eff_6h = eff_master.set_index("Timestamp")["Filter_Efficiency"].resample("6h").mean().dropna()

    rolling = eff_daily["mean"].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()

    # Scatter points
    if not eff_6h.empty:
        fig.add_trace(
            go.Scatter(
                x=eff_6h.index,
                y=eff_6h.values,
                mode="markers",
                name="6h readings",
                marker={"color": COLORS["master"], "size": 3, "opacity": 0.2},
            )
        )

    # 7-day rolling average
    fig.add_trace(
        go.Scatter(
            x=rolling.index,
            y=rolling.values,
            mode="lines",
            name="7-day rolling average",
            line={"color": COLORS["rolling"], "width": 3},
            hovertemplate="%{y:.1f}%<extra>7d avg</extra>",
        )
    )

    # 85% threshold
    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color=COLORS["good"],
        annotation_text="85% — good efficiency threshold",
        annotation_position="bottom right",
    )

    # Milestone markers
    start_date = eff_daily.index.min()
    end_date = eff_daily.index.max()
    for days, label, color in [
        (45, "Mfr: 45d", COLORS["warn"]),
        (90, "ERV spec: 90d", COLORS["threshold"]),
        (120, "120d — >85%!", COLORS["good"]),
    ]:
        md = start_date + pd.Timedelta(days=days)
        if md <= end_date:
            fig.add_vline(
                x=int(md.timestamp() * 1000),
                line_dash="dot",
                line_color=color,
                opacity=0.7,
            )
            fig.add_annotation(
                x=md,
                y=1.0,
                yref="paper",
                text=label,
                showarrow=False,
                font={"size": 10, "color": color},
                yanchor="top",
            )

    total_days = (end_date - start_date).days
    avg_eff = eff_daily["mean"].mean()
    fig.add_annotation(
        text=(
            f"Average efficiency: {avg_eff:.1f}%"
            f"<br>Savings: $130\u2013$910/yr on unnecessary replacements"
        ),
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.05,
        showarrow=False,
        font={"size": 11, "color": "#555"},
        align="right",
        xanchor="right",
        yanchor="bottom",
        bgcolor="rgba(232,245,233,0.8)",
        bordercolor=COLORS["good"],
        borderwidth=1,
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        title={
            "text": f"Filter Efficiency Over {total_days} Days — Lasting Far Beyond Manufacturer Specs",
            "font": {"size": 16},
        },
        yaxis_title="Filter Efficiency (%)",
        yaxis={"range": [0, 105]},
        height=500,
    )

    path = os.path.join(OUTPUT_DIR, "filter_efficiency.html")
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"Saved: {path}")


def chart_indoor_vs_outdoor_pm25(df):
    """Chart 3: Indoor vs outdoor PM2.5 — filtration protection during bad air days."""
    pm = df[
        df["Indoor_PM25"].notna() & df["Outdoor_PM25"].notna() & (df["Outdoor_PM25"] > 0)
    ].copy()

    pm_main = pm[pm["Room"] == "master_bedroom"].copy()
    if pm_main.empty:
        pm_main = pm.copy()

    # Daily rolling averages (3-day)
    in_daily = pm_main.set_index("Timestamp")["Indoor_PM25"].resample("1D").mean().dropna()
    out_daily = pm_main.set_index("Timestamp")["Outdoor_PM25"].resample("1D").mean().dropna()

    common_idx = in_daily.index.intersection(out_daily.index)
    in_daily = in_daily.loc[common_idx]
    out_daily = out_daily.loc[common_idx]

    in_roll = in_daily.rolling(3, min_periods=1).mean()
    out_roll = out_daily.rolling(3, min_periods=1).mean()

    fig = go.Figure()

    # Outdoor — filled area
    fig.add_trace(
        go.Scatter(
            x=out_roll.index,
            y=out_roll.values,
            mode="lines",
            name=f"Outdoor (avg {out_daily.mean():.1f} \u03bcg/m\u00b3)",
            line={"color": COLORS["outdoor"], "width": 2.5},
            fill="tozeroy",
            fillcolor="rgba(244,67,54,0.12)",
            hovertemplate="%{y:.1f} \u03bcg/m\u00b3<extra>Outdoor</extra>",
        )
    )

    # Indoor — filled area
    fig.add_trace(
        go.Scatter(
            x=in_roll.index,
            y=in_roll.values,
            mode="lines",
            name=f"Indoor (avg {in_daily.mean():.1f} \u03bcg/m\u00b3)",
            line={"color": COLORS["indoor"], "width": 2.5},
            fill="tozeroy",
            fillcolor="rgba(76,175,80,0.15)",
            hovertemplate="%{y:.1f} \u03bcg/m\u00b3<extra>Indoor</extra>",
        )
    )

    # WHO guideline
    fig.add_hline(
        y=15,
        line_dash="dash",
        line_color=COLORS["warn"],
        annotation_text="WHO 24h guideline (15 \u03bcg/m\u00b3)",
        annotation_position="top right",
    )

    # Reduction stat
    if out_daily.mean() > 0:
        reduction = ((out_daily.mean() - in_daily.mean()) / out_daily.mean()) * 100
        fig.add_annotation(
            text=f"Average PM2.5 reduction: {reduction:.0f}%",
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            showarrow=False,
            font={"size": 12, "color": "#2E7D32", "weight": "bold"},
            xanchor="left",
            yanchor="top",
        )

    fig.update_layout(
        **LIGHT_LAYOUT,
        title={
            "text": "Indoor vs Outdoor PM2.5 — MERV 13 Filtration Protection",
            "font": {"size": 16},
        },
        yaxis_title="PM2.5 (\u03bcg/m\u00b3)",
        yaxis={"range": [0, max(40, out_roll.max() * 1.2)]},
        height=500,
    )

    path = os.path.join(OUTPUT_DIR, "indoor_vs_outdoor_pm25.html")
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"Saved: {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== HVAC Air Quality Visualizations (Plotly HTML) ===\n")
    df = fetch_data()

    print(f"\nDate range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print(f"Rooms: {df['Room'].unique().tolist()}")
    print(f"Sensors: {df['Sensor_Type'].unique().tolist()}")
    print()

    chart_co2_bedroom(df)
    chart_filter_efficiency(df)
    chart_indoor_vs_outdoor_pm25(df)

    print(f"\nAll charts saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
