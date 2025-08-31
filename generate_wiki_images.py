#!/usr/bin/env python3
"""
Generate key visualizations for wiki from analysis notebook data.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# Create wiki images directory
wiki_images = Path("wiki-repo/images")
wiki_images.mkdir(parents=True, exist_ok=True)

# Load the data (same as in notebook)
print("Loading data...")
df = pd.read_csv(
    "data/raw/airthings-export.csv", delimiter=";", decimal=","  # Replace with your actual filename
)

# Parse and clean data
df["timestamp"] = pd.to_datetime(df["recorded"], format="mixed")
df = df.set_index("timestamp").sort_index()
df = df.drop("recorded", axis=1)

# Convert to numeric and clean column names
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.columns = (
    df.columns.str.replace(" μg/m3", "")
    .str.replace(" ppm", "")
    .str.replace(" %", "")
    .str.replace(" °F", "")
    .str.replace(" ppb", "")
    .str.replace(" inHg", "")
    .str.replace(" pCi/L", "")
)

# Prepare hourly data
df_clean = df.ffill(limit=10)
df_hourly = df_clean.resample("h").mean()

# Event dates - corrected dates based on notebook
event_dates = {
    "HVAC Install": pd.to_datetime("2025-02-25"),
    "ERV Install": pd.to_datetime("2025-03-15"),
    "MERV 13 Upgrade": pd.to_datetime("2025-05-17"),
    "Today": pd.to_datetime("2025-07-27"),  # Fixed date
}

# Generate Figure 1: MERV 13 Impact
print("Generating MERV 13 impact visualization...")
pre_merv13 = df_hourly[
    (df_hourly.index >= event_dates["ERV Install"])
    & (df_hourly.index < event_dates["MERV 13 Upgrade"])
]["PM2_5"]
post_merv13 = df_hourly[df_hourly.index >= event_dates["MERV 13 Upgrade"]]["PM2_5"]

pre_avg = pre_merv13.mean()
post_avg = post_merv13.mean()
improvement = (pre_avg - post_avg) / pre_avg * 100

print(f"Pre-MERV 13 average: {pre_avg:.2f}")
print(f"Post-MERV 13 average: {post_avg:.2f}")
print(f"Improvement: {improvement:.0f}%")

fig1 = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=("Filter Upgrade Impact", "Air Quality Over Time"),
    specs=[[{"type": "bar"}, {"type": "scatter"}]],
)

# Bar chart
fig1.add_trace(
    go.Bar(
        x=["Before MERV 13<br>(Mar-May 17)", "After MERV 13<br>(May 17-Jul)"],
        y=[pre_avg, post_avg],
        marker_color=["lightcoral", "lightgreen"],
        text=[f"{pre_avg:.2f}", f"{post_avg:.2f}"],
        textposition="outside",
        showlegend=False,
    ),
    row=1,
    col=1,
)

# Add improvement annotation
fig1.add_annotation(
    x=0.5,
    y=pre_avg / 2,
    text=f"<b>{improvement:.0f}%<br>Reduction</b>",
    showarrow=False,
    font=dict(size=16),
    bgcolor="yellow",
    bordercolor="black",
    borderwidth=2,
    xref="x",
    yref="y",
)

# Timeline - filter to show only from March onwards
march_onwards = df_hourly[df_hourly.index >= "2025-03-01"]
rolling_avg = march_onwards["PM2_5"].rolling("7D").mean()

# Convert datetime index to string format to avoid scientific notation
x_dates = rolling_avg.index.strftime("%b %d")
fig1.add_trace(
    go.Scatter(
        x=x_dates,
        y=rolling_avg.values,
        mode="lines",
        name="7-day average",
        line=dict(color="darkblue", width=2),
        hovertemplate="%{x}<br>PM2.5: %{y:.2f}<extra></extra>",
    ),
    row=1,
    col=2,
)

# Find the index for MERV 13 upgrade date in string format
merv13_dates = pd.to_datetime(rolling_avg.index).date
upgrade_date = event_dates["MERV 13 Upgrade"].date()
merv13_idx = (merv13_dates == upgrade_date).argmax()
merv13_label = x_dates[merv13_idx] if merv13_idx < len(x_dates) else None

if merv13_label:
    # Add vertical line at MERV 13 upgrade
    fig1.add_shape(
        type="line",
        x0=merv13_label,
        x1=merv13_label,
        y0=0,
        y1=3.5,
        line=dict(color="red", width=2, dash="dash"),
        row=1,
        col=2,
    )

    # Add MERV 13 annotation
    fig1.add_annotation(
        x=merv13_label,
        y=2.5,
        text="MERV 13<br>Upgrade",
        showarrow=True,
        arrowhead=2,
        ax=30,
        ay=-30,
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
        row=1,
        col=2,
    )

fig1.update_layout(
    title_text="Your MERV 13 Upgrade Was a Huge Success!",
    title_font_size=20,
    height=500,
    showlegend=False,
)

# Fix x-axis formatting for timeline - show fewer labels
num_ticks = 5
tick_step = len(x_dates) // num_ticks
fig1.update_xaxes(
    title_text="",
    tickmode="array",
    tickvals=x_dates[::tick_step],
    ticktext=x_dates[::tick_step],
    tickangle=-45,
    row=1,
    col=2,
)

fig1.update_yaxes(title_text="Indoor PM2.5 (μg/m³)", row=1, col=1)
fig1.update_yaxes(title_text="PM2.5 (μg/m³)", row=1, col=2)

fig1.write_image(str(wiki_images / "merv13_impact.png"))
print(f"Saved: {wiki_images / 'merv13_impact.png'}")

# Generate Figure 2: Cost Comparison
print("Generating cost comparison...")
filter_cost = 260
worst_case = filter_cost * 4
best_case = filter_cost * 1
your_cost = filter_cost * 0.5

fig2 = go.Figure()

scenarios = [
    "Manufacturer Worst Case<br>(Replace every 3 months)",
    "Manufacturer Best Case<br>(Replace every 12 months)",
    "Your Data-Driven Approach<br>(Replace when efficiency drops)",
]
costs = [worst_case, best_case, your_cost]
colors = ["red", "orange", "green"]

fig2.add_trace(
    go.Bar(
        x=scenarios,
        y=costs,
        marker_color=colors,
        text=[f"${int(cost)}/year" for cost in costs],
        textposition="outside",
        textfont=dict(size=16, color="black"),
    )
)

fig2.update_layout(
    title="The Real Value: Knowing WHEN to Replace",
    yaxis_title="Annual Filter Cost ($)",
    height=500,
    showlegend=False,
    yaxis=dict(range=[0, 1100]),
)

fig2.write_image(str(wiki_images / "cost_comparison.png"))
print(f"Saved: {wiki_images / 'cost_comparison.png'}")

# Generate Figure 3: Efficiency Chaos Example
print("Generating efficiency chaos visualization...")
real_data = pd.DataFrame(
    {
        "Time": [
            "13:27",
            "15:23",
            "15:28",
            "15:30",
            "15:35",
            "15:40",
            "15:45",
            "15:50",
            "15:55",
            "16:00",
            "16:05",
            "16:10",
            "16:15",
            "16:20",
            "16:25",
            "16:30",
        ],
        "Indoor": [0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 3, 1, 2, 1, 0],
        "Outdoor": [
            3.15,
            3.68,
            3.23,
            3.68,
            3.45,
            3.47,
            3.36,
            3.43,
            3.47,
            3.74,
            3.31,
            3.29,
            2.92,
            3.05,
            3.17,
            2.6,
        ],
        "Traditional_Eff": [
            100,
            100,
            100,
            100,
            100,
            71.2,
            100,
            70.8,
            100,
            100,
            69.8,
            8.8,
            65.8,
            34.4,
            68.5,
            100,
        ],
    }
)

# Create numeric index for proper x-axis
real_data["x_idx"] = range(len(real_data))

fig3 = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=(
        "Traditional Efficiency Calculation is Nonsense at Low PM2.5",
        "Focus on Absolute Values, Not Percentages",
    ),
    specs=[[{"type": "scatter"}], [{"secondary_y": True}]],
    row_heights=[0.5, 0.5],
    vertical_spacing=0.15,
)

# Efficiency chaos
fig3.add_trace(
    go.Scatter(
        x=real_data["x_idx"],
        y=real_data["Traditional_Eff"],
        mode="lines+markers",
        line=dict(color="darkblue", width=2),
        marker=dict(size=8),
        name="Traditional Efficiency",
        showlegend=False,
        customdata=real_data["Time"],
        hovertemplate="Time: %{customdata}<br>Efficiency: %{y}%<extra></extra>",
    ),
    row=1,
    col=1,
)

# Add annotations for crazy readings
fig3.add_annotation(
    x=real_data[real_data["Traditional_Eff"] == 8.8]["x_idx"].values[0],
    y=8.8,
    text="8.8%?!",
    showarrow=True,
    arrowhead=2,
    ay=30,
    bgcolor="red",
    font=dict(color="white"),
    row=1,
    col=1,
)

# Absolute values
fig3.add_trace(
    go.Scatter(
        x=real_data["x_idx"],
        y=real_data["Outdoor"],
        mode="lines+markers",
        line=dict(color="blue", width=2),
        marker=dict(size=8),
        name="Outdoor PM2.5",
        customdata=real_data["Time"],
        hovertemplate="Time: %{customdata}<br>Outdoor: %{y}<extra></extra>",
    ),
    row=2,
    col=1,
)

fig3.add_trace(
    go.Scatter(
        x=real_data["x_idx"],
        y=real_data["Indoor"],
        mode="lines+markers",
        line=dict(color="green", width=2),
        marker=dict(size=8, symbol="square"),
        name="Indoor PM2.5",
        customdata=real_data["Time"],
        hovertemplate="Time: %{customdata}<br>Indoor: %{y}<extra></extra>",
    ),
    row=2,
    col=1,
    secondary_y=True,
)

# Update x-axis to show selected time labels
fig3.update_xaxes(
    tickmode="array",
    tickvals=[0, 4, 8, 12, 15],
    ticktext=["13:27", "15:35", "15:55", "16:15", "16:30"],
    title_text="Time (July 26, 2025)",
    row=2,
    col=1,
)

fig3.update_xaxes(
    tickmode="array",
    tickvals=[0, 4, 8, 12, 15],
    ticktext=["13:27", "15:35", "15:55", "16:15", "16:30"],
    row=1,
    col=1,
)

fig3.update_yaxes(title_text="Efficiency (%)", row=1, col=1, range=[0, 110])
fig3.update_yaxes(title_text="Outdoor PM2.5 (μg/m³)", row=2, col=1, range=[0, 5])
fig3.update_yaxes(title_text="Indoor PM2.5 (μg/m³)", row=2, col=1, secondary_y=True, range=[0, 5])

fig3.update_layout(height=800, title="Why You Need Outdoor Monitoring", showlegend=True)
fig3.write_image(str(wiki_images / "efficiency_chaos.png"))
print(f"Saved: {wiki_images / 'efficiency_chaos.png'}")

# Generate Figure 4: Comprehensive Timeline
print("Generating comprehensive timeline visualization...")
fig4 = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=(
        "Your Air Quality Timeline - The MERV 13 Difference",
        "Ventilation Performance - CO2 Levels",
    ),
    shared_xaxes=True,
    vertical_spacing=0.12,
    row_heights=[0.6, 0.4],
)

# Filter data from February onwards
timeline_data = df_hourly[df_hourly.index >= "2025-02-01"]

# Convert to string dates for proper display
timeline_dates = timeline_data.index.strftime("%b %d")

# PM2.5 plot
fig4.add_trace(
    go.Scatter(
        x=timeline_dates,
        y=timeline_data["PM2_5"].rolling("24h").mean().values,
        mode="lines",
        name="PM2.5 (24h avg)",
        line=dict(color="blue", width=2),
    ),
    row=1,
    col=1,
)

# CO2 plot
fig4.add_trace(
    go.Scatter(
        x=timeline_dates,
        y=timeline_data["CO2"].rolling("24h").mean().values,
        mode="lines",
        name="CO2 (24h avg)",
        line=dict(color="green", width=2),
        yaxis="y2",
    ),
    row=2,
    col=1,
)

# Don't add WHO guideline - it's at 15 and our data is 0-3, makes chart unreadable

# Add pre/post MERV 13 average lines
pre_avg = 1.30
post_avg = 0.38
fig4.add_hline(
    y=pre_avg,
    line_color="red",
    line_width=2,
    annotation_text=f"Pre-MERV 13: {pre_avg}",
    annotation_position="right",
    row=1,
    col=1,
)
fig4.add_hline(
    y=post_avg,
    line_color="green",
    line_width=2,
    annotation_text=f"Post-MERV 13: {post_avg}",
    annotation_position="right",
    row=1,
    col=1,
)

# Add CO2 reference levels
fig4.add_hline(
    y=800,
    line_dash="dash",
    line_color="green",
    annotation_text="Excellent ventilation (<800 ppm)",
    annotation_position="right",
    row=2,
    col=1,
)
fig4.add_hline(
    y=1000,
    line_dash="dash",
    line_color="orange",
    annotation_text="Cognitive impact (>1000 ppm)",
    annotation_position="right",
    row=2,
    col=1,
)

# Add event lines for MERV 13 upgrade
merv13_date = event_dates["MERV 13 Upgrade"]
merv13_idx = (timeline_data.index.date == merv13_date.date()).argmax()
if merv13_idx < len(timeline_dates):
    merv13_label = timeline_dates[merv13_idx]
    fig4.add_shape(
        type="line",
        x0=merv13_label,
        x1=merv13_label,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color="green", width=2, dash="dash"),
    )
    fig4.add_annotation(
        x=merv13_label,
        y=0.5,
        text="MERV 13<br>Upgrade",
        showarrow=False,
        yref="paper",
        xref="x",
        bgcolor="yellow",
        bordercolor="green",
        borderwidth=1,
    )

# Set sparse x-axis labels
num_ticks = 6
tick_step = len(timeline_dates) // num_ticks
fig4.update_xaxes(
    title_text="Date",
    tickmode="array",
    tickvals=timeline_dates[::tick_step],
    ticktext=timeline_dates[::tick_step],
    tickangle=-45,
    row=2,
    col=1,
)
fig4.update_yaxes(title_text="PM2.5 (μg/m³)", row=1, col=1, range=[0, 3.5])
fig4.update_yaxes(title_text="CO2 (ppm)", row=2, col=1)

# Add vacation ERV issue annotation
vacation_mid = pd.to_datetime("2025-06-17")
vacation_idx = (timeline_data.index.date == vacation_mid.date()).argmax()
if vacation_idx < len(timeline_dates):
    vacation_label = timeline_dates[vacation_idx]
    fig4.add_annotation(
        x=vacation_label,
        y=850,
        text="Vacation ERV Issue<br>(System restart needed)",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        bgcolor="yellow",
        bordercolor="orange",
        borderwidth=1,
        row=2,
        col=1,
    )

fig4.update_layout(
    title="Your Air Quality Journey: MERV 13 Success Story",
    height=700,
    showlegend=True,
    plot_bgcolor="rgba(240,240,240,0.5)",
    paper_bgcolor="white",
)

fig4.write_image(str(wiki_images / "pm25_timeline.png"))
print(f"Saved: {wiki_images / 'pm25_timeline.png'}")

# Generate Figure 5: Filter Performance
print("Generating filter performance visualization...")

# This should show filter efficiency, not just PM2.5
# But since we don't have outdoor data for most of the period,
# we'll show PM2.5 levels with context about what happened

post_merv13_data = df_hourly[df_hourly.index >= event_dates["MERV 13 Upgrade"]]
rolling_pm25 = post_merv13_data["PM2_5"].rolling("7D").mean()

fig5 = go.Figure()

# Convert dates to strings
pm25_dates = rolling_pm25.index.strftime("%b %d")

# Add rolling average
fig5.add_trace(
    go.Scatter(
        x=pm25_dates,
        y=rolling_pm25.values,
        mode="lines",
        name="7-day Average Indoor PM2.5",
        line=dict(color="blue", width=2),
    )
)

# Mark vacation/ERV failure period with correct dates
vacation_start = pd.to_datetime("2025-06-10")
vacation_end = pd.to_datetime("2025-06-24")

# Find string dates for vacation period
vacation_start_idx = (rolling_pm25.index.date >= vacation_start.date()).argmax()
vacation_end_idx = (rolling_pm25.index.date > vacation_end.date()).argmax()
if vacation_end_idx == 0:  # If vacation_end is after all data
    vacation_end_idx = len(pm25_dates) - 1

# ERV failure continued past vacation
erv_fixed = pd.to_datetime("2025-07-10")  # Fixed July 10th
erv_fixed_idx = (rolling_pm25.index.date >= erv_fixed.date()).argmax()

if vacation_start_idx < len(pm25_dates) and vacation_end_idx <= len(pm25_dates):
    vacation_start_label = pm25_dates[vacation_start_idx]
    vacation_end_label = pm25_dates[vacation_end_idx]
    erv_fixed_label = (
        pm25_dates[erv_fixed_idx] if erv_fixed_idx < len(pm25_dates) else pm25_dates[-1]
    )

    # Add shaded rectangle for vacation period
    fig5.add_shape(
        type="rect",
        x0=vacation_start_label,
        x1=vacation_end_label,
        y0=0,
        y1=1,
        fillcolor="yellow",
        opacity=0.3,
        layer="below",
        line_width=0,
        yref="paper",
    )

    # Add shaded rectangle for ERV failure period (vacation end to early July)
    fig5.add_shape(
        type="rect",
        x0=vacation_end_label,
        x1=erv_fixed_label,
        y0=0,
        y1=1,
        fillcolor="red",
        opacity=0.2,
        layer="below",
        line_width=0,
        yref="paper",
    )

    # Add annotations
    fig5.add_annotation(
        x=vacation_start_label,
        y=0.95,
        text="Vacation<br>(No occupancy)",
        showarrow=False,
        yref="paper",
    )

    fig5.add_annotation(
        x=erv_fixed_label,
        y=0.90,
        text="ERV Fixed<br>July 10",
        showarrow=True,
        ay=-30,
        yref="paper",
        bgcolor="lightgreen",
        bordercolor="green",
        borderwidth=1,
    )

# Set sparse x-axis labels
num_ticks = 5
tick_step = len(pm25_dates) // num_ticks
fig5.update_xaxes(
    tickmode="array",
    tickvals=pm25_dates[::tick_step],
    ticktext=pm25_dates[::tick_step],
    tickangle=-45,
)

fig5.update_layout(
    title="Indoor Air Quality: Context Matters for Analysis",
    xaxis_title="Date",
    yaxis_title="Indoor PM2.5 (μg/m³)",
    height=400,
    showlegend=True,
)

fig5.write_image(str(wiki_images / "filter_performance.png"))
print(f"Saved: {wiki_images / 'filter_performance.png'}")

print("\nAll images generated successfully!")
print(f"Images saved to: {wiki_images}")
print("\nNow commit these images to the wiki repository for display.")
