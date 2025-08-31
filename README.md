# HVAC Air Quality Monitoring

Multi-sensor smart filter replacement tracking to prevent asthma triggers before they happen.

📚 **[View the Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki)** for detailed documentation, analysis results, and hardware setup guides.

## 🚨 Latest Updates (August 30, 2025)

- ✅ **Data collection restored** after 22-day outage (cron job was missing!)
- ✅ **Multi-sensor support deployed**: Now tracking master bedroom (Airthings) and second bedroom (AirGradient) separately
- ✅ **Switched to Google Sheets API**: Better data structure with room identification
- ✅ **New filter installed Aug 29**: Showing excellent performance (85-100% efficiency)

## Quick Setup with UV

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and virtual environment
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Create .env file
cat > .env << EOF
AIRTHINGS_CLIENT_ID=your_client_id
AIRTHINGS_CLIENT_SECRET=your_secret
AIRTHINGS_DEVICE_SERIAL=your_serial
EOF
```

## Project Timeline

- **February 2025**: HVAC installation completed
- **March 2025**: ERV installation completed
- **May 17, 2025**: Filter upgrade to MERV 13 (both HVAC and ERV)
- **Current**: 70+ days of excellent performance, monitoring for data-driven replacement

## Running on Unifi Gateway

> **Having issues?** Check the [🔧 Troubleshooting Guide](TROUBLESHOOTING.md) for common problems and solutions.

1. SSH into your Unifi Cloud Gateway Ultra:
```bash
ssh root@[your-gateway-ip]
```

2. Copy the setup script and run it:
```bash
scp collect_air_quality.py setup_unifi.sh root@[gateway-ip]:/data/scripts/
ssh root@[gateway-ip]
cd /data/scripts
./setup_unifi.sh
```

3. The setup script will:
   - Install Python dependencies
   - Create .env template
   - Set up data collection every 5 minutes
   - Create log directories

4. Edit your credentials:
```bash
vi /data/scripts/.env
```

5. Data will be collected every 5 minutes to capture:
   - Cooking events (PM2.5 spikes)
   - Shower humidity changes
   - HVAC cycling patterns
   - Cleaning activities
   - Real-time filter efficiency

## Google Sheets Setup

1. Create a Google Form with these fields:
   - Timestamp (Short answer)
   - Indoor PM2.5 (Short answer)
   - Outdoor PM2.5 (Short answer)
   - Filter Efficiency (Short answer)
   - Indoor CO2 (Short answer)
   - Indoor VOC (Short answer)
   - Days Since Install (Short answer)

2. Get the form response URL and field IDs:
   - Fill out the form once
   - Right-click → Inspect on each field
   - Find the `entry.XXXXXX` IDs
   - Update `FORM_FIELD_MAPPING` in the script

3. Link form to a Google Sheet for automatic data collection

## Working with Jupyter Notebooks and Claude Code

### What Claude Code Can Do
- ✅ Read and edit notebook cells
- ✅ Write analysis code for you
- ✅ See cell outputs (text/numbers)
- ❌ Cannot execute cells (you run them)
- ❌ Cannot see Plotly visualizations (screenshot and share)

### Workflow Example
```bash
# 1. Open notebook with Claude Code
code analysis.ipynb

# 2. Ask Claude to write analysis code
"Load the Airthings CSV and calculate PM2.5 averages"

# 3. You execute the cells manually
# 4. For visualizations: Take screenshot → Share with Claude
```

### Tips
- Claude Code can update multiple cells at once
- Export Plotly charts as PNG for Claude to analyze
- Use `fig.write_image()` to save charts Claude can read later

## Key Metrics to Track

### Filter Replacement Triggers
- **Efficiency < 85%**: Start monitoring closely
- **Efficiency < 80%**: Plan replacement within 2 weeks
- **Indoor PM2.5 > 5 μg/m³ consistently**: Consider replacement
- **Indoor PM2.5 > 12 μg/m³**: Replace immediately (WHO guideline)

### Current Performance (July 2025)
- **Filter age**: 70 days since MERV 13 installation (May 17)
- **PM2.5 reduction**: 71% vs pre-MERV 13 period
- **Indoor PM2.5**: 0.38 μg/m³ average post-MERV 13
- **Cost projection**: $130/year (vs $260-$1040/year without data)

### Health Correlation
Track these events in your spreadsheet:
- Asthma symptoms (wife/son)
- Inhaler usage frequency
- Sleep quality changes
- Allergy flare-ups

## Privacy Considerations

The Jupyter notebook analysis can reveal sensitive information about your household:
- Daily activity patterns (wake/sleep times)
- Occupancy schedules (when you're home)
- Cooking habits and meal times
- Weekend vs weekday routines

**For public sharing:** Use `analysis.ipynb` with general insights only.

**For private analysis:** Create `local-analysis.ipynb` (gitignored) for detailed pattern analysis:
```bash
cp local-analysis-template.ipynb local-analysis.ipynb
```

This keeps your personal patterns private while sharing useful insights with the community.

## Local Analysis (Your Computer)

```bash
# Activate environment
source .venv/bin/activate

# Open analysis notebook in VSCode for Claude integration
code analysis.ipynb
```

### Available Analysis Notebooks
- `analysis.ipynb` - Main analysis notebook with 6 months of historical data
- `local-analysis-template.ipynb` - Template for private household pattern analysis

📊 **[See Analysis Results](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/Analysis-Results)** in the wiki for key findings and visualizations.

## Project Structure

```
hvac-air-quality/
├── collect_air_quality.py   # Runs on Unifi Gateway
├── analysis.ipynb           # Local analysis with Claude
├── pyproject.toml          # UV package management
├── .env                    # Your secrets (never commit!)
├── README.md               # This file
└── data/
    ├── airthings_export.csv  # Your manual export
    └── filter_events.csv     # Track replacements & symptoms
```


## Why Outdoor Monitoring Matters

Without outdoor PM2.5 data, you can't calculate true filter efficiency:
- **Filter Efficiency = (Outdoor - Indoor) / Outdoor × 100%**
- **Airthings limitation**: Only whole numbers (0, 1, 2, 3...) for PM2.5
- Indoor "0" → 100% efficiency (meaningless!)
- Indoor "1" vs "0" → Efficiency swings from 70% to 100%
- **Solution**: AirGradient provides 0.01 μg/m³ precision

## Current Status (July 2025)

### What's Working
1. ✅ Unifi Gateway collecting data every 5 minutes
2. ✅ 6 months of Airthings data analyzed
3. ✅ AirGradient outdoor sensor installed (July 26)
4. ✅ Logging to Google Sheets for tracking

### Recent Discovery
July 26 data revealed efficiency calculations are **meaningless** at low PM2.5:
- Efficiency swings from 8.8% to 100% in minutes
- Same filter, different readings due to rounding
- Need 30+ days of outdoor data to establish patterns

### Next Steps
- Collect outdoor baseline for your area
- Develop thresholds based on absolute values
- Build alerts (not percentages!) for replacement

Remember: **With Airthings' whole number precision, percentage-based efficiency is useless!**

## Documentation

### 📚 [GitHub Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki)
- [Hardware Setup](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/Hardware-Setup) - Airthings + AirGradient configuration
- [Data Collection](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/Data-Collection) - Automated monitoring setup
- [Analysis Results](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/Analysis-Results) - Key findings from 6 months of data
- [Analysis Techniques](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/Analysis-Techniques) - Data science methods used

### 🛠️ Setup Guides
- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- 🚀 [Quick Start Guide](START_HERE.md) - 30-minute setup
- 🔐 [SSH Setup Guide](ssh_into_uni_fi_cloud_gateway_ultra.md) - Unifi Gateway access
- 📊 [Google Sheets Setup](docs/google-form-setup.md) - Form-based data logging
