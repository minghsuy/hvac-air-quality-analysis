# 🚀 Start Here - HVAC Filter Monitoring Project

## Your Situation
- **Timeline**: HVAC (Feb 2025) → ERV (Mar 2025) → MERV 13 (Jun 2025)
- **Goal**: Replace filters BEFORE asthma symptoms, not on schedule
- **Method**: Compare indoor (Airthings) vs outdoor (AirGradient) PM2.5

## What This Does
Every hour, your Unifi Gateway will:
1. Get indoor air quality from Airthings API
2. Get outdoor air quality from local AirGradient sensor (using compensated values)
3. Calculate filter efficiency: (Outdoor - Indoor) / Outdoor × 100%
4. Log to Google Sheets (13 sensor readings)
5. Alert you when efficiency < 85%

## Filter Tracking Strategy
Instead of logging "days since installation" every hour (wasteful!), we:
1. Track filter changes in a separate sheet tab manually
2. Calculate days/costs in analysis dashboards
3. Keep hourly data focused on sensor readings only

## Quick Start (30 minutes total)

### Step 1: Local Setup (5 min)
```bash
# Install uv and create environment
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .

# Create your .env from template
cp .env.example .env
# Edit .env with your actual values
```

### Step 2: Create Google Form (10 min)
Create form with 13 fields (see GOOGLE_FORM_SETUP.md):
- Timestamp, Indoor/Outdoor PM2.5, Efficiency
- Indoor/Outdoor: CO2, VOC, Temp, Humidity
- Outdoor: NOX

### Step 3: Unifi Setup (10 min)
```bash
# SSH to gateway
ssh root@your-gateway-ip

# Run setup
./setup_unifi.sh

# Edit credentials
vi /data/scripts/.env
```

### Step 4: Test (5 min)
```bash
# On Unifi
python3 /data/scripts/collect_air.py

# Should see:
# Indoor: 3.2 μg/m³, Outdoor: 18.5 μg/m³ (compensated), Efficiency: 82.7%
```

## Key Thresholds

- **Efficiency < 90%**: Start watching closely
- **Efficiency < 85%**: Get alerts, plan replacement  
- **Efficiency < 80%**: Replace within days
- **Indoor PM2.5 > 12**: Replace immediately

## Cost Tracking

Track filter changes manually in sheets:
```
Date       | Type | Brand   | MERV | Cost
2025-06-01 | HVAC | Carrier | 15   | $130
2025-06-01 | ERV  | Broan   | 13   | $50
```

Then calculate in dashboard:
- Days since change
- Cost per day
- Projected annual cost

## Using Claude in VSCode

1. Open `analysis.ipynb` in VSCode
2. Select any comment
3. Press Cmd/Ctrl + K
4. Ask: "Calculate when efficiency will hit 80%"

## Bottom Line

You're preventing asthma attacks, not following arbitrary schedules. The $180 filters are expensive, but an ER visit is $3000+. This system helps you maximize filter life while maintaining protection.

**Remember**: All device serials and API keys stay in `.env` (never in code)!
