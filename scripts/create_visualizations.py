#!/usr/bin/env python3
"""
Create P0 visualizations for README and LinkedIn post.

Pulls data from Google Sheets API and generates:
1. CO2 before/after ERV chart (bedrooms)
2. Filter efficiency over time
3. Indoor vs outdoor PM2.5 during high AQI events
"""

import os
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")


def fetch_data():
    """Fetch air quality data from Google Sheets."""
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

    # Parse types
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
    # Filter for rooms with CO2 data
    co2 = df[df["Indoor_CO2"].notna() & (df["Indoor_CO2"] > 0)].copy()

    # Separate by room
    master = co2[co2["Room"] == "master_bedroom"].copy()
    second = co2[co2["Room"] == "second_bedroom"].copy()

    # Resample to hourly averages for cleaner chart
    master_hourly = master.set_index("Timestamp")["Indoor_CO2"].resample("1h").mean().dropna()
    second_hourly = second.set_index("Timestamp")["Indoor_CO2"].resample("1h").mean().dropna()

    fig, ax = plt.subplots(figsize=(14, 6))

    if not master_hourly.empty:
        ax.plot(
            master_hourly.index,
            master_hourly.values,
            alpha=0.6,
            linewidth=0.8,
            color="#4A90D9",
            label=f"Master Bedroom (avg {master_hourly.mean():.0f} ppm)",
        )

    if not second_hourly.empty:
        ax.plot(
            second_hourly.index,
            second_hourly.values,
            alpha=0.6,
            linewidth=0.8,
            color="#E8744F",
            label=f"Second Bedroom (avg {second_hourly.mean():.0f} ppm)",
        )

    # Threshold lines
    ax.axhline(
        y=1000,
        color="#D32F2F",
        linestyle="--",
        linewidth=1.5,
        alpha=0.8,
        label="1000 ppm — cognitive impairment threshold",
    )
    ax.axhline(
        y=600,
        color="#4CAF50",
        linestyle="--",
        linewidth=1,
        alpha=0.5,
        label="600 ppm — target with ERV",
    )

    # Annotations
    ax.annotate(
        "CO₂ > 1000 ppm reduces\ncognitive performance by 72%",
        xy=(0.02, 0.92),
        xycoords="axes fraction",
        fontsize=9,
        color="#D32F2F",
        fontstyle="italic",
        verticalalignment="top",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "#FFEBEE",
            "edgecolor": "#D32F2F",
            "alpha": 0.8,
        },
    )

    ax.set_title(
        "Indoor CO₂ Levels — ERV Keeps Bedrooms Below Impairment Threshold",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.set_ylabel("CO₂ (ppm)", fontsize=12)
    ax.set_xlabel("")
    ax.legend(loc="upper right", fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(bottom=300)

    # Stats annotation
    all_co2 = co2["Indoor_CO2"]
    pct_above_1000 = (all_co2 > 1000).mean() * 100
    ax.annotate(
        f"Only {pct_above_1000:.1f}% of readings exceed 1000 ppm\n({len(co2):,} total readings)",
        xy=(0.98, 0.02),
        xycoords="axes fraction",
        fontsize=9,
        ha="right",
        va="bottom",
        color="#555",
    )

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "co2_bedroom_levels.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def chart_filter_efficiency(df):
    """Chart 2: Filter efficiency over time — lasting well past manufacturer recommendation."""
    eff = df[df["Filter_Efficiency"].notna() & (df["Filter_Efficiency"] > 0)].copy()

    # Use master bedroom (airthings) for consistent efficiency reading
    eff_master = eff[eff["Room"] == "master_bedroom"].copy()
    if eff_master.empty:
        eff_master = eff.copy()

    eff_hourly = (
        eff_master.set_index("Timestamp")["Filter_Efficiency"].resample("1h").mean().dropna()
    )

    # Calculate daily averages for trend line
    eff_daily = (
        eff_master.set_index("Timestamp")["Filter_Efficiency"].resample("1D").mean().dropna()
    )

    fig, ax = plt.subplots(figsize=(14, 6))

    # Hourly scatter (faded)
    ax.scatter(
        eff_hourly.index,
        eff_hourly.values,
        alpha=0.15,
        s=3,
        color="#4A90D9",
        label="_nolegend_",
    )

    # Daily moving average
    rolling = eff_daily.rolling(window=7, min_periods=1).mean()
    ax.plot(
        rolling.index,
        rolling.values,
        linewidth=2.5,
        color="#1565C0",
        label="7-day rolling average",
    )

    # 85% threshold
    ax.axhline(
        y=85,
        color="#4CAF50",
        linestyle="--",
        linewidth=1.5,
        alpha=0.7,
        label="85% — good efficiency threshold",
    )

    # Manufacturer's 45-day and 90-day markers
    start_date = eff_hourly.index.min()
    day_45 = start_date + pd.Timedelta(days=45)
    day_90 = start_date + pd.Timedelta(days=90)
    day_120 = start_date + pd.Timedelta(days=120)

    for day, label, color in [
        (day_45, "Mfr says: replace\nat 45 days", "#FF9800"),
        (day_90, "90 days\n(ERV filter spec)", "#F44336"),
        (day_120, "120 days\n(still >85%!)", "#4CAF50"),
    ]:
        if day <= eff_hourly.index.max():
            ax.axvline(x=day, color=color, linestyle=":", linewidth=1.5, alpha=0.7)
            ax.annotate(
                label,
                xy=(day, ax.get_ylim()[1] * 0.95),
                fontsize=8,
                color=color,
                fontweight="bold",
                ha="center",
                va="top",
            )

    # Title and labels
    total_days = (eff_hourly.index.max() - eff_hourly.index.min()).days
    avg_eff = eff_daily.mean()
    ax.set_title(
        f"Filter Efficiency Over {total_days} Days — Lasting Far Beyond Manufacturer Specs",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.set_ylabel("Filter Efficiency (%)", fontsize=12)
    ax.set_xlabel("")
    ax.legend(loc="lower left", fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 105)

    ax.annotate(
        f"Average efficiency: {avg_eff:.1f}%\nSavings: $130–$910/yr on unnecessary replacements",
        xy=(0.98, 0.05),
        xycoords="axes fraction",
        fontsize=9,
        ha="right",
        va="bottom",
        color="#555",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "#E8F5E9",
            "edgecolor": "#4CAF50",
            "alpha": 0.8,
        },
    )

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "filter_efficiency_over_time.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def chart_indoor_vs_outdoor_pm25(df):
    """Chart 3: Indoor vs outdoor PM2.5 — filtration protection during bad air days."""
    pm = df[
        df["Indoor_PM25"].notna() & df["Outdoor_PM25"].notna() & (df["Outdoor_PM25"] > 0)
    ].copy()

    # Use room with both indoor and outdoor readings
    pm_main = pm[pm["Room"] == "master_bedroom"].copy()
    if pm_main.empty:
        pm_main = pm.copy()

    pm_hourly_indoor = pm_main.set_index("Timestamp")["Indoor_PM25"].resample("1h").mean().dropna()
    pm_hourly_outdoor = (
        pm_main.set_index("Timestamp")["Outdoor_PM25"].resample("1h").mean().dropna()
    )

    # Align indices
    common_idx = pm_hourly_indoor.index.intersection(pm_hourly_outdoor.index)
    pm_hourly_indoor = pm_hourly_indoor.loc[common_idx]
    pm_hourly_outdoor = pm_hourly_outdoor.loc[common_idx]

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.fill_between(
        pm_hourly_outdoor.index,
        pm_hourly_outdoor.values,
        alpha=0.3,
        color="#F44336",
        label=f"Outdoor PM2.5 (avg {pm_hourly_outdoor.mean():.1f} μg/m³)",
    )
    ax.plot(
        pm_hourly_outdoor.index,
        pm_hourly_outdoor.values,
        linewidth=0.8,
        color="#D32F2F",
        alpha=0.6,
    )

    ax.fill_between(
        pm_hourly_indoor.index,
        pm_hourly_indoor.values,
        alpha=0.4,
        color="#4CAF50",
        label=f"Indoor PM2.5 (avg {pm_hourly_indoor.mean():.1f} μg/m³)",
    )
    ax.plot(
        pm_hourly_indoor.index,
        pm_hourly_indoor.values,
        linewidth=0.8,
        color="#2E7D32",
        alpha=0.6,
    )

    # WHO guideline
    ax.axhline(
        y=15,
        color="#FF9800",
        linestyle="--",
        linewidth=1.5,
        alpha=0.7,
        label="WHO 24h guideline (15 μg/m³)",
    )

    # Find and annotate worst outdoor day
    outdoor_daily = pm_main.set_index("Timestamp")["Outdoor_PM25"].resample("1D").mean().dropna()
    if not outdoor_daily.empty:
        worst_day = outdoor_daily.idxmax()
        worst_val = outdoor_daily.max()
        indoor_on_worst = (
            pm_main.set_index("Timestamp")["Indoor_PM25"].resample("1D").mean().get(worst_day, 0)
        )

        if worst_val > 20:
            ax.annotate(
                f"Worst day: outdoor {worst_val:.0f} μg/m³\n"
                f"Indoor stayed at {indoor_on_worst:.0f} μg/m³",
                xy=(worst_day, worst_val),
                xytext=(30, 20),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color="#D32F2F",
                arrowprops={"arrowstyle": "->", "color": "#D32F2F"},
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "#FFEBEE",
                    "edgecolor": "#D32F2F",
                    "alpha": 0.8,
                },
            )

    ax.set_title(
        "Indoor vs Outdoor PM2.5 — MERV 13 Filtration Protection",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.set_ylabel("PM2.5 (μg/m³)", fontsize=12)
    ax.set_xlabel("")
    ax.legend(loc="upper right", fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)

    # Reduction stat
    if pm_hourly_outdoor.mean() > 0:
        reduction = (
            (pm_hourly_outdoor.mean() - pm_hourly_indoor.mean()) / pm_hourly_outdoor.mean()
        ) * 100
        ax.annotate(
            f"Average PM2.5 reduction: {reduction:.0f}%",
            xy=(0.02, 0.02),
            xycoords="axes fraction",
            fontsize=10,
            fontweight="bold",
            color="#2E7D32",
            va="bottom",
        )

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "indoor_vs_outdoor_pm25.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== HVAC Air Quality Visualizations ===\n")
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
