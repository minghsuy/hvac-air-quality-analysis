# HVAC Air Quality Project - Claude Code Context

## Vision

Transform this data collection project into a family health dashboard that any family can deploy to protect their children's cognitive development and respiratory health.

**North Star Metric**: One family's kid gets sick less because of this project.

## Why This Exists

My mother lived next to a freeway for 20 years. The constant coughing. The asthma. The cancer. Her early passing at 67.

My wife has asthma. My son was sick every 45 days. After installing ERV + MERV15 + heat pump and monitoring air quality:
- CO2 in son's bedroom: 1000+ ppm → 600 ppm
- Son's sickness: every 45 days → healthy all fall/winter 2025
- Wife's asthma triggers: reduced

The research is clear: CO2 above 1000 ppm reduces children's cognitive performance to 28% of capacity. Better air quality has higher ROI than Kumon and private school tuition combined.

## Current State

### What Works
- **Sensors**: Airthings (indoor) + AirGradient (outdoor + second room)
- **Collection**: Python scripts on DGX Spark, systemd timers, 5-minute intervals
- **Storage**: Google Sheets (82,791+ readings)
- **Alerting**: Google Apps Script (HVACMonitor_v3.gs)
  - Efficiency-based filter alerts (not time-based)
  - Seasonal calibration
  - Barometric pressure alerts (wife's nerve pain)
  - Outdoor AQI → ERV on/off recommendations
  - Indoor PM spike detection
- **Documentation**: Wiki with "Why This Project Matters" story

### What's Missing
1. **Visual Dashboard** - Currently just Google Sheets, need real-time webapp
2. **README Impact** - Story buried in Wiki, not surfaced in README
3. **Visualizations** - No charts/graphs to show outcomes
4. **Automation** - Still manually turning ERV on/off based on email alerts
5. **Shareability** - Other families can't easily deploy this

## Technical Architecture

```
Current:
Sensors → Python (DGX Spark) → Google Sheets → Apps Script → Email alerts

Future:
Sensors → Python (DGX Spark) → Google Sheets → Apps Script
                                      ↓
                              Webapp Dashboard (DGX Spark)
                                      ↓
                              ERV/HVAC automation (future)
```

## Hardware Setup

| Device | Location | What it measures | API |
|--------|----------|------------------|-----|
| Airthings View Plus | Master Bedroom | PM2.5, CO2, VOC, radon, temp, humidity | OAuth2 cloud API |
| AirGradient Open Air | Outdoor (balcony) | PM2.5, CO2, VOC, NOX, temp, humidity | Local mDNS |
| AirGradient ONE | Son's Bedroom | PM2.5, CO2, VOC, NOX, temp, humidity | Local mDNS |
| Temp Stick WiFi | Attic (near ERV/air handler) | Temperature, humidity | REST API (cloud) |

## HVAC System

| Component | Model | Purpose |
|-----------|-------|---------|
| ERV | Carrier ERVXXLHB | Fresh air + CO2 reduction (horizontal, attic-installed) |
| Main Filter | Carrier MERV 15 + Plasma | PM2.5 filtration + pathogen killing |
| Heat Pump | [model] | Gentle heating/cooling, no dry air |
| Zone Filters | 12x12x1 | Individual room blower protection |

## Key Data Findings (82,791 readings)

1. **Filter Life**: MERV 13 maintains >85% efficiency for 120+ days (manufacturer says 45)
2. **Load-based prediction FAILED**: Filter at 197% of "max life" still performed at 87.3%
3. **Efficiency-based alerts WORK**: Measure actual performance, not theoretical decay
4. **Seasonal calibration needed**: Winter/summer have different outdoor PM2.5 baselines

## Key Health Findings

1. **CO2 in small bedroom with 2 people**: Easily exceeds 1000 ppm without ERV
2. **After ERV**: Maintains ~600 ppm
3. **Son's health**: Sick every 45 days → healthy all fall/winter 2025
4. **Sleep quality**: No more thermal cycling from gas furnace, stable temps

## Constraints

- **Time**: Full-time job (IC6 at Guidewire), family, wife's surgery April 2026
- **Cost**: Prefer free/cheap infra (Google Apps Script is great)
- **Hosting**: DGX Spark available 24/7 at home for dashboard
- **Learning goals**: Want to learn TSX/React

## Files Reference

| File | Purpose |
|------|---------|
| `HVACMonitor_v3.gs` | Google Apps Script - alerting brain |
| `collect_with_sheets_api_v2.py` | Data collection (runs on DGX Spark) |
| `docs/indoor_airqualitys_hidden_impact_on_family_health.md` | Research summary |
| `wiki-repo/` | Separate git repo for GitHub Wiki |
| `BACKLOG.md` | Prioritized task list |

## Design Principles

1. **Health outcomes > technical metrics** - Lead with "kid stopped getting sick"
2. **Data-driven, not assumption-driven** - Efficiency-based filter alerts, not time-based
3. **Good enough > perfect** - 80th percentile optimization
4. **Show don't tell** - Visualizations > explanations
5. **Open source for impact** - Help other families, not for clout

## Target Audiences

| Audience | What they care about | Where to reach them |
|----------|---------------------|---------------------|
| Parents with sick kids | "My kid stopped getting sick" | Parent forums, NextDoor |
| Engineers | Data, architecture, code quality | LinkedIn, GitHub, HN |
| California homeowners | Wildfire smoke protection | r/BayArea, local groups |
| Asthma families | Trigger reduction | Asthma support communities |

## Key Insight to Communicate

> "Indoor air quality monitoring has higher ROI for your child's cognitive development than tutoring or private school tuition. CO2 above 1000 ppm cuts cognitive performance by 72%. Most bedrooms exceed this when two people sleep in a small room."

## Future Vision: Help Friends Deploy

Eventually want to:
1. Go to friends' houses
2. Help them set up sensors
3. Configure data collection
4. Deploy dashboard
5. One less sick kid = success

This requires making the setup process simpler and creating good documentation.
