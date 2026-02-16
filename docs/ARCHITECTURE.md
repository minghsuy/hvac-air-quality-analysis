# System Architecture

## Data Collection Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Airthings API  │────▶│   Collector     │────▶│  Google Sheets  │
└─────────────────┘     │  (Spark DGX)    │     └─────────────────┘
                        └─────────────────┘
                               ▲
┌─────────────────┐            │
│ AirGradient     │────────────┘
│ (Local Network) │
└─────────────────┘
```

## Components

### Sensors

1. **Airthings View Plus** (Master Bedroom)
   - OAuth2 API authentication
   - Measures: PM2.5, CO2, VOC, radon, temp, humidity
   - Serial: [configured in .env]

2. **AirGradient Open Air** (Outdoor)
   - Local mDNS API (no auth)
   - URL: `http://airgradient_XXXXXX.local/measures/current`
   - Measures: PM2.5, CO2, VOC, NOX, temp, humidity

3. **AirGradient ONE** (Second Bedroom)
   - Local mDNS API (no auth)
   - URL: `http://airgradient_XXXXXX.local/measures/current`
   - Measures: PM2.5, CO2, VOC, NOX, temp, humidity

### Data Collection Scripts

- **`collect_with_sheets_api_v2.py`**: Main multi-sensor collector using Sheets API
- **`collect_with_sheets_api.py`**: Legacy single-room collector
- **`collect_air_quality.py`**: Legacy single-sensor with Forms API

### Systemd Deployment

The collector runs as a systemd user service with a timer:

```bash
# Check service status
systemctl --user status air-quality-collector.timer
systemctl --user status air-quality-collector.service

# View logs
journalctl --user -u air-quality-collector.service --since "1 hour ago"
```

**Requirements:**
- Enable linger for persistence: `loginctl enable-linger $USER`
- Services survive logout and reboot automatically

### Google Sheets Structure

| Column | Description |
|--------|-------------|
| Timestamp | Collection time |
| Sensor_ID | Unique identifier |
| Room | Location name |
| Sensor_Type | airthings/airgradient |
| Indoor_PM25 | Indoor PM2.5 reading |
| Outdoor_PM25 | Outdoor PM2.5 reading |
| Filter_Efficiency | Calculated efficiency |
| Indoor_CO2 | CO2 levels |
| Indoor_VOC | VOC index |
| Indoor_NOX | NOX index |
| Indoor_Temp | Temperature |
| Indoor_Humidity | Humidity % |
| Indoor_Radon | Radon (Airthings only) |
| Outdoor_* | Outdoor equivalents |

### API Authentication

- **Airthings**: OAuth2 client credentials in `.env`
- **AirGradient**: No auth (local network only)
- **Google Sheets**: Service account JSON credentials

## Network Configuration

### mDNS Resolution

If mDNS (.local domains) don't work on your network, use IP-based discovery:

```bash
# Run the IP discovery script
python scripts/update_airgradient_ips.py

# This updates sensors.json with current IPs
```

### DHCP Reservations Recommended

Configure static DHCP leases for AirGradient devices to maintain fixed IPs.

## Dashboard & Analysis

### Streamlit Dashboard (`scripts/dashboard.py`)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Google Sheets   │────▶│  Parquet Cache   │────▶│   Streamlit     │
│  (98k+ rows)    │     │  (.cache/)       │     │  Dashboard      │
│  ~3.5s fetch    │     │  ~18ms read      │     │  (7 pages)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

3-layer caching strategy:
1. **Parquet on disk** (1hr TTL) — eliminates network latency
2. **Session state** — persists across page switches within a session
3. **Pre-aggregated dicts** — hourly/daily summaries computed once on load

### Analysis Tools

- **Real-time**: Google Sheets formulas
- **Interactive**: Streamlit dashboard with Plotly charts
- **Static**: `scripts/create_visualizations.py` for README/LinkedIn PNGs
- **Benchmarking**: `scripts/bench_heatmap.py` for performance comparisons
- **Correlation**: Spearman rank correlation for all 14 metrics
- **Anomaly detection**: LOWESS smoothing with residual-based spike identification
