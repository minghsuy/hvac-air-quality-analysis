#!/usr/bin/env python3
"""
HVAC Air Quality Dashboard — Multi-page Streamlit app.
Pre-aggregates 98k rows on load so each page renders fast.

Run: streamlit run scripts/dashboard.py --server.port 8501
"""

import os
import time

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

PARQUET_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".cache", "air_quality.parquet"
)

st.set_page_config(page_title="HVAC Air Quality", page_icon="🌬️", layout="wide")

PLOT_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, system-ui, sans-serif"},
    "margin": {"l": 60, "r": 30, "t": 50, "b": 40},
    "hovermode": "x unified",
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
}

COLORS = {
    "master": "#4A90D9",
    "son": "#E8744F",
    "outdoor": "#F44336",
    "indoor": "#4CAF50",
    "threshold": "#D32F2F",
    "good": "#4CAF50",
    "warn": "#FF9800",
}


# ── Data Loading & Pre-aggregation ───────────────────────────────────────────


def _fetch_from_sheets():
    """Fetch raw data from Google Sheets API (~3.5s)."""
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    sheet_tab = os.getenv("GOOGLE_SHEET_TAB", "")
    creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google-credentials.json")
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    range_name = f"{sheet_tab}!A:R" if sheet_tab else "A:R"
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get("values", [])

    headers = values[0]
    n_cols = len(headers)
    padded, orig_cols = [], []
    for row in values[1:]:
        orig_cols.append(len(row))
        r = row + [""] * (n_cols - len(row)) if len(row) < n_cols else row[:n_cols]
        padded.append(r)

    df = pd.DataFrame(padded, columns=headers)
    df["_orig_cols"] = orig_cols
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    for col in [
        "Indoor_PM25",
        "Outdoor_PM25",
        "Filter_Efficiency",
        "Indoor_CO2",
        "Outdoor_CO2",
        "Indoor_VOC",
        "Indoor_NOX",
        "Indoor_Temp",
        "Indoor_Humidity",
        "Indoor_Radon",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    shifted = df["_orig_cols"] < 18
    for col in [
        "Indoor_Temp",
        "Indoor_Humidity",
        "Indoor_Radon",
        "Outdoor_CO2",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    ]:
        if col in df.columns:
            df.loc[shifted, col] = np.nan

    df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)
    return df


def _save_parquet(df):
    """Save cleaned DataFrame to local Parquet cache."""
    os.makedirs(os.path.dirname(PARQUET_CACHE), exist_ok=True)
    df.drop(columns=["_orig_cols"], errors="ignore").to_parquet(PARQUET_CACHE)


def load_raw(force_refresh=False):
    """Load data with Parquet cache. Falls back to Sheets API if cache is missing/stale."""
    # Use parquet cache if it exists and is fresh (< 1 hour old)
    if not force_refresh and os.path.exists(PARQUET_CACHE):
        cache_age = time.time() - os.path.getmtime(PARQUET_CACHE)
        if cache_age < 3600:  # 1 hour
            t0 = time.perf_counter()
            df = pd.read_parquet(PARQUET_CACHE)
            elapsed = time.perf_counter() - t0
            st.toast(f"Loaded from cache in {elapsed * 1000:.0f}ms ({len(df):,} rows)", icon="⚡")
            return df

    # Fetch from Sheets API and update cache
    t0 = time.perf_counter()
    df = _fetch_from_sheets()
    elapsed = time.perf_counter() - t0
    _save_parquet(df)
    st.toast(f"Fetched from Sheets in {elapsed:.1f}s ({len(df):,} rows), cache updated", icon="☁️")
    return df


@st.cache_data(ttl=600, show_spinner="Pre-aggregating...")
def precompute(df_raw):
    """Pre-aggregate to hourly and daily — this is what pages use."""
    metrics = [
        "Indoor_CO2",
        "Indoor_PM25",
        "Outdoor_PM25",
        "Filter_Efficiency",
        "Indoor_Temp",
        "Indoor_Humidity",
        "Indoor_VOC",
        "Indoor_NOX",
        "Indoor_Radon",
        "Outdoor_CO2",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    ]

    rooms = ["master_bedroom", "second_bedroom"]
    hourly = {}
    daily = {}

    for room in rooms:
        rd = df_raw[df_raw["Room"] == room].set_index("Timestamp")
        for m in metrics:
            if m in rd.columns:
                s = rd[m].dropna()
                if not s.empty:
                    hourly[(room, m)] = s.resample("1h").mean().dropna()
                    daily[(room, m)] = s.resample("1D").agg(["mean", "min", "max"]).dropna()

    return hourly, daily


def get_data():
    force = st.session_state.get("_force_refresh", False)
    if force:
        st.session_state.pop("_force_refresh", None)
        st.session_state.pop("_cached_raw", None)
        st.session_state.pop("_cached_hourly", None)
        st.session_state.pop("_cached_daily", None)

    if "_cached_raw" not in st.session_state or force:
        raw = load_raw(force_refresh=force)
        hourly, daily = precompute(raw)
        st.session_state["_cached_raw"] = raw
        st.session_state["_cached_hourly"] = hourly
        st.session_state["_cached_daily"] = daily

    return (
        st.session_state["_cached_raw"],
        st.session_state["_cached_hourly"],
        st.session_state["_cached_daily"],
    )


# ── Shared sidebar ───────────────────────────────────────────────────────────


def sidebar_date_range(raw):
    min_date = raw["Timestamp"].min().date()
    max_date = raw["Timestamp"].max().date()

    st.sidebar.markdown(f"**{len(raw):,} readings**")
    st.sidebar.markdown(f"{min_date} → {max_date}")

    # Show cache status and refresh button
    if os.path.exists(PARQUET_CACHE):
        cache_age_min = (time.time() - os.path.getmtime(PARQUET_CACHE)) / 60
        st.sidebar.caption(f"Cache: {cache_age_min:.0f}min old")
    if st.sidebar.button("Refresh from Sheets"):
        st.session_state["_force_refresh"] = True
        st.rerun()

    preset = st.sidebar.radio("Range", ["All", "90d", "30d", "7d"], horizontal=True)
    if preset == "90d":
        start = max_date - pd.Timedelta(days=90)
    elif preset == "30d":
        start = max_date - pd.Timedelta(days=30)
    elif preset == "7d":
        start = max_date - pd.Timedelta(days=7)
    else:
        start = min_date

    custom = st.sidebar.date_input(
        "Custom", value=(start, max_date), min_value=min_date, max_value=max_date
    )
    if len(custom) == 2:
        return pd.Timestamp(custom[0]), pd.Timestamp(custom[1]) + pd.Timedelta(days=1)
    return pd.Timestamp(start), pd.Timestamp(max_date) + pd.Timedelta(days=1)


def filter_series(series, dr):
    return series[(series.index >= dr[0]) & (series.index < dr[1])]


def filter_daily(daily_df, dr):
    return daily_df[(daily_df.index >= dr[0]) & (daily_df.index < dr[1])]


# ── Pages ────────────────────────────────────────────────────────────────────


def page_overview():
    import plotly.graph_objects as go

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# 🌬️ Air Quality Overview")

    co2_data = raw[(raw["Indoor_CO2"].notna()) & (raw["Indoor_CO2"] > 0)]
    pm_data = raw[raw["Indoor_PM25"].notna()]
    eff_data = raw[(raw["Filter_Efficiency"].notna()) & (raw["Filter_Efficiency"] > 0)]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        v = co2_data["Indoor_CO2"].mean()
        st.metric("Avg CO₂", f"{v:.0f} ppm", delta=f"{1000 - v:.0f} below threshold")
    with c2:
        v = pm_data["Indoor_PM25"].mean()
        st.metric("Avg Indoor PM2.5", f"{v:.1f} μg/m³", delta="Below WHO 15")
    with c3:
        v = eff_data["Filter_Efficiency"].mean()
        st.metric("Avg Efficiency", f"{v:.1f}%", delta=f"{v - 85:.1f}% above target")
    with c4:
        v = (co2_data["Indoor_CO2"] <= 1000).mean() * 100
        st.metric("CO₂ Safe", f"{v:.1f}%", delta=f"{len(raw):,} readings")

    # One summary chart: CO₂ rolling (lightweight — daily data only)
    fig = go.Figure()
    for room, color, name in [
        ("master_bedroom", COLORS["master"], "Master"),
        ("second_bedroom", COLORS["son"], "Son's Room"),
    ]:
        key = (room, "Indoor_CO2")
        if key not in daily:
            continue
        d = filter_daily(daily[key], dr)
        if d.empty:
            continue
        r = d["mean"].rolling(3, min_periods=1).mean()
        fig.add_trace(
            go.Scatter(
                x=r.index,
                y=r.values,
                mode="lines",
                name=f"{name} (avg {d['mean'].mean():.0f})",
                line={"color": color, "width": 2.5},
                hovertemplate="%{y:.0f} ppm<extra></extra>",
            )
        )

    fig.add_hline(
        y=1000,
        line_dash="dash",
        line_color=COLORS["threshold"],
        annotation_text="1000 ppm — cognitive impairment",
        annotation_position="top left",
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        title={"text": "CO₂ Trend (3-day rolling)", "font": {"size": 16}},
        yaxis_title="CO₂ (ppm)",
        height=400,
    )
    st.plotly_chart(fig, key="overview_co2")


def page_co2_compare():
    import plotly.graph_objects as go
    from statsmodels.nonparametric.smoothers_lowess import lowess as lowess_fn

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# CO₂ — Visualization Comparison")
    st.caption("Same data, four ways. Pick your favorite.")

    choice = st.radio(
        "Style",
        ["Rolling Avg + Band", "Heatmap", "Weekly Box Plots", "LOWESS + Anomalies"],
        horizontal=True,
        key="co2_style",
    )

    if choice == "Rolling Avg + Band":
        fig = go.Figure()
        for room, color, name in [
            ("master_bedroom", COLORS["master"], "Master"),
            ("second_bedroom", COLORS["son"], "Son's Room"),
        ]:
            key = (room, "Indoor_CO2")
            if key not in daily:
                continue
            d = filter_daily(daily[key], dr)
            if d.empty:
                continue
            r_mean = d["mean"].rolling(3, min_periods=1).mean()
            r_min = d["min"].rolling(3, min_periods=1).min()
            r_max = d["max"].rolling(3, min_periods=1).max()

            hex_c = color
            rgba = f"rgba({int(hex_c[1:3], 16)},{int(hex_c[3:5], 16)},{int(hex_c[5:7], 16)},0.12)"
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
            fig.add_trace(
                go.Scatter(
                    x=r_mean.index,
                    y=r_mean.values,
                    mode="lines",
                    name=f"{name} (avg {d['mean'].mean():.0f})",
                    line={"color": color, "width": 2.5},
                    hovertemplate=f"%{{y:.0f}} ppm<extra>{name}</extra>",
                )
            )

        fig.add_hline(
            y=1000,
            line_dash="dash",
            line_color=COLORS["threshold"],
            annotation_text="1000 ppm threshold",
            annotation_position="top left",
        )
        fig.add_hline(y=600, line_dash="dot", line_color=COLORS["good"], opacity=0.5)
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "3-Day Rolling Avg + Daily Range"},
            yaxis_title="ppm",
            yaxis={"range": [300, 1200]},
            height=500,
        )
        st.plotly_chart(fig, key="co2_roll")

    elif choice == "Heatmap":
        room = st.radio(
            "Room",
            ["master_bedroom", "second_bedroom"],
            horizontal=True,
            format_func=lambda x: "Master" if x == "master_bedroom" else "Son's Room",
            key="hm_room",
        )
        sub = raw[
            (raw["Room"] == room)
            & (raw["Indoor_CO2"].notna())
            & (raw["Indoor_CO2"] > 0)
            & (raw["Timestamp"] >= dr[0])
            & (raw["Timestamp"] < dr[1])
        ].copy()
        if sub.empty:
            st.info("No data for this room/range")
            return
        sub["hour"] = sub["Timestamp"].dt.hour
        sub["date"] = sub["Timestamp"].dt.date
        pivot = sub.pivot_table(values="Indoor_CO2", index="hour", columns="date", aggfunc="mean")
        pivot = pivot.sort_index(ascending=False)

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=[str(d) for d in pivot.columns],
                y=[f"{h:02d}:00" for h in pivot.index],
                colorscale=[
                    [0, "#1a237e"],
                    [0.3, "#4CAF50"],
                    [0.5, "#FFC107"],
                    [0.7, "#FF9800"],
                    [0.85, "#F44336"],
                    [1, "#B71C1C"],
                ],
                zmin=350,
                zmax=1200,
                colorbar={"title": "ppm", "thickness": 15},
                hovertemplate="Date: %{x}<br>%{y}<br>CO₂: %{z:.0f} ppm<extra></extra>",
            )
        )
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "CO₂ Heatmap — Hour × Date"},
            xaxis={"dtick": 7, "tickangle": -45},
            height=450,
        )
        st.plotly_chart(fig, key="co2_heat")

    elif choice == "Weekly Box Plots":
        sub = raw[
            (raw["Indoor_CO2"].notna())
            & (raw["Indoor_CO2"] > 0)
            & (raw["Timestamp"] >= dr[0])
            & (raw["Timestamp"] < dr[1])
        ].copy()
        sub["year_week"] = sub["Timestamp"].dt.strftime("%Y-W%V")

        fig = go.Figure()
        for room, color, name in [
            ("master_bedroom", COLORS["master"], "Master"),
            ("second_bedroom", COLORS["son"], "Son's"),
        ]:
            rd = sub[sub["Room"] == room]
            if rd.empty:
                continue
            for w in sorted(rd["year_week"].unique()):
                fig.add_trace(
                    go.Box(
                        y=rd[rd["year_week"] == w]["Indoor_CO2"],
                        name=w,
                        marker_color=color,
                        line_color=color,
                        boxmean=True,
                        showlegend=False,
                    )
                )

        fig.add_hline(y=1000, line_dash="dash", line_color=COLORS["threshold"])
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "Weekly CO₂ Distribution"},
            yaxis_title="ppm",
            yaxis={"range": [300, 1200]},
            xaxis={"tickangle": -45},
            height=500,
        )
        st.plotly_chart(fig, key="co2_box")

    elif choice == "LOWESS + Anomalies":
        fig = go.Figure()
        for room, color, name in [
            ("master_bedroom", COLORS["master"], "Master"),
            ("second_bedroom", COLORS["son"], "Son's Room"),
        ]:
            key = (room, "Indoor_CO2")
            if key not in hourly:
                continue
            s = filter_series(hourly[key], dr).resample("6h").mean().dropna()
            if len(s) < 10:
                continue
            x_num = np.arange(len(s))
            sm = lowess_fn(s.values, x_num, frac=0.08, return_sorted=False)
            resid = s.values - sm
            mask = resid > 1.5 * resid.std()

            fig.add_trace(
                go.Scatter(
                    x=s.index,
                    y=sm,
                    mode="lines",
                    name=f"{name} (LOWESS)",
                    line={"color": color, "width": 2.5},
                    hovertemplate=f"%{{y:.0f}} ppm<extra>{name}</extra>",
                )
            )
            if mask.any():
                fig.add_trace(
                    go.Scatter(
                        x=s.index[mask],
                        y=s.values[mask],
                        mode="markers",
                        name=f"{name} spikes",
                        marker={"color": COLORS["threshold"], "size": 8, "symbol": "diamond"},
                        hovertemplate="%{y:.0f} ppm — SPIKE<extra></extra>",
                    )
                )

        fig.add_hline(y=1000, line_dash="dash", line_color=COLORS["threshold"])
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "LOWESS + Anomaly Detection"},
            yaxis_title="ppm",
            yaxis={"range": [300, 1200]},
            height=500,
        )
        st.plotly_chart(fig, key="co2_low")


def page_heatmaps():
    import plotly.graph_objects as go

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# Seasonal & Time-of-Day Patterns")

    metric_group = st.radio(
        "Category", ["Indoor Air", "Outdoor", "Comfort"], horizontal=True, key="hm_cat"
    )

    if metric_group == "Indoor Air":
        metric = st.radio(
            "Metric",
            ["CO₂", "Indoor PM2.5", "VOC Index", "NOX Index", "Radon", "Filter Efficiency"],
            horizontal=True,
            key="hm_metric_indoor",
        )
    elif metric_group == "Outdoor":
        metric = st.radio(
            "Metric",
            [
                "Outdoor PM2.5",
                "Outdoor CO₂",
                "Outdoor VOC",
                "Outdoor NOX",
                "Outdoor Temp",
                "Outdoor Humidity",
            ],
            horizontal=True,
            key="hm_metric_outdoor",
        )
    else:
        metric = st.radio(
            "Metric", ["Temperature", "Humidity"], horizontal=True, key="hm_metric_comfort"
        )

    metric_map = {
        "CO₂": "Indoor_CO2",
        "Indoor PM2.5": "Indoor_PM25",
        "VOC Index": "Indoor_VOC",
        "NOX Index": "Indoor_NOX",
        "Radon": "Indoor_Radon",
        "Filter Efficiency": "Filter_Efficiency",
        "Outdoor PM2.5": "Outdoor_PM25",
        "Outdoor CO₂": "Outdoor_CO2",
        "Outdoor VOC": "Outdoor_VOC",
        "Outdoor NOX": "Outdoor_NOX",
        "Outdoor Temp": "Outdoor_Temp",
        "Outdoor Humidity": "Outdoor_Humidity",
        "Temperature": "Indoor_Temp",
        "Humidity": "Indoor_Humidity",
    }
    col = metric_map[metric]

    cs_map = {
        "Indoor_CO2": (
            [
                [0, "#1a237e"],
                [0.3, "#4CAF50"],
                [0.5, "#FFC107"],
                [0.7, "#FF9800"],
                [0.85, "#F44336"],
                [1, "#B71C1C"],
            ],
            350,
            1200,
            "ppm",
        ),
        "Indoor_PM25": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#880E4F"]],
            0,
            10,
            "μg/m³",
        ),
        "Outdoor_PM25": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#880E4F"]],
            0,
            30,
            "μg/m³",
        ),
        "Filter_Efficiency": (
            [[0, "#B71C1C"], [0.3, "#FF9800"], [0.5, "#FFC107"], [0.7, "#4CAF50"], [1, "#1B5E20"]],
            0,
            100,
            "%",
        ),
        "Indoor_Temp": (
            [[0, "#1565C0"], [0.3, "#42A5F5"], [0.5, "#FFC107"], [0.7, "#FF7043"], [1, "#B71C1C"]],
            18,
            30,
            "°C",
        ),
        "Indoor_Humidity": (
            [[0, "#FFCC80"], [0.3, "#FF9800"], [0.5, "#4CAF50"], [0.7, "#42A5F5"], [1, "#0D47A1"]],
            25,
            65,
            "%",
        ),
        "Indoor_VOC": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            0,
            300,
            "index",
        ),
        "Indoor_NOX": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            0,
            300,
            "index",
        ),
        "Indoor_Radon": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            0,
            150,
            "Bq/m³",
        ),
        "Outdoor_CO2": (
            [[0, "#1a237e"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            350,
            600,
            "ppm",
        ),
        "Outdoor_Temp": (
            [[0, "#1565C0"], [0.3, "#42A5F5"], [0.5, "#FFC107"], [0.7, "#FF7043"], [1, "#B71C1C"]],
            -10,
            40,
            "°C",
        ),
        "Outdoor_Humidity": (
            [[0, "#FFCC80"], [0.3, "#FF9800"], [0.5, "#4CAF50"], [0.7, "#42A5F5"], [1, "#0D47A1"]],
            20,
            100,
            "%",
        ),
        "Outdoor_VOC": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            0,
            300,
            "index",
        ),
        "Outdoor_NOX": (
            [[0, "#1B5E20"], [0.3, "#4CAF50"], [0.5, "#FFC107"], [0.7, "#FF9800"], [1, "#B71C1C"]],
            0,
            300,
            "index",
        ),
    }
    cs, zmin, zmax, unit = cs_map[col]

    outdoor_cols = {
        "Outdoor_PM25",
        "Outdoor_CO2",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    }
    room_needed = col not in outdoor_cols
    if room_needed:
        room = st.radio(
            "Room",
            ["master_bedroom", "second_bedroom"],
            horizontal=True,
            format_func=lambda x: "Master" if x == "master_bedroom" else "Son's Room",
            key="hm_r",
        )
    else:
        room = "master_bedroom"

    sub = raw[(raw[col].notna()) & (raw["Timestamp"] >= dr[0]) & (raw["Timestamp"] < dr[1])].copy()
    if room:
        sub = sub[sub["Room"] == room]
    if sub.empty:
        st.info("No data for this selection")
        return

    # ── Heatmap ──
    sub["hour"] = sub["Timestamp"].dt.hour
    sub["date"] = sub["Timestamp"].dt.date
    pivot = sub.pivot_table(values=col, index="hour", columns="date", aggfunc="mean")
    pivot = pivot.sort_index(ascending=False)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(d) for d in pivot.columns],
            y=[f"{h:02d}:00" for h in pivot.index],
            colorscale=cs,
            zmin=zmin,
            zmax=zmax,
            colorbar={"title": unit, "thickness": 15},
            hovertemplate=f"Date: %{{x}}<br>%{{y}}<br>{metric}: %{{z:.1f}} {unit}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        title={"text": f"{metric} — Hour × Date", "font": {"size": 16}},
        xaxis={"dtick": 7, "tickangle": -45},
        height=420,
    )
    st.plotly_chart(fig, key="hm_main")

    # ── Two small charts side by side ──
    col1, col2 = st.columns(2)

    with col1:
        # Weekday vs Weekend
        sub["is_weekend"] = sub["Timestamp"].dt.dayofweek >= 5
        wd = sub[~sub["is_weekend"]].groupby("hour")[col].mean()
        we = sub[sub["is_weekend"]].groupby("hour")[col].mean()

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=wd.index,
                y=wd.values,
                mode="lines+markers",
                name="Weekday",
                line={"color": COLORS["master"], "width": 2.5},
                marker={"size": 5},
            )
        )
        fig2.add_trace(
            go.Scatter(
                x=we.index,
                y=we.values,
                mode="lines+markers",
                name="Weekend",
                line={"color": COLORS["son"], "width": 2.5, "dash": "dash"},
                marker={"size": 5},
            )
        )
        fig2.update_layout(
            **PLOT_LAYOUT,
            title={"text": "Weekday vs Weekend", "font": {"size": 14}},
            xaxis={
                "dtick": 2,
                "tickvals": list(range(0, 24, 2)),
                "ticktext": [f"{h:02d}" for h in range(0, 24, 2)],
            },
            yaxis_title=unit,
            height=320,
        )
        st.plotly_chart(fig2, key="hm_dow")

    with col2:
        # Monthly profiles
        sub["month"] = sub["Timestamp"].dt.to_period("M").astype(str)
        months = sorted(sub["month"].unique())
        n = len(months)
        fig3 = go.Figure()
        for i, month in enumerate(months):
            mdata = sub[sub["month"] == month].groupby("hour")[col].mean()
            hue = int(200 + i * 160 / max(n - 1, 1))
            fig3.add_trace(
                go.Scatter(
                    x=mdata.index,
                    y=mdata.values,
                    mode="lines",
                    name=month,
                    line={"color": f"hsl({hue},70%,55%)", "width": 2},
                )
            )
        fig3.update_layout(
            **PLOT_LAYOUT,
            title={"text": "Monthly Profiles", "font": {"size": 14}},
            xaxis={
                "dtick": 2,
                "tickvals": list(range(0, 24, 2)),
                "ticktext": [f"{h:02d}" for h in range(0, 24, 2)],
            },
            yaxis_title=unit,
            height=320,
        )
        st.plotly_chart(fig3, key="hm_month")


def page_filter_pm25():
    import plotly.graph_objects as go

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# Filter Efficiency & PM2.5")

    choice = st.radio(
        "Chart", ["Filter Efficiency", "Indoor vs Outdoor PM2.5"], horizontal=True, key="fp_choice"
    )

    if choice == "Filter Efficiency":
        key = ("master_bedroom", "Filter_Efficiency")
        if key not in daily:
            st.info("No efficiency data")
            return
        d = filter_daily(daily[key], dr)
        h = filter_series(hourly[key], dr) if key in hourly else pd.Series(dtype=float)
        rolling = d["mean"].rolling(7, min_periods=1).mean()

        fig = go.Figure()
        if not h.empty:
            # Downsample scatter to daily for performance
            h_daily = h.resample("6h").mean().dropna()
            fig.add_trace(
                go.Scatter(
                    x=h_daily.index,
                    y=h_daily.values,
                    mode="markers",
                    name="6h readings",
                    marker={"color": COLORS["master"], "size": 3, "opacity": 0.2},
                )
            )
        fig.add_trace(
            go.Scatter(
                x=rolling.index,
                y=rolling.values,
                mode="lines",
                name="7-day rolling avg",
                line={"color": "#42A5F5", "width": 3},
            )
        )
        fig.add_hline(
            y=85,
            line_dash="dash",
            line_color=COLORS["good"],
            annotation_text="85% target",
            annotation_position="bottom right",
        )

        start = d.index.min()
        end = d.index.max()
        for days, label, color in [
            (45, "Mfr: 45d", COLORS["warn"]),
            (90, "ERV spec: 90d", COLORS["threshold"]),
            (120, "120d — >85%!", COLORS["good"]),
        ]:
            md = start + pd.Timedelta(days=days)
            if md <= end:
                fig.add_vline(
                    x=int(md.timestamp() * 1000), line_dash="dot", line_color=color, opacity=0.7
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

        total_days = (end - start).days
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": f"Filter Efficiency — {total_days} Days"},
            yaxis_title="%",
            yaxis={"range": [0, 105]},
            height=500,
        )
        st.plotly_chart(fig, key="fp_eff")

    else:
        out_key = ("master_bedroom", "Outdoor_PM25")
        in_key = ("master_bedroom", "Indoor_PM25")
        if out_key not in daily or in_key not in daily:
            st.info("No PM2.5 data")
            return
        out_d = filter_daily(daily[out_key], dr)["mean"].rolling(3, min_periods=1).mean().dropna()
        in_d = filter_daily(daily[in_key], dr)["mean"].rolling(3, min_periods=1).mean().dropna()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=out_d.index,
                y=out_d.values,
                mode="lines",
                name=f"Outdoor (avg {daily[out_key]['mean'].mean():.1f})",
                line={"color": COLORS["outdoor"], "width": 2.5},
                fill="tozeroy",
                fillcolor="rgba(244,67,54,0.12)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=in_d.index,
                y=in_d.values,
                mode="lines",
                name=f"Indoor (avg {daily[in_key]['mean'].mean():.1f})",
                line={"color": COLORS["indoor"], "width": 2.5},
                fill="tozeroy",
                fillcolor="rgba(76,175,80,0.15)",
            )
        )
        fig.add_hline(
            y=15,
            line_dash="dash",
            line_color=COLORS["warn"],
            annotation_text="WHO 24h guideline",
            annotation_position="top right",
        )

        om, im = daily[out_key]["mean"].mean(), daily[in_key]["mean"].mean()
        red = ((om - im) / om * 100) if om > 0 else 0
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": f"Indoor vs Outdoor PM2.5 — {red:.0f}% reduction"},
            yaxis_title="μg/m³",
            yaxis={"range": [0, max(40, out_d.max() * 1.2)]},
            height=500,
        )
        st.plotly_chart(fig, key="fp_pm")


def page_environment():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# Environment — Temperature & Humidity")
    room = st.radio(
        "Room",
        ["master_bedroom", "second_bedroom"],
        horizontal=True,
        format_func=lambda x: "Master" if x == "master_bedroom" else "Son's Room",
        key="env_room",
    )

    choice = st.radio(
        "View",
        ["Indoor + Outdoor Overlay", "Indoor Only", "Radon"],
        horizontal=True,
        key="env_view",
    )

    if choice == "Indoor + Outdoor Overlay":
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=["Temperature (°C)", "Humidity (%)"],
        )

        for metric, row, colors in [
            ("Temp", 1, {"indoor": "#FF7043", "outdoor": "#1565C0"}),
            ("Humidity", 2, {"indoor": "#42A5F5", "outdoor": "#8D6E63"}),
        ]:
            in_key = (room, f"Indoor_{metric}")
            out_key = (room, f"Outdoor_{metric}")
            if in_key in daily:
                d = filter_daily(daily[in_key], dr)["mean"].rolling(3, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=d.index,
                        y=d.values,
                        mode="lines",
                        name=f"Indoor {metric}",
                        line={"color": colors["indoor"], "width": 2.5},
                    ),
                    row=row,
                    col=1,
                )
            if out_key in daily:
                d = filter_daily(daily[out_key], dr)["mean"].rolling(3, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=d.index,
                        y=d.values,
                        mode="lines",
                        name=f"Outdoor {metric}",
                        line={"color": colors["outdoor"], "width": 2, "dash": "dash"},
                    ),
                    row=row,
                    col=1,
                )

        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "Indoor vs Outdoor: Temp & Humidity (3-day rolling)"},
            height=550,
        )
        st.plotly_chart(fig, key="env_overlay")

    elif choice == "Indoor Only":
        t_key = (room, "Indoor_Temp")
        h_key = (room, "Indoor_Humidity")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        if t_key in daily:
            td = filter_daily(daily[t_key], dr)
            t_mean = td["mean"].rolling(3, min_periods=1).mean()
            t_min = td["min"].rolling(3, min_periods=1).min()
            t_max = td["max"].rolling(3, min_periods=1).max()

            fig.add_trace(
                go.Scatter(
                    x=t_max.index,
                    y=t_max.values,
                    mode="lines",
                    line={"width": 0},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(
                    x=t_min.index,
                    y=t_min.values,
                    mode="lines",
                    line={"width": 0},
                    fill="tonexty",
                    fillcolor="rgba(255,112,67,0.12)",
                    showlegend=False,
                    hoverinfo="skip",
                ),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(
                    x=t_mean.index,
                    y=t_mean.values,
                    mode="lines",
                    name=f"Temp (avg {td['mean'].mean():.1f}°C)",
                    line={"color": "#FF7043", "width": 2.5},
                ),
                secondary_y=False,
            )

        if h_key in daily:
            hd = filter_daily(daily[h_key], dr)
            h_mean = hd["mean"].rolling(3, min_periods=1).mean()
            h_min = hd["min"].rolling(3, min_periods=1).min()
            h_max = hd["max"].rolling(3, min_periods=1).max()

            fig.add_trace(
                go.Scatter(
                    x=h_max.index,
                    y=h_max.values,
                    mode="lines",
                    line={"width": 0},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )
            fig.add_trace(
                go.Scatter(
                    x=h_min.index,
                    y=h_min.values,
                    mode="lines",
                    line={"width": 0},
                    fill="tonexty",
                    fillcolor="rgba(66,165,245,0.12)",
                    showlegend=False,
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )
            fig.add_trace(
                go.Scatter(
                    x=h_mean.index,
                    y=h_mean.values,
                    mode="lines",
                    name=f"Humidity (avg {hd['mean'].mean():.1f}%)",
                    line={"color": "#42A5F5", "width": 2.5},
                ),
                secondary_y=True,
            )

        fig.add_hrect(
            y0=20,
            y1=25,
            line_width=0,
            fillcolor="rgba(255,112,67,0.06)",
            annotation_text="Comfort zone",
            annotation_position="top left",
            secondary_y=False,
        )

        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": f"{room.replace('_', ' ').title()} — Temp & Humidity"},
            height=450,
        )
        fig.update_yaxes(title_text="°C", secondary_y=False)
        fig.update_yaxes(title_text="%", secondary_y=True)
        st.plotly_chart(fig, key="env_indoor")

    elif choice == "Radon":
        radon_key = (room, "Indoor_Radon")
        if radon_key not in daily:
            st.info("No radon data for this room/range (available post-September 2025)")
            return
        d = filter_daily(daily[radon_key], dr)
        if d.empty:
            st.info("No radon data in selected range")
            return

        r_mean = d["mean"].rolling(7, min_periods=1).mean()
        r_min = d["min"].rolling(7, min_periods=1).min()
        r_max = d["max"].rolling(7, min_periods=1).max()

        fig = go.Figure()
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
                fillcolor="rgba(156,39,176,0.12)",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=r_mean.index,
                y=r_mean.values,
                mode="lines",
                name=f"Radon (avg {d['mean'].mean():.0f} Bq/m³)",
                line={"color": "#9C27B0", "width": 2.5},
            )
        )
        fig.add_hline(
            y=100,
            line_dash="dash",
            line_color=COLORS["warn"],
            annotation_text="WHO action level (100 Bq/m³)",
            annotation_position="top right",
        )
        fig.add_hline(
            y=148,
            line_dash="dash",
            line_color=COLORS["threshold"],
            annotation_text="EPA action level (4 pCi/L ≈ 148 Bq/m³)",
            annotation_position="bottom right",
        )

        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "Indoor Radon (7-day rolling)"},
            yaxis_title="Bq/m³",
            height=450,
        )
        st.plotly_chart(fig, key="env_radon")


def page_correlations():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# Multivariate Analysis")
    st.caption("How do metrics relate to each other? Select a view below.")

    choice = st.radio(
        "View",
        ["Correlation Matrix", "Outdoor → Indoor Impact", "ERV Tradeoff (CO₂ vs PM2.5)"],
        horizontal=True,
        key="corr_choice",
    )

    room = "master_bedroom"

    if choice == "Correlation Matrix":
        corr_method = st.radio(
            "Method", ["Spearman (recommended)", "Pearson"], horizontal=True, key="corr_method"
        )
        method = "spearman" if "Spearman" in corr_method else "pearson"
        method_label = "ρ" if method == "spearman" else "r"

        corr_cols = [
            "Indoor_CO2",
            "Indoor_PM25",
            "Outdoor_PM25",
            "Indoor_VOC",
            "Indoor_NOX",
            "Indoor_Radon",
            "Indoor_Temp",
            "Indoor_Humidity",
            "Outdoor_Temp",
            "Outdoor_Humidity",
            "Outdoor_CO2",
            "Outdoor_VOC",
            "Outdoor_NOX",
            "Filter_Efficiency",
        ]
        sub = raw[(raw["Room"] == room) & (raw["Timestamp"] >= dr[0]) & (raw["Timestamp"] < dr[1])]
        available = [c for c in corr_cols if c in sub.columns and sub[c].notna().sum() > 100]
        corr = sub[available].corr(method=method)

        labels = [
            c.replace("Indoor_", "In ").replace("Outdoor_", "Out ").replace("_", " ")
            for c in available
        ]
        fig = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=labels,
                y=labels,
                colorscale=[
                    [0, "#1565C0"],
                    [0.25, "#42A5F5"],
                    [0.5, "#FFFFFF"],
                    [0.75, "#FF7043"],
                    [1, "#B71C1C"],
                ],
                zmin=-1,
                zmax=1,
                colorbar={"title": method_label, "thickness": 15},
                text=np.round(corr.values, 2),
                texttemplate="%{text}",
                hovertemplate=f"%{{x}} vs %{{y}}<br>{method_label} = %{{z:.2f}}<extra></extra>",
            )
        )
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": f"Metric Correlations — {method.title()} (Master Bedroom)"},
            height=550,
            xaxis={"tickangle": -45},
        )
        st.plotly_chart(fig, key="corr_matrix")

        if method == "spearman":
            st.caption(
                "Spearman rank correlation: captures monotonic relationships, robust to outliers and skewed data (cooking spikes, flat NOX index)."
            )
        else:
            st.caption(
                "Pearson: assumes linear relationships. Sensitive to outliers like PM2.5 cooking spikes."
            )

        # Highlight interesting correlations
        strong = []
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                v = corr.iloc[i, j]
                if abs(v) > 0.4:
                    strong.append((available[i], available[j], v))
        if strong:
            strong.sort(key=lambda x: abs(x[2]), reverse=True)
            st.markdown(f"**Notable correlations (|{method_label}| > 0.4):**")
            for a, b, v in strong[:10]:
                direction = "positive" if v > 0 else "inverse"
                a_label = a.replace("Indoor_", "").replace("Outdoor_", "Out ")
                b_label = b.replace("Indoor_", "").replace("Outdoor_", "Out ")
                st.markdown(
                    f"- **{a_label}** ↔ **{b_label}**: {method_label}={v:.2f} ({direction})"
                )

    elif choice == "Outdoor → Indoor Impact":
        st.markdown("### How outdoor conditions drive indoor air quality")

        pairs = [
            (
                "Outdoor_Temp",
                "Indoor_CO2",
                "Outdoor Temp → CO₂",
                "When it's cold, windows closed → CO₂ rises",
            ),
            (
                "Outdoor_PM25",
                "Indoor_PM25",
                "Outdoor PM2.5 → Indoor PM2.5",
                "ERV brings outdoor particles in",
            ),
            (
                "Outdoor_Humidity",
                "Indoor_Humidity",
                "Outdoor Humidity → Indoor Humidity",
                "Moisture ingress",
            ),
            (
                "Outdoor_Temp",
                "Indoor_PM25",
                "Outdoor Temp → Indoor PM2.5",
                "Cold = more heating = more indoor particles?",
            ),
        ]
        pair_labels = [p[2] for p in pairs]
        sel = st.radio("Relationship", pair_labels, horizontal=True, key="corr_pair")
        idx = pair_labels.index(sel)
        x_col, y_col, title, desc = pairs[idx]

        sub = raw[
            (raw["Room"] == room)
            & (raw["Timestamp"] >= dr[0])
            & (raw["Timestamp"] < dr[1])
            & (raw[x_col].notna())
            & (raw[y_col].notna())
        ].copy()

        if sub.empty:
            st.info("No overlapping data for this pair")
            return

        # Downsample for performance — daily averages
        sub = sub.set_index("Timestamp")[[x_col, y_col]].resample("1D").mean().dropna()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=sub[x_col],
                y=sub[y_col],
                mode="markers",
                marker={
                    "color": np.arange(len(sub)),
                    "colorscale": "Viridis",
                    "size": 8,
                    "colorbar": {"title": "Day", "thickness": 10},
                    "opacity": 0.7,
                },
                hovertemplate=f"{x_col}: %{{x:.1f}}<br>{y_col}: %{{y:.1f}}<extra></extra>",
            )
        )

        # Trend line
        z = np.polyfit(sub[x_col], sub[y_col], 1)
        x_line = np.linspace(sub[x_col].min(), sub[x_col].max(), 50)
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=np.polyval(z, x_line),
                mode="lines",
                name=f"Trend (slope={z[0]:.2f})",
                line={"color": "#FF9800", "width": 2, "dash": "dash"},
            )
        )

        rho = sub[x_col].corr(sub[y_col], method="spearman")
        r = sub[x_col].corr(sub[y_col])
        x_label = x_col.replace("_", " ")
        y_label = y_col.replace("_", " ")
        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": f"{title} (Spearman ρ={rho:.2f}, Pearson r={r:.2f})"},
            xaxis_title=x_label,
            yaxis_title=y_label,
            height=450,
        )
        st.plotly_chart(fig, key="corr_scatter")
        st.caption(desc)

    elif choice == "ERV Tradeoff (CO₂ vs PM2.5)":
        st.markdown("### The ERV dilemma: more fresh air = lower CO₂ but higher PM2.5")
        st.caption(
            "High ERV flow → lower CO₂, but brings outdoor particles in. Low flow → CO₂ rises, PM2.5 stays low."
        )

        co2_key = (room, "Indoor_CO2")
        pm_key = (room, "Indoor_PM25")
        out_pm_key = (room, "Outdoor_PM25")

        if co2_key not in daily or pm_key not in daily:
            st.info("Need CO₂ and PM2.5 data")
            return

        co2_d = filter_daily(daily[co2_key], dr)["mean"]
        pm_d = filter_daily(daily[pm_key], dr)["mean"]
        common = co2_d.index.intersection(pm_d.index)
        if len(common) < 7:
            st.info("Not enough overlapping data")
            return

        co2_d = co2_d.loc[common]
        pm_d = pm_d.loc[common]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        co2_roll = co2_d.rolling(7, min_periods=1).mean()
        pm_roll = pm_d.rolling(7, min_periods=1).mean()

        fig.add_trace(
            go.Scatter(
                x=co2_roll.index,
                y=co2_roll.values,
                mode="lines",
                name="CO₂ (7d avg)",
                line={"color": COLORS["master"], "width": 2.5},
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=pm_roll.index,
                y=pm_roll.values,
                mode="lines",
                name="Indoor PM2.5 (7d avg)",
                line={"color": COLORS["son"], "width": 2.5},
            ),
            secondary_y=True,
        )

        if out_pm_key in daily:
            out_d = filter_daily(daily[out_pm_key], dr)["mean"]
            out_common = out_d.index.intersection(common)
            if len(out_common) > 7:
                out_roll = out_d.loc[out_common].rolling(7, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=out_roll.index,
                        y=out_roll.values,
                        mode="lines",
                        name="Outdoor PM2.5 (7d avg)",
                        line={"color": COLORS["outdoor"], "width": 2, "dash": "dot"},
                    ),
                    secondary_y=True,
                )

        fig.add_hline(
            y=1000, line_dash="dash", line_color=COLORS["threshold"], opacity=0.5, secondary_y=False
        )
        fig.update_layout(
            **PLOT_LAYOUT, title={"text": "ERV Tradeoff: CO₂ vs PM2.5 (7-day rolling)"}, height=500
        )
        fig.update_yaxes(title_text="CO₂ (ppm)", secondary_y=False)
        fig.update_yaxes(title_text="PM2.5 (μg/m³)", secondary_y=True)
        st.plotly_chart(fig, key="corr_erv")

        rho = co2_d.corr(pm_d, method="spearman")
        st.markdown(
            f"**CO₂ ↔ PM2.5 Spearman ρ = {rho:.2f}** — "
            f"{'Inverse: when CO₂ drops (more ventilation), PM2.5 rises' if rho < -0.1 else 'Weak or positive: ventilation not the main PM2.5 driver' if rho < 0.2 else 'Positive: both driven by same source (e.g., cooking)'}"
        )


def page_voc_nox():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    raw, hourly, daily = get_data()
    dr = sidebar_date_range(raw)

    st.markdown("# VOC & NOX — Air Chemistry")
    st.caption("Volatile organic compounds and nitrogen oxides. Higher = worse air quality.")

    room = st.radio(
        "Room",
        ["master_bedroom", "second_bedroom"],
        horizontal=True,
        format_func=lambda x: "Master" if x == "master_bedroom" else "Son's Room (near kitchen)",
        key="vn_room",
    )

    choice = st.radio(
        "View", ["Indoor vs Outdoor", "Daily Pattern", "Trend"], horizontal=True, key="vn_view"
    )

    if choice == "Indoor vs Outdoor":
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=["VOC Index", "NOX Index"],
        )
        for i, (metric, label) in enumerate([("VOC", "VOC"), ("NOX", "NOX")]):
            in_key = (room, f"Indoor_{metric}")
            out_key = (room, f"Outdoor_{metric}")
            row = i + 1
            if in_key in daily:
                d = filter_daily(daily[in_key], dr)["mean"].rolling(3, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=d.index,
                        y=d.values,
                        mode="lines",
                        name=f"Indoor {label}",
                        line={"color": COLORS["indoor"], "width": 2.5},
                    ),
                    row=row,
                    col=1,
                )
            if out_key in daily:
                d = filter_daily(daily[out_key], dr)["mean"].rolling(3, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=d.index,
                        y=d.values,
                        mode="lines",
                        name=f"Outdoor {label}",
                        line={"color": COLORS["outdoor"], "width": 2, "dash": "dash"},
                    ),
                    row=row,
                    col=1,
                )

        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "VOC & NOX: Indoor vs Outdoor (3-day rolling)"},
            height=550,
            showlegend=True,
        )
        st.plotly_chart(fig, key="vn_compare")

    elif choice == "Daily Pattern":
        sub = raw[
            (raw["Room"] == room) & (raw["Timestamp"] >= dr[0]) & (raw["Timestamp"] < dr[1])
        ].copy()
        sub["hour"] = sub["Timestamp"].dt.hour

        fig = make_subplots(rows=1, cols=2, subplot_titles=["VOC by Hour", "NOX by Hour"])
        for i, metric in enumerate(["Indoor_VOC", "Indoor_NOX"]):
            if metric not in sub.columns:
                continue
            by_hour = sub.groupby("hour")[metric].agg(["mean", "std"]).dropna()
            if by_hour.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=by_hour.index,
                    y=by_hour["mean"],
                    mode="lines+markers",
                    name=metric.replace("Indoor_", ""),
                    line={"color": COLORS["master"] if i == 0 else COLORS["son"], "width": 2.5},
                    marker={"size": 5},
                ),
                row=1,
                col=i + 1,
            )
            fig.add_trace(
                go.Scatter(
                    x=list(by_hour.index) + list(by_hour.index[::-1]),
                    y=list((by_hour["mean"] + by_hour["std"]).values)
                    + list((by_hour["mean"] - by_hour["std"]).values[::-1]),
                    fill="toself",
                    fillcolor="rgba(74,144,217,0.1)" if i == 0 else "rgba(232,116,79,0.1)",
                    line={"width": 0},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=i + 1,
            )

        fig.update_layout(
            **PLOT_LAYOUT,
            title={"text": "VOC & NOX Daily Pattern (mean +/- std)"},
            height=400,
            xaxis={"dtick": 2},
            xaxis2={"dtick": 2},
        )
        st.plotly_chart(fig, key="vn_daily")

    elif choice == "Trend":
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=["VOC Index (7-day rolling)", "NOX Index (7-day rolling)"],
        )
        for i, metric in enumerate(["Indoor_VOC", "Indoor_NOX"]):
            key = (room, metric)
            if key not in daily:
                continue
            d = filter_daily(daily[key], dr)
            r_mean = d["mean"].rolling(7, min_periods=1).mean()
            r_min = d["min"].rolling(7, min_periods=1).min()
            r_max = d["max"].rolling(7, min_periods=1).max()
            color = COLORS["master"] if i == 0 else COLORS["son"]
            hex_c = color
            rgba = f"rgba({int(hex_c[1:3], 16)},{int(hex_c[3:5], 16)},{int(hex_c[5:7], 16)},0.12)"

            fig.add_trace(
                go.Scatter(
                    x=r_max.index,
                    y=r_max.values,
                    mode="lines",
                    line={"width": 0},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=i + 1,
                col=1,
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
                ),
                row=i + 1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=r_mean.index,
                    y=r_mean.values,
                    mode="lines",
                    name=metric.replace("Indoor_", ""),
                    line={"color": color, "width": 2.5},
                ),
                row=i + 1,
                col=1,
            )

        fig.update_layout(**PLOT_LAYOUT, title={"text": "VOC & NOX Trends"}, height=550)
        st.plotly_chart(fig, key="vn_trend")


# ── Navigation ───────────────────────────────────────────────────────────────

pg = st.navigation(
    [
        st.Page(page_overview, title="Overview", icon="📊"),
        st.Page(page_co2_compare, title="CO₂ Compare", icon="🫁"),
        st.Page(page_heatmaps, title="Heatmaps", icon="🗺️"),
        st.Page(page_voc_nox, title="VOC & NOX", icon="🧪"),
        st.Page(page_filter_pm25, title="Filter & PM2.5", icon="🔧"),
        st.Page(page_environment, title="Environment", icon="🏠"),
        st.Page(page_correlations, title="Correlations", icon="🔗"),
    ]
)
pg.run()
