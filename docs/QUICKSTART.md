# Quick Start Guide

## 1. Local Setup (Your Computer) - 5 minutes

```bash
# Clone or create project directory
mkdir hvac-air-quality && cd hvac-air-quality

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Create pyproject.toml and install dependencies
# Copy the pyproject.toml from artifacts
uv pip install -e .

# Create .gitignore
# Copy the .gitignore from artifacts

# Initialize git (for version control, not required)
git init
git add .
git commit -m "Initial setup"
```

## 2. Unifi Gateway Setup - 10 minutes

```bash
# SSH into your Unifi Gateway
ssh root@[your-gateway-ip]

# Copy and run the setup script
# Copy setup_unifi.sh from artifacts
chmod +x setup_unifi.sh
./setup_unifi.sh

# Edit credentials
vi /data/scripts/.env
# Add your:
# - Airthings client ID & secret
# - AirGradient serial number
# - Google Form ID and field IDs

# Find your AirGradient serial
avahi-browse -t _http._tcp
# Look for "airgradient_XXXXX"

# Test the collector
python3 /data/scripts/collect_air.py
```

## 3. Google Sheets Setup - 10 minutes

1. Create a new Google Form
2. Add these questions (all "Short answer"):
   - Timestamp
   - Indoor PM2.5
   - Outdoor PM2.5
   - Filter Efficiency
   - Indoor CO2
   - Indoor VOC
   - Days Since Install

3. Get the form response URL:
   - Send a test response
   - Go to Form → Responses → View in Sheets
   - Form → Send → Link icon
   - Copy the form ID from URL

4. Get field IDs:
   - Open form in edit mode
   - Right-click → Inspect on each field
   - Find `entry.XXXXXX` in the HTML
   - Update these in `/data/scripts/.env`

## 4. Analysis Setup (Your Computer) - 5 minutes

```bash
# In your project directory
code analysis.ipynb  # Opens in VSCode

# Or use Jupyter directly
jupyter notebook analysis.ipynb
```

### Using Claude in VSCode Notebooks:

1. **Install Claude extension** in VSCode
2. Open the notebook
3. Select any code comment or markdown
4. Press **Cmd/Ctrl + K**
5. Ask Claude to help

Example prompts:
- "Load my Airthings CSV export and show PM2.5 trends"
- "Calculate how many days until filter efficiency drops below 80%"
- "Create a cost analysis comparing different replacement schedules"

## 5. What You'll See

### On Unifi Gateway (every hour):
```
Indoor: 3.2 μg/m³, Outdoor: 18.5 μg/m³, Efficiency: 82.7%
✓ Data sent to Google Sheets at 2025-01-14 10:00:00
```

### In Google Sheets:
A growing dataset with hourly readings that you can chart and analyze

### In Your Analysis:
- Filter efficiency trends
- Predicted replacement dates
- Cost optimization
- Health event correlations

## Key Files Summary

- **collect_air_quality.py** - Main collector (runs on Unifi)
- **analysis.ipynb** - Data analysis (runs on your computer)
- **pyproject.toml** - Python dependencies (using uv)
- **.env** - Your secrets (NEVER commit this!)
- **README.md** - Full documentation

## Troubleshooting

### Can't find AirGradient:
```bash
# On Unifi Gateway
curl http://airgradient_XXXXX.local/measures/current
# Replace XXXXX with your serial
```

### Airthings API errors:
- Check credentials in .env
- Verify device serial number
- API limit is 120 requests/hour

### Google Sheets not updating:
- Verify form ID and field IDs
- Test with manual form submission
- Check Unifi logs: `tail /data/logs/collection.log`

## Success Criteria

You'll know it's working when:
1. ✓ Hourly data appears in Google Sheets
2. ✓ Filter efficiency tracks between 70-95%
3. ✓ You get alerts when efficiency < 85%
4. ✓ You can predict replacement dates

## Remember

**Goal**: Replace filters BEFORE they trigger asthma symptoms!

Current efficiency threshold: 85% (with 80% as absolute minimum)
