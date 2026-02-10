#!/usr/bin/env python3
"""
Analyze your historical Airthings CSV export
Run this locally on your computer
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# Configuration - Update these dates!
HVAC_INSTALL = "2025-02-25"
ERV_INSTALL = "2025-03-15"
FILTER_UPGRADE = "2025-06-01"  # MERV 8 to MERV 13


def load_airthings_csv(filepath):
    """Load and parse Airthings CSV export"""
    # Read CSV - Airthings exports typically have these columns
    df = pd.read_csv(filepath)

    # Convert timestamp to datetime
    if "recorded" in df.columns:
        df["timestamp"] = pd.to_datetime(df["recorded"])
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    else:
        print("Warning: No timestamp column found!")
        return None

    # Set timestamp as index
    df.set_index("timestamp", inplace=True)

    # Sort by time
    df.sort_index(inplace=True)

    print(f"Loaded {len(df)} records from {df.index.min()} to {df.index.max()}")
    print(f"Columns: {list(df.columns)}")

    return df


def analyze_air_quality(df):
    """Analyze key air quality metrics"""
    # Key metrics
    metrics = ["pm1", "pm25", "co2", "voc", "humidity", "temp"]
    available = [m for m in metrics if m in df.columns]

    print("\n=== Air Quality Summary ===")
    for metric in available:
        print(f"\n{metric.upper()}:")
        print(f"  Mean: {df[metric].mean():.1f}")
        print(f"  Std: {df[metric].std():.1f}")
        print(f"  Min: {df[metric].min():.1f}")
        print(f"  Max: {df[metric].max():.1f}")

        # Check against guidelines
        if metric == "pm25":
            who_limit = 15  # WHO 24-hour guideline
            days_above = (df[metric] > who_limit).sum()
            print(
                f"  Days above WHO limit ({who_limit} μg/m³): {days_above} ({days_above / len(df) * 100:.1f}%)"
            )
        elif metric == "co2":
            high_co2 = 1000  # Cognitive impact threshold
            hours_above = (df[metric] > high_co2).sum()
            print(
                f"  Hours above {high_co2} ppm: {hours_above} ({hours_above / len(df) * 100:.1f}%)"
            )


def plot_timeline(df, metric="pm25"):
    """Plot metric over time with event markers"""
    plt.figure(figsize=(14, 8))

    # Plot raw data
    plt.plot(df.index, df[metric], alpha=0.5, label="Hourly data")

    # Add rolling average
    rolling = df[metric].rolling("7D").mean()
    plt.plot(df.index, rolling, linewidth=2, label="7-day average")

    # Add event markers
    events = {
        "HVAC Install": HVAC_INSTALL,
        "ERV Install": ERV_INSTALL,
        "MERV 13 Upgrade": FILTER_UPGRADE,
    }

    for event, date in events.items():
        event_date = pd.to_datetime(date)
        if df.index.min() <= event_date <= df.index.max():
            plt.axvline(x=event_date, color="red", linestyle="--", alpha=0.7)
            plt.text(event_date, plt.ylim()[1] * 0.95, event, rotation=45, verticalalignment="top")

    plt.xlabel("Date")
    plt.ylabel(f"{metric.upper()} Level")
    plt.title(f"{metric.upper()} Over Time - HVAC/ERV Impact Analysis")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{metric}_timeline.png", dpi=300)
    plt.show()


def analyze_filter_impact(df):
    """Analyze the impact of filter changes"""
    print("\n=== Filter Impact Analysis ===")

    # Define periods
    periods = {
        "Baseline": (df.index.min(), pd.to_datetime(HVAC_INSTALL)),
        "HVAC Only": (pd.to_datetime(HVAC_INSTALL), pd.to_datetime(ERV_INSTALL)),
        "HVAC + ERV": (pd.to_datetime(ERV_INSTALL), pd.to_datetime(FILTER_UPGRADE)),
        "MERV 13": (pd.to_datetime(FILTER_UPGRADE), df.index.max()),
    }

    # Analyze PM2.5 for each period
    if "pm25" in df.columns:
        print("\nPM2.5 by Period:")
        baseline_pm25 = None

        for period_name, (start, end) in periods.items():
            period_data = df.loc[start:end, "pm25"]
            if len(period_data) > 0:
                mean_pm25 = period_data.mean()
                print(f"\n{period_name}:")
                print(f"  Mean: {mean_pm25:.1f} μg/m³")
                print(f"  Days: {len(period_data) / 24:.0f}")

                if baseline_pm25 is None:
                    baseline_pm25 = mean_pm25
                else:
                    reduction = ((baseline_pm25 - mean_pm25) / baseline_pm25) * 100
                    print(f"  Reduction from baseline: {reduction:.1f}%")


def predict_replacement(df):
    """Predict when to replace filters based on degradation"""
    print("\n=== Filter Replacement Prediction ===")

    # Get data since last filter change
    last_change = pd.to_datetime(FILTER_UPGRADE)
    recent_data = df[df.index >= last_change].copy()

    if len(recent_data) == 0:
        print("No data since last filter change!")
        return

    # Calculate days since installation
    recent_data["days_since_change"] = (recent_data.index - last_change).days

    # Simple degradation estimate based on PM2.5 increase
    if "pm25" in recent_data.columns:
        # Fit linear trend
        from scipy import stats

        days = recent_data["days_since_change"].values
        pm25 = recent_data["pm25"].values

        # Remove outliers for better fit
        mask = (pm25 < np.percentile(pm25, 95)) & (pm25 > np.percentile(pm25, 5))
        slope, intercept, r_value, p_value, std_err = stats.linregress(days[mask], pm25[mask])

        print(f"Current filter age: {days[-1]} days")
        print(f"PM2.5 increase rate: {slope:.3f} μg/m³ per day")

        # Predict when PM2.5 will exceed threshold
        # Assuming we want to keep indoor PM2.5 below 12 μg/m³
        target_pm25 = 12
        current_pm25 = recent_data["pm25"].rolling("24H").mean().iloc[-1]

        if slope > 0:
            days_until_target = (target_pm25 - current_pm25) / slope
            print(f"Current PM2.5 (24h avg): {current_pm25:.1f} μg/m³")
            print(f"Days until PM2.5 reaches {target_pm25} μg/m³: {days_until_target:.0f}")
            print(
                f"Recommended replacement date: {datetime.now().date() + pd.Timedelta(days=days_until_target)}"
            )
        else:
            print("PM2.5 levels are stable or decreasing - filters still effective!")


def generate_report(df):
    """Generate a summary report"""
    print("\n" + "=" * 50)
    print("HVAC/ERV FILTER ANALYSIS REPORT")
    print("=" * 50)

    analyze_air_quality(df)
    analyze_filter_impact(df)
    predict_replacement(df)

    # Cost analysis
    print("\n=== Cost Analysis ===")
    hvac_filter_cost = 130  # MERV 13
    erv_filter_cost = 50  # MERV 13

    days_since_last_change = (datetime.now() - pd.to_datetime(FILTER_UPGRADE)).days
    daily_cost = (hvac_filter_cost + erv_filter_cost) / days_since_last_change

    print(f"Days since last filter change: {days_since_last_change}")
    print(f"Total filter cost: ${hvac_filter_cost + erv_filter_cost}")
    print(f"Cost per day: ${daily_cost:.2f}")
    print(f"Annual cost (at current replacement rate): ${daily_cost * 365:.0f}")


def main():
    """Run the analysis"""
    # Update this path to your CSV file
    csv_path = "data/airthings_export.csv"

    print("Loading Airthings data...")
    df = load_airthings_csv(csv_path)

    if df is None:
        print("Failed to load data!")
        return

    # Generate visualizations
    for metric in ["pm25", "co2", "voc"]:
        if metric in df.columns:
            plot_timeline(df, metric)

    # Generate report
    generate_report(df)

    print("\n✓ Analysis complete! Check the generated PNG files for visualizations.")


if __name__ == "__main__":
    main()
