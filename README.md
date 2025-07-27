# HVAC Air Quality Monitoring

Smart filter replacement tracking to prevent asthma triggers before they happen.

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

- **Late February 2025**: HVAC installation completed
- **March 2025**: ERV installation completed
- **June 2025**: Filter upgrade from MERV 8 to MERV 13
- **Current**: Monitoring filter efficiency to optimize replacement schedule

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

## Using Claude Code with Jupyter in VSCode

### Setup

1. Install VSCode extensions:
   - Python
   - Jupyter
   - Claude (by Anthropic)

2. Select Python interpreter:
   - Cmd/Ctrl + Shift + P → "Python: Select Interpreter"
   - Choose the uv virtual environment (`.venv`)

3. Create a new notebook:
```bash
# In your project directory
touch analysis.ipynb
```

### Working with Claude in Notebooks

In VSCode with a Jupyter notebook open:

1. **Use Claude inline**: 
   - Type your question in a markdown cell
   - Select the text and press Cmd/Ctrl + K
   - Ask Claude to analyze or generate code

2. **Generate analysis code**:
   ```python
   # Select this comment and ask Claude:
   # "Load the CSV data I exported from Airthings dashboard and analyze filter efficiency trends"
   ```

3. **Interactive analysis**:
   - Run cells with Shift + Enter
   - Claude can see the output and help iterate

### Example Claude Prompts for Your Analysis

```python
# Cell 1: Ask Claude
# "Load my Airthings CSV export and create a DataFrame with proper datetime index"

# Cell 2: Ask Claude  
# "Calculate daily average PM2.5 and identify days where indoor > outdoor (filter failure)"

# Cell 3: Ask Claude
# "Create a visualization showing filter efficiency degradation since June 2024"

# Cell 4: Ask Claude
# "Predict when filter efficiency will drop below 80% based on current trend"
```

## Key Metrics to Track

### Filter Replacement Triggers
- **Efficiency < 85%**: Start monitoring closely
- **Efficiency < 80%**: Plan replacement within 2 weeks
- **Efficiency < 75%**: Replace immediately
- **Indoor PM2.5 > 12 μg/m³**: Replace regardless of efficiency

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

# Start Jupyter
jupyter notebook

# Open analysis.ipynb in VSCode instead for Claude integration
code analysis.ipynb
```

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

## Safety Alerts

The script will warn you when:
- Filter efficiency drops below 85% AND outdoor PM2.5 > 10 μg/m³
- It's been > 180 days since last filter change
- Indoor air quality exceeds WHO guidelines

## Next Steps

1. Set up data collection on Unifi Gateway
2. Import your historical CSV data
3. Run analysis to establish baseline degradation rate
4. Set up alerts for predictive replacement

Remember: **The goal is to replace filters BEFORE symptoms appear!**

## Need Help?

- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- 🚀 [Quick Start Guide](START_HERE.md) - 30-minute setup
- 🔐 [SSH Setup Guide](ssh_into_uni_fi_cloud_gateway_ultra.md) - Unifi Gateway access
