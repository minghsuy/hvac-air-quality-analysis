# 🚀 Start Here - HVAC Filter Monitoring Project

## Your Situation
- **Timeline**: HVAC (Feb 2025) → ERV (Mar 2025) → MERV 13 (Jun 2025)
- **Goal**: Replace filters BEFORE asthma symptoms, not on schedule
- **Method**: Compare indoor (Airthings) vs outdoor (AirGradient) PM2.5

## What This Does
Every hour, your Unifi Gateway will:
1. Get indoor air quality from Airthings API
2. Get outdoor air quality from local AirGradient sensor  
3. Calculate filter efficiency: (Outdoor - Indoor) / Outdoor × 100%
4. Log to Google Sheets
5. Alert you when efficiency < 85%

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

### Step 2: Unifi Setup (10 min)
```bash
# SSH to gateway
ssh root@your-gateway-ip

# Run setup
./setup_unifi.sh

# Edit credentials
vi /data/scripts/.env
```

### Step 3: Google Sheets (10 min)
1. Create form with 7 short-answer fields
2. Get form ID from URL
3. Get field IDs by inspecting HTML
4. Update in .env

### Step 4: Test (5 min)
```bash
# On Unifi
python3 /data/scripts/collect_air.py

# Should see:
# Indoor: 3.2 μg/m³, Outdoor: 18.5 μg/m³, Efficiency: 82.7%
```

## File Reference

| File | Purpose | Where it runs |
|------|---------|---------------|
| `collect_air_quality.py` | Main data collector | Unifi Gateway (hourly) |
| `analyze_historical.py` | Analyze your CSV export | Your computer (on demand) |
| `analysis.ipynb` | Interactive analysis with Claude | VSCode on your computer |
| `.env` | Your secrets (NEVER commit!) | Both locations |
| `.env.example` | Safe template | GitHub |

## Key Thresholds

- **Efficiency < 90%**: Start watching closely
- **Efficiency < 85%**: Get alerts, plan replacement  
- **Efficiency < 80%**: Replace within days
- **Indoor PM2.5 > 12**: Replace immediately

## Cost Tracking

Current (if replaced today):
- Days since MERV 13: ~45 days
- HVAC filter: $130
- ERV filter: $50  
- Daily cost: $4.00/day

Goal: Extend to 120+ days = $1.50/day

## Using Claude in VSCode

1. Open `analysis.ipynb` in VSCode
2. Select any comment
3. Press Cmd/Ctrl + K
4. Ask: "Calculate when efficiency will hit 80%"

## Bottom Line

You're preventing asthma attacks, not following arbitrary schedules. The $180 filters are expensive, but an ER visit is $3000+. This system helps you maximize filter life while maintaining protection.

**Remember**: All device serials and API keys stay in `.env` (never in code)!
