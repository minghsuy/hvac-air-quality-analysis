# HVAC Air Quality Project Overview

## Problem Statement

HVAC filters are expensive ($130 for MERV 15) and changing them too frequently wastes money, but waiting too long triggers asthma symptoms. The manufacturer recommends 3-6 months, but actual lifetime varies based on outdoor air quality, usage patterns, and season.

## Solution

Real-time filter efficiency monitoring by comparing indoor vs outdoor air quality:
- **Indoor sensor**: Airthings View Plus (master bedroom) 
- **Outdoor sensor**: AirGradient Open Air
- **New indoor sensor**: AirGradient ONE (second bedroom)

## Key Metrics

- **Filter Efficiency** = (Outdoor PM2.5 - Indoor PM2.5) / Outdoor PM2.5 × 100%
- **Alert threshold**: < 85% efficiency
- **Replace threshold**: < 80% efficiency
- **WHO guideline**: Indoor PM2.5 < 15 μg/m³

## Cost Goals

- **Current**: $130 every 45 days = $2.89/day
- **Target**: $130 every 120+ days = $1.08/day
- **Annual savings**: $661/year

## Health Impact

Prevents asthma triggers by replacing filters before efficiency drops too low. Early detection of filter degradation allows planned replacement instead of emergency changes.

## Data Collection

- Every 5 minutes via cron job on Unifi Gateway
- Stored in Google Sheets for analysis
- Local backup in JSONL format
- Multi-sensor support for room-by-room analysis

## Timeline

- **July 26, 2025**: Project started after Carrier Infinity warnings
- **Aug 8, 2025**: Data collection interrupted (firmware update)
- **Aug 29, 2025**: Filter replaced, system upgraded
- **Aug 30, 2025**: Multi-sensor support added
- **Current**: Monitoring two bedrooms + outdoor