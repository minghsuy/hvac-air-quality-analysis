{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# HVAC & ERV Investment Analysis\n",
    "\n",
    "This notebook analyzes the air quality improvements from HVAC and ERV installation using Airthings View Plus data."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import plotly.graph_objects as go\n",
    "import plotly.express as px\n",
    "from plotly.subplots import make_subplots\n",
    "import json\n",
    "from pathlib import Path\n",
    "import sys\n",
    "sys.path.append('..')\n",
    "from src.analyze_data import AirQualityAnalyzer\n",
    "\n",
    "# Set style\n",
    "plt.style.use('seaborn-v0_8-darkgrid')\n",
    "sns.set_palette('husl')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Load and Prepare Data"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Initialize analyzer\n",
    "analyzer = AirQualityAnalyzer()\n",
    "\n",
    "# Load data\n",
    "data = analyzer.load_sensor_data('../data/raw')\n",
    "analyzer.add_phase_labels()\n",
    "\n",
    "# Display basic info\n",
    "print(f\"Data shape: {data.shape}\")\n",
    "print(f\"\\nColumns: {list(data.columns)}\")\n",
    "print(f\"\\nDate range: {data.index.min()} to {data.index.max()}\")\n",
    "print(f\"\\nPhases: {data['phase'].value_counts().sort_index()}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Air Quality Overview"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create interactive plot with Plotly\n",
    "metrics = ['pm25', 'pm1', 'co2', 'voc', 'humidity', 'temp']\n",
    "available_metrics = [m for m in metrics if m in data.columns]\n",
    "\n",
    "fig = make_subplots(\n",
    "    rows=len(available_metrics), \n",
    "    cols=1,\n",
    "    subplot_titles=[m.upper() for m in available_metrics],\n",
    "    vertical_spacing=0.05\n",
    ")\n",
    "\n",
    "for i, metric in enumerate(available_metrics, 1):\n",
    "    # Add raw data\n",
    "    fig.add_trace(\n",
    "        go.Scatter(\n",
    "            x=data.index, \n",
    "            y=data[metric],\n",
    "            mode='lines',\n",
    "            name=f'{metric} (raw)',\n",
    "            opacity=0.3,\n",
    "            showlegend=(i==1)\n",
    "        ),\n",
    "        row=i, col=1\n",
    "    )\n",
    "    \n",
    "    # Add rolling average\n",
    "    rolling = data[metric].rolling('7D').mean()\n",
    "    fig.add_trace(\n",
    "        go.Scatter(\n",
    "            x=data.index,\n",
    "            y=rolling,\n",
    "            mode='lines',\n",
    "            name=f'{metric} (7-day avg)',\n",
    "            showlegend=(i==1)\n",
    "        ),\n",
    "        row=i, col=1\n",
    "    )\n",
    "    \n",
    "# Add phase markers\n",
    "for event, date in analyzer.timeline.items():\n",
    "    fig.add_vline(\n",
    "        x=date, \n",
    "        line_dash=\"dash\", \n",
    "        line_color=\"red\",\n",
    "        annotation_text=event.replace('_', ' ').title(),\n",
    "        annotation_position=\"top\"\n",
    "    )\n",
    "\n",
    "fig.update_layout(\n",
    "    height=300*len(available_metrics),\n",
    "    title_text=\"Air Quality Metrics Timeline\",\n",
    "    showlegend=True\n",
    ")\n",
    "\n",
    "fig.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Statistical Analysis by Phase"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Calculate improvements\n",
    "improvements = analyzer.calculate_improvements()\n",
    "\n",
    "# Create comparison plots\n",
    "fig, axes = plt.subplots(2, 3, figsize=(15, 10))\n",
    "axes = axes.flatten()\n",
    "\n",
    "for i, (metric, stats) in enumerate(improvements.items()):\n",
    "    if i < len(axes):\n",
    "        ax = axes[i]\n",
    "        stats['mean'].plot(kind='bar', ax=ax, yerr=stats['std'])\n",
    "        ax.set_title(f'{metric.upper()} by Phase')\n",
    "        ax.set_xlabel('Phase')\n",
    "        ax.set_ylabel(metric)\n",
    "        ax.tick_params(axis='x', rotation=45)\n",
    "\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. PM2.5 Reduction Analysis"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "if 'pm25' in data.columns:\n",
    "    # Calculate PM2.5 statistics by phase\n",
    "    pm25_stats = data.groupby('phase')['pm25'].agg(['mean', 'std', 'min', 'max', 'count'])\n",
    "    \n",
    "    # Calculate percentage improvements\n",
    "    baseline_pm25 = pm25_stats.loc['baseline', 'mean']\n",
    "    pm25_stats['reduction_%'] = ((baseline_pm25 - pm25_stats['mean']) / baseline_pm25 * 100)\n",
    "    \n",
    "    print(\"PM2.5 Statistics by Phase:\")\n",
    "    print(pm25_stats)\n",
    "    \n",
    "    # Create box plot\n",
    "    plt.figure(figsize=(10, 6))\n",
    "    data.boxplot(column='pm25', by='phase', ax=plt.gca())\n",
    "    plt.title('PM2.5 Distribution by Phase')\n",
    "    plt.suptitle('')  # Remove default title\n",
    "    plt.ylabel('PM2.5 (μg/m³)')\n",
    "    plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 5. CO2 and Cognitive Performance"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "if 'co2' in data.columns:\n",
    "    # Analyze CO2 levels and estimated cognitive impact\n",
    "    co2_stats = data.groupby('phase')['co2'].agg(['mean', 'std', 'min', 'max'])\n",
    "    \n",
    "    # Cognitive performance estimation (based on research)\n",
    "    # ~15% decrease per 400ppm above 600ppm baseline\n",
    "    baseline_cognitive = 100  # 100% at 600ppm\n",
    "    co2_stats['cognitive_performance_%'] = baseline_cognitive - ((co2_stats['mean'] - 600) / 400 * 15)\n",
    "    \n",
    "    print(\"CO2 and Estimated Cognitive Performance:\")\n",
    "    print(co2_stats)\n",
    "    \n",
    "    # Time of day analysis\n",
    "    data['hour'] = data.index.hour\n",
    "    hourly_co2 = data.groupby(['phase', 'hour'])['co2'].mean().unstack(0)\n",
    "    \n",
    "    plt.figure(figsize=(12, 6))\n",
    "    for phase in hourly_co2.columns:\n",
    "        plt.plot(hourly_co2.index, hourly_co2[phase], label=phase, marker='o')\n",
    "    \n",
    "    plt.xlabel('Hour of Day')\n",
    "    plt.ylabel('Average CO2 (ppm)')\n",
    "    plt.title('CO2 Levels by Hour of Day and Phase')\n",
    "    plt.legend()\n",
    "    plt.grid(True, alpha=0.3)\n",
    "    plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 6. Filter Upgrade Impact (MERV 8 to MERV 13)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Compare before and after filter upgrade\n",
    "if 'pm25' in data.columns and 'pm1' in data.columns:\n",
    "    # Get data around filter upgrade\n",
    "    filter_date = analyzer.timeline['filter_upgrade']\n",
    "    before_filter = data[(data.index >= filter_date - pd.Timedelta(days=30)) & \n",
    "                        (data.index < filter_date)]\n",
    "    after_filter = data[(data.index >= filter_date) & \n",
    "                       (data.index < filter_date + pd.Timedelta(days=30))]\n",
    "    \n",
    "    # Statistical comparison\n",
    "    print(\"Filter Upgrade Impact (30 days before vs after):\")\n",
    "    print(\"\\nBefore (MERV 8):\")\n",
    "    print(before_filter[['pm25', 'pm1']].describe())\n",
    "    print(\"\\nAfter (MERV 13):\")\n",
    "    print(after_filter[['pm25', 'pm1']].describe())\n",
    "    \n",
    "    # Calculate improvement\n",
    "    pm25_reduction = ((before_filter['pm25'].mean() - after_filter['pm25'].mean()) / \n",
    "                     before_filter['pm25'].mean() * 100)\n",
    "    pm1_reduction = ((before_filter['pm1'].mean() - after_filter['pm1'].mean()) / \n",
    "                    before_filter['pm1'].mean() * 100)\n",
    "    \n",
    "    print(f\"\\nPM2.5 Reduction: {pm25_reduction:.1f}%\")\n",
    "    print(f\"PM1.0 Reduction: {pm1_reduction:.1f}%\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 7. ROI Calculation"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Estimate costs (adjust these to your actual costs)\n",
    "costs = {\n",
    "    'hvac_system': 12000,  # Total HVAC cost\n",
    "    'erv_system': 3500,    # ERV installation\n",
    "    'filter_upgrade_annual': 200  # Additional cost for MERV 13 vs MERV 8\n",
    "}\n",
    "\n",
    "# Estimate benefits\n",
    "benefits = {\n",
    "    'energy_savings_monthly': 50,  # From improved efficiency\n",
    "    'health_cost_reduction_annual': 1000,  # Reduced allergies, better sleep\n",
    "    'productivity_gain_monthly': 200  # From better CO2 levels\n",
    "}\n",
    "\n",
    "# Calculate payback period\n",
    "total_cost = costs['hvac_system'] + costs['erv_system']\n",
    "monthly_benefits = (benefits['energy_savings_monthly'] + \n",
    "                   benefits['productivity_gain_monthly'] + \n",
    "                   benefits['health_cost_reduction_annual']/12)\n",
    "\n",
    "payback_months = total_cost / monthly_benefits\n",
    "payback_years = payback_months / 12\n",
    "\n",
    "print(\"ROI Analysis:\")\n",
    "print(f\"\\nTotal Investment: ${total_cost:,.2f}\")\n",
    "print(f\"Monthly Benefits: ${monthly_benefits:,.2f}\")\n",
    "print(f\"Payback Period: {payback_years:.1f} years\")\n",
    "\n",
    "# Create ROI visualization\n",
    "months = np.arange(0, 120)  # 10 years\n",
    "cumulative_cost = total_cost + (months * costs['filter_upgrade_annual']/12)\n",
    "cumulative_benefits = months * monthly_benefits\n",
    "net_value = cumulative_benefits - cumulative_cost\n",
    "\n",
    "plt.figure(figsize=(10, 6))\n",
    "plt.plot(months/12, cumulative_cost/1000, label='Cumulative Cost', linestyle='--')\n",
    "plt.plot(months/12, cumulative_benefits/1000, label='Cumulative Benefits')\n",
    "plt.plot(months/12, net_value/1000, label='Net Value', linewidth=3)\n",
    "plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)\n",
    "plt.xlabel('Years')\n",
    "plt.ylabel('Value ($1000s)')\n",
    "plt.title('HVAC/ERV Investment ROI Over Time')\n",
    "plt.legend()\n",
    "plt.grid(True, alpha=0.3)\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 8. Health Impact Summary"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create health impact summary\n",
    "health_metrics = {\n",
    "    'PM2.5 Exposure': {\n",
    "        'WHO Guideline': 15,  # μg/m³ (24-hour)\n",
    "        'Baseline': pm25_stats.loc['baseline', 'mean'] if 'pm25' in data.columns else None,\n",
    "        'Current': pm25_stats.loc['merv13', 'mean'] if 'pm25' in data.columns and 'merv13' in pm25_stats.index else None\n",
    "    },\n",
    "    'CO2 Levels': {\n",
    "        'Optimal': 600,  # ppm\n",
    "        'Baseline': co2_stats.loc['baseline', 'mean'] if 'co2' in data.columns else None,\n",
    "        'Current': co2_stats.loc['merv13', 'mean'] if 'co2' in data.columns and 'merv13' in co2_stats.index else None\n",
    "    }\n",
    "}\n",
    "\n",
    "print(\"Health Impact Summary:\")\n",
    "for metric, values in health_metrics.items():\n",
    "    print(f\"\\n{metric}:\")\n",
    "    for key, value in values.items():\n",
    "        if value is not None:\n",
    "            print(f\"  {key}: {value:.1f}\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}