/**
 * HVAC & Air Quality Monitor v3.0
 *
 * FOR WIFE (ALERT_EMAIL_2):
 *   - Barometric pressure drops → nerve pain warning
 *   - Outdoor air quality → when to turn ERV on/off for asthma
 *
 * FOR YOU (ALERT_EMAIL):
 *   - ERV/Main filter efficiency → "TIME TO CHANGE FILTER" (based on actual performance)
 *   - Zone filter age → time-based replacement reminders (can't measure efficiency)
 *   - Data collection status
 *   - CO2/ventilation alerts
 *
 * KEY CONCEPTS:
 *   - ERV/Main filters: Alert when efficiency drops below threshold (seasonally calibrated)
 *   - Zone filters: Alert after X days (they don't affect efficiency readings)
 *   - Thresholds auto-calibrate from your data monthly
 *
 * SETUP - Script Properties:
 *   ALERT_EMAIL       - Your email
 *   ALERT_EMAIL_2     - Wife's email
 *   LOCATION_LAT      - Latitude (e.g., 37.35)
 *   LOCATION_LON      - Longitude (e.g., -121.95)
 *   LOCATION_NAME     - Display name (e.g., "Home")
 *   LOCATION_TIMEZONE - Timezone (e.g., "America/Los_Angeles")
 *
 * SETUP - Filter_Changes sheet columns:
 *   Date | Filter_Type | Location | Action | Filter_Model | Notes
 *   Filter_Type: erv, main, zone (with Location = master_bedroom or second_bedroom)
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

// Bump on every repo edit so the Apps Script execution log reveals which repo
// version is actually running — deploy-drift is grep-able, not a mystery.
const MONITOR_VERSION = 'v3.2026-04-17';

const CONFIG = {
  SHEET_NAME: 'Cleaned_Data_20250831',
  FILTER_SHEET: 'Filter_Changes',

  // DEPRECATED: superseded by per-sensor EXPECTED_SENSORS[type].maxGapHours below.
  // Left in place for any callers still referencing it; checkDataCollection() no
  // longer consults it.
  DATA_GAP_HOURS: 2,

  // Per-sensor expected cadence. A sensor is flagged STOPPED when its most
  // recent row is older than maxGapHours. Temp Stick reports hourly (battery
  // conservation); Airthings and AirGradient report every 5 min.
  EXPECTED_SENSORS: {
    airthings:   { maxGapHours: 1 },
    airgradient: { maxGapHours: 1 },
    tempstick:   { maxGapHours: 3 },
  },

  // Absolute indoor PM threshold — fires when master-bedroom Indoor_PM25 stays
  // elevated while outdoor is calm (filtration-failure signature). Calibrated
  // against 9 months of master-bedroom data: threshold=5 produces ~2.76
  // alerts/wk; slope gate + progressive escalation separate cooking's
  // spike-then-decay from filtration-failure's rise-and-sustain.
  INDOOR_BASELINE: {
    room:                    'master_bedroom',  // canonical indoor sensor
    absoluteThreshold:       5,                 // µg/m³
    warningMinutes:          30,                // sustained above threshold → WARNING
    criticalMinutes:         90,                // sustained above threshold → CRITICAL
    outdoorGate:             10,                // skip check when outdoor PM >= this
    slopeSuppressThreshold: -0.5,               // µg/m³ drop over 30-min windows → suppress WARNING
    cooldownMinutes:         60,                // per-tier cooldown
  },

  // Outdoor AQI thresholds for ERV control (asthma-friendly)
  OUTDOOR_AQI: {
    shutoffPM25: 35,      // Turn ERV OFF above this
    reducePM25: 25,       // Consider reducing ERV
    safePM25: 15,         // Safe to turn ERV back ON
    sustainedHours: 1,    // How long bad air must persist before alert
  },

  // Pressure thresholds (nerve pain sensitivity)
  PRESSURE: {
    dropThreshold: 6,     // hPa drop to trigger alert
    windowHours: 6,       // Time window for drop detection
    forecastHours: 12,    // Look ahead for drops
  },

  // Efficiency thresholds - THIS IS THE "CHANGE FILTER" SIGNAL for ERV/Main
  // These are DEFAULTS - calibrated values stored in Script Properties
  EFFICIENCY: {
    changeFilter: 75,   // Below this = CHANGE YOUR FILTER
    critical: 65,       // Urgent - filter is failing
    // Minimum outdoor PM2.5 for reliable measurement (seasonal)
    minOutdoorPM: {
      winter: 10,       // Plenty of dirty air days
      summer: 5,        // Cleaner air - lower threshold
      default: 7,       // Spring/fall
    },
  },

  // Zone filter reminder intervals (days)
  // Zone filters don't affect efficiency readings - time-based only
  ZONE_FILTER_DAYS: {
    zone_master: 90,    // 12x12x1 in master bedroom
    zone_second: 90,    // 12x12x1 in second bedroom
  },

  // CO2 thresholds
  CO2: {
    warning: 1000,
    high: 800,
  },

  // Indoor PM spike detection (suggests increasing ERV)
  INDOOR_SPIKE: {
    threshold: 5,         // Indoor must exceed outdoor by this much (μg/m³)
    maxOutdoorPM: 25,     // Only suggest ERV increase if outdoor is clean
    cooldownMinutes: 60,  // Don't re-alert within this window
  },

  // ERV/HRV unit specs (attic-installed)
  ERV: {
    maxOperatingTemp: 40,  // °C - max ambient temp for safe operation
  },

  // Nighttime zone control
  NIGHT_TEMP: {
    maxSpread: 3,          // °C - spread above this flags zone damper issues
  },

  // Location defaults (override via Script Properties)
  LOCATION_DEFAULTS: {
    latitude: 37.35,
    longitude: -121.95,
    timezone: 'America/Los_Angeles',
    name: 'My Location'
  },
};

// Column indices (0-based) matching your 18-column schema
const COLS = {
  TIMESTAMP: 0, SENSOR_ID: 1, ROOM: 2, SENSOR_TYPE: 3,
  INDOOR_PM25: 4, OUTDOOR_PM25: 5, FILTER_EFFICIENCY: 6,
  INDOOR_CO2: 7, INDOOR_VOC: 8, INDOOR_NOX: 9,
  INDOOR_TEMP: 10, INDOOR_HUMIDITY: 11, INDOOR_RADON: 12,
  OUTDOOR_CO2: 13, OUTDOOR_TEMP: 14, OUTDOOR_HUMIDITY: 15,
  OUTDOOR_VOC: 16, OUTDOOR_NOX: 17
};

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

/**
 * Main hourly check - runs all monitoring
 */
function runAllChecks() {
  console.log(`Monitor version: ${MONITOR_VERSION}`);
  const alerts = { you: [], wife: [] };

  // === FOR WIFE ===

  // 1. Check barometric pressure (nerve pain)
  const pressure = checkPressure();
  if (pressure.alerts.length > 0) {
    alerts.wife.push(...pressure.alerts);
  }

  // 2. Check outdoor air quality (ERV control for asthma)
  const aqi = checkOutdoorAQI();
  if (aqi.alerts.length > 0) {
    alerts.wife.push(...aqi.alerts);
    // You also get AQI alerts
    alerts.you.push(...aqi.alerts);
  }

  // === FOR YOU ===

  // 3. Check filter efficiency - THIS IS THE "CHANGE FILTER" SIGNAL for ERV/Main
  const efficiency = checkEfficiency();
  if (efficiency.alerts.length > 0) {
    alerts.you.push(...efficiency.alerts);
  }

  // 4. Check for indoor PM spikes (cooking, cleaning)
  const indoorSpike = checkIndoorSpike();
  if (indoorSpike.alerts.length > 0) {
    alerts.you.push(...indoorSpike.alerts);
  }

  // 4b. Check absolute indoor PM baseline (filtration-failure scenario #27)
  const indoorBaseline = checkIndoorBaseline();
  if (indoorBaseline.alerts.length > 0) {
    alerts.you.push(...indoorBaseline.alerts);
  }

  // 5. Check zone filter ages (time-based - can't measure efficiency)
  const zoneFilters = checkZoneFilters();
  if (zoneFilters.alerts.length > 0) {
    alerts.you.push(...zoneFilters.alerts);
  }

  // 6. Check CO2 levels (ventilation)
  const co2 = checkCO2();
  if (co2.alerts.length > 0) {
    alerts.you.push(...co2.alerts);
  }

  // 7. Check data collection
  const data = checkDataCollection();
  if (data.alert) {
    alerts.you.push(data.alert);
  }

  // Send alerts
  sendAlerts(alerts);

  console.log('Check complete:', new Date().toISOString());
  return { alerts, pressure, aqi, efficiency, indoorSpike, indoorBaseline, zoneFilters, co2, data };
}

// ============================================================================
// PRESSURE MONITORING (For wife - nerve pain)
// ============================================================================

function checkPressure() {
  const location = getLocation();
  const url = `https://api.open-meteo.com/v1/forecast?` +
    `latitude=${location.latitude}&longitude=${location.longitude}` +
    `&hourly=surface_pressure` +
    `&timezone=${encodeURIComponent(location.timezone)}` +
    `&past_hours=12&forecast_hours=24`;

  try {
    const response = UrlFetchApp.fetch(url);
    const data = JSON.parse(response.getContentText());
    return analyzePressure(data);
  } catch (error) {
    console.log('Pressure API error:', error);
    return { current: null, alerts: [] };
  }
}

function analyzePressure(data) {
  const times = data.hourly.time;
  const pressures = data.hourly.surface_pressure;
  const now = new Date();
  const alerts = [];

  // Find current pressure
  let currentIdx = 0;
  let minDiff = Infinity;
  times.forEach((t, i) => {
    const diff = Math.abs(new Date(t) - now);
    if (diff < minDiff) { minDiff = diff; currentIdx = i; }
  });

  const current = pressures[currentIdx];

  // Check recent drop
  const pastIdx = Math.max(0, currentIdx - CONFIG.PRESSURE.windowHours);
  const pastPressure = pressures[pastIdx];
  const recentDrop = pastPressure - current;

  if (recentDrop >= CONFIG.PRESSURE.dropThreshold) {
    alerts.push({
      level: 'WARNING',
      message: `🌡️ PRESSURE DROP: ${recentDrop.toFixed(1)} hPa in ${CONFIG.PRESSURE.windowHours}h ` +
               `(${pastPressure.toFixed(0)} → ${current.toFixed(0)} hPa). May trigger nerve pain.`
    });
  }

  // Check forecast
  const futureIdx = Math.min(pressures.length - 1, currentIdx + CONFIG.PRESSURE.forecastHours);
  const futurePressure = pressures[futureIdx];
  const forecastDrop = current - futurePressure;

  if (forecastDrop >= CONFIG.PRESSURE.dropThreshold) {
    alerts.push({
      level: 'INFO',
      message: `📉 PRESSURE FORECAST: ${forecastDrop.toFixed(1)} hPa drop expected in ${CONFIG.PRESSURE.forecastHours}h ` +
               `(${current.toFixed(0)} → ${futurePressure.toFixed(0)} hPa). Consider preventive measures.`
    });
  }

  return { current, trend: current - pastPressure, forecast: futurePressure - current, alerts };
}

// ============================================================================
// OUTDOOR AQI MONITORING (For wife - ERV control for asthma)
// ============================================================================

function checkOutdoorAQI() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 50) return { current: null, alerts: [] };

  // Get last 3 hours of data
  const numRows = Math.min(72, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 18).getValues();

  const now = new Date();
  const oneHourAgo = new Date(now - 60 * 60 * 1000);

  // Get recent outdoor PM2.5
  const recentReadings = data
    .filter(r => new Date(r[COLS.TIMESTAMP]) >= oneHourAgo)
    .map(r => parseFloat(r[COLS.OUTDOOR_PM25]) || 0);

  if (recentReadings.length === 0) return { current: null, alerts: [] };

  const current = recentReadings[recentReadings.length - 1];
  const avg1h = average(recentReadings);

  const alerts = [];
  const props = PropertiesService.getScriptProperties();
  const previousState = props.getProperty('ERV_STATE') || 'NORMAL';

  // Determine recommendation
  if (avg1h >= CONFIG.OUTDOOR_AQI.shutoffPM25) {
    if (previousState !== 'OFF') {
      alerts.push({
        level: 'WARNING',
        message: `🚫 TURN ERV OFF - Bad outdoor air!\n` +
                 `Outdoor PM2.5: ${avg1h.toFixed(1)} μg/m³ (1h avg)\n` +
                 `This is unhealthy for asthma. Turn ERV off or set to recirculate.\n` +
                 `You'll be notified when air improves.`
      });
      props.setProperty('ERV_STATE', 'OFF');
    }
  } else if (avg1h <= CONFIG.OUTDOOR_AQI.safePM25 && previousState === 'OFF') {
    alerts.push({
      level: 'INFO',
      message: `✅ OK to turn ERV back ON\n` +
               `Outdoor PM2.5: ${avg1h.toFixed(1)} μg/m³ (1h avg)\n` +
               `Air quality has improved. Safe to resume normal ERV operation.`
    });
    props.setProperty('ERV_STATE', 'NORMAL');
  }

  return { current, avg1h, state: props.getProperty('ERV_STATE'), alerts };
}

// ============================================================================
// FILTER EFFICIENCY MONITORING (Actual degradation detection)
// ============================================================================

function checkEfficiency() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 100) return { alerts: [] };

  // Get seasonally-calibrated thresholds
  const thresholds = getEfficiencyThresholds();

  // Get last 4 hours of data
  const numRows = Math.min(96, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 18).getValues();

  // Only use high-confidence readings:
  // 1. Outdoor PM2.5 >= threshold (enough pollution to measure)
  // 2. Indoor PM2.5 <= Outdoor PM2.5 (exclude indoor spikes like cooking)
  const reliable = data.filter(r => {
    const outdoor = parseFloat(r[COLS.OUTDOOR_PM25]) || 0;
    const indoor = parseFloat(r[COLS.INDOOR_PM25]) || 0;
    return outdoor >= thresholds.minOutdoorPM && indoor <= outdoor;
  });

  if (reliable.length < 5) {
    return { alerts: [], note: 'Outdoor air too clean for reliable measurement' };
  }

  const efficiencies = reliable.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0);
  const medianEff = median(efficiencies);

  const alerts = [];

  if (medianEff < thresholds.critical) {
    alerts.push({
      level: 'CRITICAL',
      message: `🚨 CHANGE FILTER NOW - Efficiency critically low!\n\n` +
               `Current efficiency: ${medianEff.toFixed(0)}%\n` +
               `Threshold: ${thresholds.critical}% (seasonally calibrated)\n` +
               `Based on ${reliable.length} reliable readings\n\n` +
               `Your filter is no longer protecting indoor air quality.`
    });
  } else if (medianEff < thresholds.changeFilter) {
    alerts.push({
      level: 'WARNING',
      message: `⚠️ TIME TO CHANGE FILTER - Efficiency declining\n\n` +
               `Current efficiency: ${medianEff.toFixed(0)}%\n` +
               `Threshold: ${thresholds.changeFilter}% (seasonally calibrated)\n` +
               `Based on ${reliable.length} reliable readings\n\n` +
               `Filter performance has degraded. Plan replacement soon.`
    });
  }

  return { medianEfficiency: medianEff, readingCount: reliable.length, thresholds, alerts };
}

/**
 * Get current season name
 */
function getSeason() {
  const month = new Date().getMonth() + 1;
  if ([12, 1, 2].includes(month)) return 'winter';
  if ([6, 7, 8].includes(month)) return 'summer';
  return 'default';
}

/**
 * Get seasonally-calibrated efficiency thresholds
 * Uses calibrated values from Script Properties if available
 */
function getEfficiencyThresholds() {
  const season = getSeason();

  const props = PropertiesService.getScriptProperties();
  const stored = props.getProperty(`EFFICIENCY_${season.toUpperCase()}`);

  // Start with defaults
  let thresholds = {
    changeFilter: CONFIG.EFFICIENCY.changeFilter,
    critical: CONFIG.EFFICIENCY.critical,
    minOutdoorPM: CONFIG.EFFICIENCY.minOutdoorPM[season] || CONFIG.EFFICIENCY.minOutdoorPM.default,
  };

  // Override with calibrated values if available
  if (stored) {
    try {
      const calibrated = JSON.parse(stored);
      thresholds = { ...thresholds, ...calibrated };
      console.log(`Using calibrated ${season} thresholds`);
    } catch (e) { }
  }

  console.log(`Season: ${season}, minOutdoorPM: ${thresholds.minOutdoorPM} μg/m³`);
  return thresholds;
}

/**
 * Calibrate efficiency thresholds from your data
 * Run this after accumulating several months of data
 */
function calibrateEfficiencyThresholds() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const data = sheet.getDataRange().getValues().slice(1);

  console.log('Calibrating efficiency thresholds...');
  console.log(`Total readings: ${data.length}`);

  const seasons = { winter: [], summer: [], default: [] };

  data.forEach(row => {
    const month = new Date(row[COLS.TIMESTAMP]).getMonth() + 1;
    const season = [12, 1, 2].includes(month) ? 'winter' :
                   [6, 7, 8].includes(month) ? 'summer' : 'default';

    const outdoorPM = parseFloat(row[COLS.OUTDOOR_PM25]) || 0;
    const efficiency = parseFloat(row[COLS.FILTER_EFFICIENCY]) || 0;

    // Use seasonal minOutdoorPM threshold
    const minPM = CONFIG.EFFICIENCY.minOutdoorPM[season] || CONFIG.EFFICIENCY.minOutdoorPM.default;
    if (outdoorPM >= minPM) {
      seasons[season].push(efficiency);
    }
  });

  const props = PropertiesService.getScriptProperties();

  Object.entries(seasons).forEach(([season, efficiencies]) => {
    const minPM = CONFIG.EFFICIENCY.minOutdoorPM[season] || CONFIG.EFFICIENCY.minOutdoorPM.default;
    console.log(`\n${season.toUpperCase()} (minOutdoorPM: ${minPM} μg/m³): ${efficiencies.length} readings`);

    if (efficiencies.length < 500) {
      console.log('  Insufficient data for calibration');
      return;
    }

    // Use 10th percentile as "change filter" threshold
    // 5th percentile as "critical"
    const sorted = efficiencies.slice().sort((a, b) => a - b);
    const changeFilter = sorted[Math.floor(sorted.length * 0.10)];
    const critical = sorted[Math.floor(sorted.length * 0.05)];

    const thresholds = {
      changeFilter: Math.round(changeFilter),
      critical: Math.round(critical),
      minOutdoorPM: minPM,
    };

    console.log(`  Change filter threshold: ${thresholds.changeFilter}%`);
    console.log(`  Critical threshold: ${thresholds.critical}%`);

    props.setProperty(`EFFICIENCY_${season.toUpperCase()}`, JSON.stringify(thresholds));
  });

  props.setProperty('LAST_CALIBRATION', new Date().toISOString());
  console.log('\nCalibration complete!');
}

// ============================================================================
// INDOOR PM SPIKE DETECTION (suggest increasing ERV)
// ============================================================================

/**
 * Detect indoor PM spikes (cooking, cleaning, etc.) and suggest ERV boost
 * Only alerts when outdoor air is clean enough to help
 */
function checkIndoorSpike() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 20) return { alerts: [] };

  const props = PropertiesService.getScriptProperties();
  const alerts = [];

  // Get last 30 min of data (6 readings at 5-min intervals)
  const numRows = Math.min(6, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 18).getValues();

  // Get the most recent reading
  const latest = data[data.length - 1];
  const indoor = parseFloat(latest[COLS.INDOOR_PM25]) || 0;
  const outdoor = parseFloat(latest[COLS.OUTDOOR_PM25]) || 0;

  // Check if this is an indoor spike
  const spikeAmount = indoor - outdoor;
  const isSpike = spikeAmount >= CONFIG.INDOOR_SPIKE.threshold;
  const outdoorClean = outdoor <= CONFIG.INDOOR_SPIKE.maxOutdoorPM;

  if (!isSpike) {
    // No spike - clear cooldown if spike has ended
    props.deleteProperty('INDOOR_SPIKE_ALERTED');
    return { indoor, outdoor, spikeAmount, alerts };
  }

  // Check cooldown to avoid repeated alerts
  const lastAlerted = props.getProperty('INDOOR_SPIKE_ALERTED');
  if (lastAlerted) {
    const lastAlertTime = new Date(lastAlerted);
    const minutesSince = (new Date() - lastAlertTime) / (1000 * 60);
    if (minutesSince < CONFIG.INDOOR_SPIKE.cooldownMinutes) {
      return { indoor, outdoor, spikeAmount, inCooldown: true, alerts };
    }
  }

  // Spike detected - send alert
  if (outdoorClean) {
    alerts.push({
      level: 'INFO',
      message: `🍳 INDOOR PM SPIKE DETECTED\n\n` +
               `Indoor: ${indoor.toFixed(1)} μg/m³\n` +
               `Outdoor: ${outdoor.toFixed(1)} μg/m³\n` +
               `Spike: +${spikeAmount.toFixed(1)} μg/m³\n\n` +
               `Likely cause: cooking, cleaning, or candles.\n` +
               `Outdoor air is clean - consider temporarily setting ERV to HIGH to clear air faster.`
    });
  } else {
    alerts.push({
      level: 'INFO',
      message: `🍳 INDOOR PM SPIKE DETECTED\n\n` +
               `Indoor: ${indoor.toFixed(1)} μg/m³\n` +
               `Outdoor: ${outdoor.toFixed(1)} μg/m³ (not clean)\n` +
               `Spike: +${spikeAmount.toFixed(1)} μg/m³\n\n` +
               `Likely cause: cooking, cleaning, or candles.\n` +
               `Note: Outdoor air is also elevated (${outdoor.toFixed(1)} μg/m³), so increasing ERV won't help much.\n` +
               `Consider using a portable air purifier or waiting it out.`
    });
  }

  props.setProperty('INDOOR_SPIKE_ALERTED', new Date().toISOString());

  return { indoor, outdoor, spikeAmount, outdoorClean, alerts };
}

// ============================================================================
// INDOOR BASELINE CHECK (#27)
// Absolute-threshold alert for master-bedroom PM when outdoor is calm.
// Progressive escalation (WARNING → CRITICAL) + slope gate (suppress when PM
// is already decaying) separate cooking from filtration failure.
// ============================================================================

function _medianOf(arr) {
  if (!arr.length) return NaN;
  const s = arr.slice().sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function checkIndoorBaseline() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 20) return { alerts: [] };

  const cfg = CONFIG.INDOOR_BASELINE;
  const props = PropertiesService.getScriptProperties();

  // Pull last 500 rows — enough for 90 min across all sensors even post-dedup.
  const numRows = Math.min(500, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 18).getValues();

  // Filter to the canonical indoor room ONLY. Do NOT copy checkIndoorSpike's
  // pattern of reading last 6 rows regardless of sensor — that silently pins
  // indoor to 0 when the latest row is a Temp Stick attic row.
  const now = new Date();
  const windowMs = cfg.criticalMinutes * 60 * 1000; // 90 min
  const windowStart = new Date(now.getTime() - windowMs);

  const roomRows = data
    .filter(r => String(r[COLS.ROOM]) === cfg.room)
    .map(r => ({
      ts: new Date(r[COLS.TIMESTAMP]),
      indoor: parseFloat(r[COLS.INDOOR_PM25]),
      outdoor: parseFloat(r[COLS.OUTDOOR_PM25]),
    }))
    .filter(r => !isNaN(r.ts.getTime()) && r.ts >= windowStart && !isNaN(r.indoor));

  if (roomRows.length < 4) {
    return { alerts: [], note: 'insufficient master_bedroom rows in window' };
  }

  const warningStart = new Date(now.getTime() - cfg.warningMinutes * 60 * 1000);
  const prevStart = new Date(now.getTime() - 2 * cfg.warningMinutes * 60 * 1000);

  const now30 = roomRows.filter(r => r.ts >= warningStart).map(r => r.indoor);
  const prev30 = roomRows.filter(r => r.ts >= prevStart && r.ts < warningStart).map(r => r.indoor);
  const full90 = roomRows.map(r => r.indoor);

  if (now30.length < 4) return { alerts: [], note: 'insufficient samples in 30-min window' };

  const now30Med = _medianOf(now30);
  const prev30Med = _medianOf(prev30);
  const full90Med = _medianOf(full90);

  // Most-recent outdoor reading (from the same scan; outdoor rows interleave
  // with master_bedroom rows at the same tick).
  const outdoorRows = data
    .filter(r => String(r[COLS.ROOM]) === 'outdoor')
    .map(r => ({ ts: new Date(r[COLS.TIMESTAMP]), outdoor: parseFloat(r[COLS.OUTDOOR_PM25]) }))
    .filter(r => !isNaN(r.ts.getTime()) && !isNaN(r.outdoor))
    .sort((a, b) => b.ts - a.ts);
  const latestOutdoor = outdoorRows.length ? outdoorRows[0].outdoor : roomRows[roomRows.length - 1].outdoor;

  // Outdoor gate: above this, checkAQI covers the scenario — don't double-alert.
  if (!isNaN(latestOutdoor) && latestOutdoor >= cfg.outdoorGate) {
    return { alerts: [], note: `outdoor ${latestOutdoor.toFixed(1)} >= gate ${cfg.outdoorGate}` };
  }

  const alerts = [];
  const warnKey = 'INDOOR_BASELINE_WARN_AT';
  const critKey = 'INDOOR_BASELINE_CRIT_AT';

  const cooldownMs = cfg.cooldownMinutes * 60 * 1000;
  const inCooldown = (key) => {
    const last = props.getProperty(key);
    return last && (now - new Date(last)) < cooldownMs;
  };

  const direction = (() => {
    if (isNaN(latestOutdoor)) return 'unknown outdoor context';
    const diff = now30Med - latestOutdoor;
    if (diff > 0.5) return 'indoor > outdoor → filtration failure suspected';
    if (diff < -0.5) return 'indoor < outdoor → outdoor infiltration exceeding filter capacity';
    return 'indoor ≈ outdoor';
  })();

  const body = (level) =>
    `${level === 'CRITICAL' ? '🚨 Indoor PM elevated and not resolving' : '⚠️ Indoor PM elevated'}\n\n` +
    `Indoor (${cfg.room}): current=${now30.slice(-1)[0].toFixed(1)} μg/m³, ` +
    `30-min median=${now30Med.toFixed(1)}, 90-min median=${full90Med.toFixed(1)}\n` +
    `Outdoor: ${isNaN(latestOutdoor) ? 'n/a' : latestOutdoor.toFixed(1) + ' μg/m³'}\n` +
    `Context: ${direction}\n\n` +
    `Suggested action: turn on main HVAC fan to circulate air through the MERV 13 return ` +
    `filter. If already on, check filter condition.`;

  // CRITICAL takes priority over WARNING. Uses independent cooldown so an
  // earlier WARNING doesn't suppress the escalation.
  const criticalSustained =
    full90.length >= 15 &&        // need real 90-min coverage, not 3 samples
    full90Med > cfg.absoluteThreshold;

  if (criticalSustained && !inCooldown(critKey)) {
    alerts.push({ level: 'CRITICAL', message: body('CRITICAL') });
    props.setProperty(critKey, now.toISOString());
  } else if (now30Med > cfg.absoluteThreshold && !inCooldown(warnKey)) {
    // WARNING candidate — apply slope gate. If PM is clearly decaying the
    // event is already resolving (classic cooking signature) and the alert
    // would be noise.
    const slope = prev30.length >= 4 ? (now30Med - prev30Med) : 0;
    if (slope >= cfg.slopeSuppressThreshold) {
      alerts.push({ level: 'WARNING', message: body('WARNING') });
      props.setProperty(warnKey, now.toISOString());
    }
  }

  return {
    alerts,
    now30Med,
    prev30Med,
    full90Med,
    latestOutdoor,
    sampleCount: roomRows.length,
  };
}

// ============================================================================
// ZONE FILTER TRACKING (time-based - can't measure efficiency)
// ============================================================================

function checkZoneFilters() {
  const filters = getFiltersFromSheet();
  const now = new Date();
  const alerts = [];
  const props = PropertiesService.getScriptProperties();

  Object.entries(CONFIG.ZONE_FILTER_DAYS).forEach(([key, maxDays]) => {
    const filter = filters[key];
    if (!filter || !filter.lastChanged) return;

    const daysInService = Math.floor((now - filter.lastChanged) / (1000 * 60 * 60 * 24));
    const daysRemaining = maxDays - daysInService;

    if (daysRemaining <= 0) {
      // Overdue - always alert (but only once per day)
      const lastAlertKey = `ZONE_OVERDUE_${key}`;
      const lastAlert = props.getProperty(lastAlertKey);
      const today = now.toISOString().split('T')[0];

      if (lastAlert !== today) {
        alerts.push({
          level: 'WARNING',
          message: `🔄 ZONE FILTER: ${filter.location || key}\n` +
                   `${daysInService} days since change - time to replace (${filter.model || '12x12x1'})`
        });
        props.setProperty(lastAlertKey, today);
      }
    } else if (daysRemaining <= 14) {
      // Upcoming - only alert at milestones (14, 7, 3, 1 days) and once per milestone
      const milestones = [14, 7, 3, 1];
      if (milestones.includes(daysRemaining)) {
        const lastAlertKey = `ZONE_REMINDER_${key}`;
        const lastAlertDays = parseInt(props.getProperty(lastAlertKey) || '999');

        // Only alert if this is a new milestone (days remaining decreased)
        if (daysRemaining < lastAlertDays) {
          alerts.push({
            level: 'INFO',
            message: `ℹ️ Zone filter (${filter.location || key}): ${daysRemaining} days until replacement`
          });
          props.setProperty(lastAlertKey, String(daysRemaining));
        }
      }
    }
  });

  return { alerts };
}

// ============================================================================
// FILTER INFO (for reports and diagnostics)
// ============================================================================

function getFiltersFromSheet() {
  const filters = {};

  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.FILTER_SHEET);
    if (!sheet) return filters;

    const data = sheet.getDataRange().getValues().slice(1); // Skip header

    data.forEach(row => {
      const date = new Date(row[0]);
      const filterType = String(row[1]).toLowerCase();
      const location = String(row[2]).toLowerCase();
      const action = String(row[3]).toLowerCase();
      const model = row[4];

      if (!action.includes('replace') && !action.includes('change') && !action.includes('install')) return;

      let key = null;
      if (filterType.includes('erv')) key = 'erv';
      else if (filterType.includes('main') || filterType.includes('hvac')) key = 'main';
      else if (filterType === 'zone' && location.includes('master')) key = 'zone_master';
      else if (filterType === 'zone' && (location.includes('second') || location.includes('son'))) key = 'zone_second';

      if (key && (!filters[key] || date > filters[key].lastChanged)) {
        filters[key] = { lastChanged: date, model: model, location: location };
      }
    });
  } catch (e) {
    console.log('Error reading filters:', e);
  }

  return filters;
}

// ============================================================================
// CO2 MONITORING
// ============================================================================

function checkCO2() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 20) return { alerts: [] };

  const numRows = Math.min(24, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 18).getValues();

  const co2Values = data.map(r => parseFloat(r[COLS.INDOOR_CO2])).filter(v => !isNaN(v));
  if (co2Values.length === 0) return { alerts: [] };

  const maxCO2 = Math.max(...co2Values);
  const alerts = [];

  if (maxCO2 > CONFIG.CO2.warning) {
    alerts.push({
      level: 'WARNING',
      message: `🌬️ HIGH CO2: ${maxCO2.toFixed(0)} ppm - increase ventilation`
    });
  }

  return { current: co2Values[co2Values.length - 1], max: maxCO2, alerts };
}

// ============================================================================
// DATA COLLECTION CHECK
// ============================================================================

function checkDataCollection() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return { status: 'NO_DATA', alert: null };

  // Scan a TIME window, not a row-count window. The old 50-row fixed window was
  // narrower than DATA_GAP_HOURS once sensor cadence varied (Temp Stick writes
  // hourly, not every tick), so a stopped sensor fell out of view before the
  // gap threshold triggered. Span = 2× max(maxGapHours) gives comfortable
  // margin for any configured cadence.
  const maxGapHours = Math.max.apply(
    null,
    Object.values(CONFIG.EXPECTED_SENSORS).map(s => s.maxGapHours)
  );
  const scanHours = maxGapHours * 2;

  // We can't query "rows where timestamp >= X" directly in Apps Script; read
  // enough rows to cover the scan window at the fastest cadence (5 min → 12
  // rows/hr × sensor count). 500 rows covers ~7 hours of 3-sensor writes;
  // generous for scanHours ≤ 6.
  const numRows = Math.min(500, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 4).getValues();

  const now = new Date();
  const cutoff = new Date(now.getTime() - scanHours * 3600 * 1000);
  const props = PropertiesService.getScriptProperties();

  // Build lastSeen over the scan window only.
  const lastSeen = {};
  data.forEach(row => {
    const ts = new Date(row[COLS.TIMESTAMP]);
    if (isNaN(ts.getTime()) || ts < cutoff) return;
    const sensorType = String(row[COLS.SENSOR_TYPE]);
    if (!sensorType || sensorType === 'undefined') return;
    const room = String(row[COLS.ROOM]);
    if (!lastSeen[sensorType] || ts > lastSeen[sensorType].timestamp) {
      lastSeen[sensorType] = { timestamp: ts, room };
    }
  });

  const stoppedSensors = [];
  const resumedSensors = [];

  // Iterate EXPECTED_SENSORS, NOT lastSeen keys. A sensor that stopped writing
  // long ago won't appear in lastSeen at all — iterating lastSeen keys would
  // silently skip it (the bug that hid the 3-day Temp Stick outage).
  Object.entries(CONFIG.EXPECTED_SENSORS).forEach(([sensorType, spec]) => {
    const maxGapMs = spec.maxGapHours * 3600 * 1000;
    const seen = lastSeen[sensorType];
    const gapKey = `DATA_GAP_${sensorType}`;

    const isStopped = !seen || (now - seen.timestamp) > maxGapMs;

    if (isStopped) {
      const hoursSince = seen ? (now - seen.timestamp) / (1000 * 60 * 60) : scanHours;
      if (!props.getProperty(gapKey)) {
        stoppedSensors.push({
          sensorType,
          room: seen ? seen.room : 'unknown',
          hoursSince,
          maxGapHours: spec.maxGapHours,
          neverSeenInWindow: !seen,
        });
        props.setProperty(gapKey, now.toISOString());
      }
    } else {
      const wasDown = props.getProperty(gapKey);
      if (wasDown) {
        resumedSensors.push({ sensorType, room: seen.room, downSince: wasDown });
        props.deleteProperty(gapKey);
      }
    }
  });

  let alert = null;
  if (stoppedSensors.length > 0) {
    const details = stoppedSensors
      .map(s => {
        const age = s.neverSeenInWindow
          ? `not seen in last ${scanHours.toFixed(0)}h`
          : `${s.hoursSince.toFixed(1)}h ago (expected ≤ ${s.maxGapHours}h)`;
        return `  • ${s.room} (${s.sensorType}): ${age}`;
      })
      .join('\n');
    alert = {
      level: 'CRITICAL',
      message: `🚨 SENSOR(S) STOPPED\n${details}\nCheck these sensors!`
    };
  } else if (resumedSensors.length > 0) {
    const details = resumedSensors
      .map(s => `  • ${s.room} (${s.sensorType})`)
      .join('\n');
    alert = {
      level: 'INFO',
      message: `✅ SENSOR(S) RESUMED\n${details}\nData collection back to normal.`
    };
  }

  const expectedCount = Object.keys(CONFIG.EXPECTED_SENSORS).length;
  const status = stoppedSensors.length > 0 ? 'PARTIAL' :
                 Object.keys(lastSeen).length < expectedCount ? 'NO_DATA' : 'OK';

  return { status, lastSeen, stoppedSensors, resumedSensors, alert };
}

// ============================================================================
// ALERT SENDING
// ============================================================================

function sendAlerts(alerts) {
  const props = PropertiesService.getScriptProperties();
  const yourEmail = props.getProperty('ALERT_EMAIL');
  const wifeEmail = props.getProperty('ALERT_EMAIL_2');
  const location = getLocation();

  // Send to wife (pressure + AQI)
  if (alerts.wife.length > 0 && wifeEmail) {
    const hasERV = alerts.wife.some(a => a.message.includes('ERV'));
    const subject = hasERV
      ? (alerts.wife.some(a => a.message.includes('OFF')) ? '🚫 Turn ERV OFF' : '✅ ERV Update')
      : '🌡️ Pressure Alert';

    let body = '💜 Health Alert\n\n';
    alerts.wife.forEach(a => body += a.message + '\n\n');

    MailApp.sendEmail(wifeEmail, subject, body);
  }

  // Send to you (everything else + AQI)
  if (alerts.you.length > 0 && yourEmail) {
    const hasCritical = alerts.you.some(a => a.level === 'CRITICAL');
    const subject = hasCritical ? '🚨 CRITICAL HVAC Alert' : '⚠️ HVAC Alert';

    let body = 'HVAC System Alerts\n\n';
    alerts.you.forEach(a => body += a.message + '\n\n');
    body += '\nDashboard: ' + SpreadsheetApp.getActiveSpreadsheet().getUrl();

    MailApp.sendEmail(yourEmail, subject, body);
  }
}

// ============================================================================
// HELPERS
// ============================================================================

function getLocation() {
  const props = PropertiesService.getScriptProperties();
  return {
    latitude: parseFloat(props.getProperty('LOCATION_LAT')) || CONFIG.LOCATION_DEFAULTS.latitude,
    longitude: parseFloat(props.getProperty('LOCATION_LON')) || CONFIG.LOCATION_DEFAULTS.longitude,
    timezone: props.getProperty('LOCATION_TIMEZONE') || CONFIG.LOCATION_DEFAULTS.timezone,
    name: props.getProperty('LOCATION_NAME') || CONFIG.LOCATION_DEFAULTS.name,
  };
}

function median(arr) {
  if (arr.length === 0) return 0;
  const sorted = arr.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function average(arr) {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function extractValid(rows, colIdx, min, max) {
  const floor = min !== undefined ? min : -Infinity;
  const ceil = max !== undefined ? max : Infinity;
  const vals = [];
  for (let i = 0; i < rows.length; i++) {
    const v = parseFloat(rows[i][colIdx]);
    if (!isNaN(v) && v >= floor && v <= ceil) vals.push(v);
  }
  return vals;
}

// ============================================================================
// WEEKLY DATA HELPERS
// ============================================================================

/**
 * Load one full week of sheet data in a single read.
 * Returns array of rows filtered to the last 7 days, or null if empty.
 */
function getWeeklyData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return null;

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

  // Sheet may have stale data past the current collector's write position.
  // Read timestamp column to find the actual last row with recent data.
  const allTimestamps = sheet.getRange(1, 1, lastRow, 1).getValues();
  let actualLastRow = 0;
  for (let i = allTimestamps.length - 1; i >= 0; i--) {
    const ts = allTimestamps[i][0];
    if (!ts) continue;
    const d = ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T'));
    if (!isNaN(d.getTime()) && d >= sevenDaysAgo) {
      actualLastRow = i + 1; // 1-based
      break;
    }
  }
  if (actualLastRow <= 1) return null;

  // Now find the first row within 7 days (search forward from estimated start)
  let firstRow = Math.max(2, actualLastRow - 6700);
  for (let i = firstRow - 1; i < actualLastRow; i++) {
    const ts = allTimestamps[i][0];
    if (!ts) continue;
    const d = ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T'));
    if (!isNaN(d.getTime()) && d >= sevenDaysAgo) {
      firstRow = i + 1; // 1-based
      break;
    }
  }

  const numRows = actualLastRow - firstRow + 1;
  if (numRows <= 0) return null;

  const data = sheet.getRange(firstRow, 1, numRows, 18).getValues();

  // Parse timestamps consistently for downstream consumers
  const filtered = data.filter(r => {
    const ts = r[COLS.TIMESTAMP];
    if (!ts) return false;
    const d = ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T'));
    return !isNaN(d.getTime()) && d >= sevenDaysAgo;
  });
  return filtered.length > 0 ? filtered : null;
}

/**
 * Compute 7-day min/avg/max for key metrics from weekly sheet data.
 * Filters by room to avoid double-counting sensor-specific columns.
 */
function computeWeeklyTrends(weekData) {
  if (!weekData || weekData.length === 0) return null;

  function stats(arr) {
    if (arr.length === 0) return null;
    const sorted = arr.slice().sort((a, b) => a - b);
    return {
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: average(arr),
      median: median(arr),
      count: arr.length,
    };
  }

  // Bedroom rows: master_bedroom + second_bedroom (have PM2.5, CO2, VOC)
  const bedroomRows = weekData.filter(r => {
    const room = String(r[COLS.ROOM]).toLowerCase();
    return room.includes('master') || room.includes('second');
  });

  // Master only: has radon (Airthings)
  const masterRows = weekData.filter(r =>
    String(r[COLS.ROOM]).toLowerCase().includes('master')
  );

  // Second bedroom only: has outdoor PM2.5 (AirGradient)
  const secondRows = weekData.filter(r =>
    String(r[COLS.ROOM]).toLowerCase().includes('second')
  );

  // Attic rows: temp/humidity only (Temp Stick)
  const atticRows = weekData.filter(r =>
    String(r[COLS.ROOM]).toLowerCase().includes('attic')
  );

  // Nighttime master bedroom temp (11pm-7am) — per-night spread detects zone issues
  // Group by night (date key = date of the evening, so 11pm Sun + 1-6am Mon = "Sun night")
  const nightsByDate = {};
  for (let i = 0; i < masterRows.length; i++) {
    const ts = masterRows[i][COLS.TIMESTAMP];
    const d = ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T'));
    if (!isNaN(d.getTime())) {
      const hour = d.getHours();
      if (hour >= 23 || hour < 7) {
        const temp = parseFloat(masterRows[i][COLS.INDOOR_TEMP]);
        if (!isNaN(temp) && temp >= -40 && temp <= 50) {
          // Normalize: 1am Mon belongs to "Sun night"
          const nightDate = hour < 7
            ? new Date(d.getTime() - 12 * 3600000).toDateString()
            : d.toDateString();
          if (!nightsByDate[nightDate]) nightsByDate[nightDate] = [];
          nightsByDate[nightDate].push(temp);
        }
      }
    }
  }
  // Compute per-night spreads, then take the median spread across the week
  const nightSpreads = [];
  const nightAvgs = [];
  Object.values(nightsByDate).forEach(temps => {
    if (temps.length >= 3) { // need enough readings for meaningful spread
      nightSpreads.push(Math.max.apply(null, temps) - Math.min.apply(null, temps));
      nightAvgs.push(average(temps));
    }
  });
  const nightTempAvg = nightAvgs.length > 0 ? average(nightAvgs) : null;
  const nightSpreadMedian = nightSpreads.length > 0 ? median(nightSpreads) : null;

  // Attic ERV exceedance: count hours and days above max operating temp
  const atticTemps = extractValid(atticRows, COLS.INDOOR_TEMP, -40, 80);
  let ervExceedanceHours = 0;
  let ervExceedanceDays = 0;
  if (atticTemps.length > 0) {
    const exceedanceDates = new Set();
    let exceedanceReadings = 0;
    for (let i = 0; i < atticRows.length; i++) {
      const temp = parseFloat(atticRows[i][COLS.INDOOR_TEMP]);
      if (!isNaN(temp) && temp >= CONFIG.ERV.maxOperatingTemp && temp <= 80) {
        exceedanceReadings++;
        const ts = atticRows[i][COLS.TIMESTAMP];
        const d = ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T'));
        if (!isNaN(d.getTime())) exceedanceDates.add(d.toDateString());
      }
    }
    // Estimate hours from actual sensor span, not full 7 days
    const atticTimestamps = atticRows
      .map(r => { const ts = r[COLS.TIMESTAMP]; return ts instanceof Date ? ts : new Date(String(ts).replace(' ', 'T')); })
      .filter(d => !isNaN(d.getTime()));
    const spanHours = atticTimestamps.length >= 2
      ? (Math.max.apply(null, atticTimestamps) - Math.min.apply(null, atticTimestamps)) / 3600000
      : 7 * 24;
    const readingsPerHour = atticTemps.length / Math.max(spanHours, 1);
    ervExceedanceHours = Math.round(exceedanceReadings / readingsPerHour);
    ervExceedanceDays = exceedanceDates.size;
  }

  return {
    indoorPM: stats(extractValid(bedroomRows, COLS.INDOOR_PM25, 0, 1000)),
    co2: stats(extractValid(bedroomRows, COLS.INDOOR_CO2, 400, 10000)),
    nightTempAvg: nightTempAvg,
    nightSpreadMedian: nightSpreadMedian,
    nightCount: Object.keys(nightsByDate).length,
    atticTemp: stats(atticTemps),
    humidity: stats(extractValid(bedroomRows, COLS.INDOOR_HUMIDITY, 0, 100)),
    radon: stats(extractValid(masterRows, COLS.INDOOR_RADON, 0, 3700)),
    outdoorPM: stats(extractValid(secondRows, COLS.OUTDOOR_PM25, 0, 1000)),
    ervExceedanceHours: ervExceedanceHours,
    ervExceedanceDays: ervExceedanceDays,
  };
}

/**
 * Week-scoped efficiency analysis. Same thresholds as checkEfficiency() but
 * looks at 7 days instead of 4 hours. Falls back to absolute indoor PM2.5
 * as a proxy when outdoor air is too clean for relative measurement.
 */
function computeWeeklyEfficiency(weekData) {
  if (!weekData || weekData.length === 0) return { type: 'no_data' };

  const thresholds = getEfficiencyThresholds();

  // Same reliability filter as checkEfficiency(), but with explicit NaN guard
  const reliable = weekData.filter(r => {
    const outdoor = parseFloat(r[COLS.OUTDOOR_PM25]);
    const indoor = parseFloat(r[COLS.INDOOR_PM25]);
    return !isNaN(outdoor) && !isNaN(indoor) && outdoor >= thresholds.minOutdoorPM && indoor <= outdoor;
  });

  if (reliable.length >= 5) {
    const efficiencies = reliable
      .map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]))
      .filter(v => !isNaN(v) && v >= 0 && v <= 100);
    if (efficiencies.length === 0) return { type: 'no_data' };
    const medianEff = median(efficiencies);
    const status = medianEff >= thresholds.changeFilter ? 'Good' :
                   medianEff >= thresholds.critical ? 'Change soon' : 'Change now';
    return {
      type: 'measured',
      medianEfficiency: medianEff,
      readingCount: efficiencies.length,
      status: status,
      thresholds: thresholds,
    };
  }

  // Fallback: use absolute indoor PM2.5 as proxy
  const bedroomRows = weekData.filter(r => {
    const room = String(r[COLS.ROOM]).toLowerCase();
    return room.includes('master') || room.includes('second');
  });
  const indoorPMValues = extractValid(bedroomRows, COLS.INDOOR_PM25, 0, 1000);

  if (indoorPMValues.length === 0) return { type: 'no_data' };

  return {
    type: 'proxy',
    avgIndoorPM: average(indoorPMValues),
    maxIndoorPM: Math.max(...indoorPMValues),
    readingCount: indoorPMValues.length,
    reliableCount: reliable.length,
    thresholds: thresholds,
  };
}

// ============================================================================
// WEEKLY REPORT
// ============================================================================

function weeklyReport() {
  const props = PropertiesService.getScriptProperties();
  const email = props.getProperty('ALERT_EMAIL');
  if (!email) return;

  const location = getLocation();
  const filters = getFiltersFromSheet();
  const pressure = checkPressure();
  const weekData = getWeeklyData();
  const trends = computeWeeklyTrends(weekData);
  const efficiency = computeWeeklyEfficiency(weekData);

  let body = `📊 Weekly HVAC Report - ${location.name}\n`;
  body += '═'.repeat(50) + '\n\n';

  // Precompute filter ages (used in both alerts and filter status sections)
  const filterAges = {};
  Object.entries(filters).forEach(([name, f]) => {
    if (f.lastChanged) {
      const days = Math.floor((new Date() - f.lastChanged) / (1000 * 60 * 60 * 24));
      const isZone = name.includes('zone');
      const maxDays = isZone ? (CONFIG.ZONE_FILTER_DAYS[name] || 90) : null;
      filterAges[name] = { days, isZone, maxDays };
    }
  });

  // --- Status summary (Problem 4) ---
  const alerts = [];
  if (efficiency.type === 'measured' && efficiency.medianEfficiency < efficiency.thresholds.changeFilter) {
    alerts.push(`Filter efficiency ${efficiency.medianEfficiency.toFixed(0)}% (below ${efficiency.thresholds.changeFilter}%)`);
  } else if (efficiency.type === 'proxy' && efficiency.avgIndoorPM >= 12) { // EPA 24-hr PM2.5 "Good" limit
    alerts.push(`Indoor PM2.5 elevated: avg ${efficiency.avgIndoorPM.toFixed(1)} μg/m³ — check filters`);
  }
  if (pressure.alerts && pressure.alerts.length > 0) {
    pressure.alerts.forEach(a => alerts.push(a.message ?? String(a)));
  }
  Object.entries(filterAges).forEach(([name, info]) => {
    if (info.isZone && info.days > info.maxDays) {
      alerts.push(`${name} overdue (${info.days - info.maxDays} days past)`);
    }
  });
  if (trends && trends.ervExceedanceDays > 0) {
    alerts.push(`HRV above operating limit: ${trends.ervExceedanceDays} days, ~${trends.ervExceedanceHours}h above ${CONFIG.ERV.maxOperatingTemp}°C`);
  }

  if (alerts.length === 0) {
    body += 'STATUS: All Clear\n';
    body += 'No alerts this week. All systems operating normally.\n\n';
  } else {
    body += `STATUS: ${alerts.length} alert(s) this week\n`;
    alerts.forEach(a => { body += `  - ${a}\n`; });
    body += '\n';
  }

  // --- Weekly Trends (Problem 5) ---
  body += '📊 WEEKLY TRENDS (7 days)\n';
  body += '─'.repeat(40) + '\n';
  if (trends) {
    if (trends.indoorPM) {
      body += `Indoor PM2.5: avg ${trends.indoorPM.avg.toFixed(1)}, range ${trends.indoorPM.min.toFixed(1)}-${trends.indoorPM.max.toFixed(1)} μg/m³\n`;
    }
    if (trends.co2) {
      body += `CO2:          avg ${trends.co2.avg.toFixed(0)}, max ${trends.co2.max.toFixed(0)} ppm\n`;
    }
    if (trends.nightSpreadMedian !== null) {
      body += `Night Temp:   avg ${trends.nightTempAvg.toFixed(1)} °C, ${trends.nightSpreadMedian.toFixed(1)}° typical spread (11pm-7am, ${trends.nightCount} nights)\n`;
      if (trends.nightSpreadMedian > CONFIG.NIGHT_TEMP.maxSpread) {
        body += `              ⚠️ wide overnight spread — check zone dampers/sensors\n`;
      }
    }
    if (trends.humidity) {
      body += `Humidity:     ${trends.humidity.min.toFixed(0)}-${trends.humidity.max.toFixed(0)}%\n`;
    }
    if (trends.radon) {
      body += `Radon:        avg ${trends.radon.avg.toFixed(0)} Bq/m³\n`;
    }
    if (trends.atticTemp) {
      body += `Attic:        ${trends.atticTemp.min.toFixed(1)}-${trends.atticTemp.max.toFixed(1)} °C`;
      if (trends.atticTemp.max >= CONFIG.ERV.maxOperatingTemp) {
        body += ` ⚠️ peak exceeds HRV limit`;
      }
      body += '\n';
      if (trends.ervExceedanceDays > 0) {
        body += `              ${trends.ervExceedanceDays} days, ~${trends.ervExceedanceHours}h above ${CONFIG.ERV.maxOperatingTemp}°C\n`;
      }
    }
  } else {
    body += 'Insufficient data for trends\n';
  }

  // --- Filter Efficiency (Problem 1) ---
  body += '\n📈 FILTER EFFICIENCY\n';
  body += '─'.repeat(40) + '\n';
  if (efficiency.type === 'measured') {
    const icons = { 'Good': '✅ Good', 'Change soon': '⚠️ Change soon', 'Change now': '🚨 Change now' };
    const icon = icons[efficiency.status] || efficiency.status;
    body += `Measured: ${efficiency.medianEfficiency.toFixed(0)}% - ${icon}\n`;
    body += `Based on ${efficiency.readingCount} reliable readings this week\n`;
  } else if (efficiency.type === 'proxy') {
    body += 'Outdoor air too clean for relative efficiency measurement\n';
    body += `Indoor PM2.5 proxy: avg ${efficiency.avgIndoorPM.toFixed(1)}, max ${efficiency.maxIndoorPM.toFixed(1)} μg/m³\n`;
    if (efficiency.avgIndoorPM < 5) {
      body += 'Filters working well (indoor air is clean)\n';
    } else if (efficiency.avgIndoorPM < 12) {
      body += 'Indoor levels moderate - monitor next week\n';
    } else {
      body += 'Indoor levels elevated - check filters\n';
    }
    if (efficiency.reliableCount > 0) {
      body += `(${efficiency.reliableCount} readings met outdoor threshold but fewer than 5 needed)\n`;
    }
  } else {
    body += 'No efficiency data available\n';
  }

  // --- Filter Ages ---
  body += '\n🔧 FILTER STATUS\n';
  body += '─'.repeat(40) + '\n';
  Object.entries(filterAges).forEach(([name, info]) => {
    if (info.isZone) {
      const remaining = info.maxDays - info.days;
      body += `${name}: ${info.days} days (${remaining > 0 ? remaining + ' days until replace' : 'REPLACE NOW'})\n`;
    } else {
      body += `${name}: ${info.days} days (efficiency-based alerts)\n`;
    }
  });

  // --- Pressure (Problem 2) ---
  body += '\n🌡️ PRESSURE (for nerve pain tracking)\n';
  body += '─'.repeat(40) + '\n';
  if (pressure.current) {
    body += `Current: ${pressure.current.toFixed(0)} hPa\n`;
    if (pressure.alerts && pressure.alerts.length > 0) {
      pressure.alerts.forEach(a => { body += `${a.message ?? String(a)}\n`; });
    } else {
      body += 'Stable this week\n';
    }
  } else {
    body += 'Unavailable (weather API error)\n';
  }

  // --- Outdoor Air Quality (Problem 3) ---
  body += '\n🌬️ OUTDOOR AIR (for ERV control)\n';
  body += '─'.repeat(40) + '\n';
  if (trends && trends.outdoorPM) {
    body += `Weekly PM2.5: avg ${trends.outdoorPM.avg.toFixed(1)}, max ${trends.outdoorPM.max.toFixed(1)} μg/m³\n`;
    if (trends.outdoorPM.avg < 12) {
      body += 'Excellent air quality - safe for ERV\n';
    } else if (trends.outdoorPM.avg < 25) {
      body += 'Moderate air quality - ERV operation normal\n';
    } else {
      body += 'Elevated outdoor PM2.5 this week\n';
    }
  } else {
    body += 'No outdoor PM2.5 data this week\n';
  }

  body += '\n' + '═'.repeat(50);
  body += '\n📎 ' + SpreadsheetApp.getActiveSpreadsheet().getUrl();

  MailApp.sendEmail(email, '📊 Weekly HVAC Report', body);
}

// ============================================================================
// DIAGNOSTIC: Analyze efficiency data robustness
// ============================================================================

/**
 * Analyze your actual efficiency data to determine best measurement approach
 * Run this to see outliers, distribution, and test different methods
 */
function analyzeEfficiencyData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const data = sheet.getDataRange().getValues().slice(1);

  console.log('═'.repeat(60));
  console.log('EFFICIENCY DATA ANALYSIS');
  console.log('═'.repeat(60));
  console.log(`Total readings: ${data.length}`);

  // Get all efficiency readings with outdoor PM2.5 context
  const readings = data.map(r => ({
    efficiency: parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0,
    outdoorPM: parseFloat(r[COLS.OUTDOOR_PM25]) || 0,
    indoorPM: parseFloat(r[COLS.INDOOR_PM25]) || 0,
  })).filter(r => !isNaN(r.efficiency));

  console.log(`\nReadings with efficiency data: ${readings.length}`);

  // === OUTLIER ANALYSIS ===
  console.log('\n' + '─'.repeat(50));
  console.log('OUTLIER ANALYSIS');
  console.log('─'.repeat(50));

  const allEff = readings.map(r => r.efficiency);
  const negativeCount = allEff.filter(e => e < 0).length;
  const over100Count = allEff.filter(e => e > 100).length;
  const extremeLow = allEff.filter(e => e < 50).length;

  console.log(`Negative efficiency (indoor > outdoor): ${negativeCount} (${(100*negativeCount/allEff.length).toFixed(1)}%)`);
  console.log(`Over 100% efficiency: ${over100Count} (${(100*over100Count/allEff.length).toFixed(1)}%)`);
  console.log(`Below 50% efficiency: ${extremeLow} (${(100*extremeLow/allEff.length).toFixed(1)}%)`);

  // === DISTRIBUTION BY OUTDOOR PM2.5 ===
  console.log('\n' + '─'.repeat(50));
  console.log('DISTRIBUTION BY OUTDOOR PM2.5 LEVEL');
  console.log('─'.repeat(50));

  const lowOutdoor = readings.filter(r => r.outdoorPM < 5);
  const medOutdoor = readings.filter(r => r.outdoorPM >= 5 && r.outdoorPM < 10);
  const highOutdoor = readings.filter(r => r.outdoorPM >= 10);
  const veryHighOutdoor = readings.filter(r => r.outdoorPM >= 20);

  console.log(`\nOutdoor PM2.5 < 5 μg/m³ (unreliable):`);
  console.log(`  Count: ${lowOutdoor.length} (${(100*lowOutdoor.length/readings.length).toFixed(1)}%)`);
  if (lowOutdoor.length > 0) {
    console.log(`  Efficiency: median ${median(lowOutdoor.map(r=>r.efficiency)).toFixed(1)}%, avg ${average(lowOutdoor.map(r=>r.efficiency)).toFixed(1)}%`);
  }

  console.log(`\nOutdoor PM2.5 5-10 μg/m³ (moderate confidence):`);
  console.log(`  Count: ${medOutdoor.length} (${(100*medOutdoor.length/readings.length).toFixed(1)}%)`);
  if (medOutdoor.length > 0) {
    console.log(`  Efficiency: median ${median(medOutdoor.map(r=>r.efficiency)).toFixed(1)}%, avg ${average(medOutdoor.map(r=>r.efficiency)).toFixed(1)}%`);
  }

  console.log(`\nOutdoor PM2.5 >= 10 μg/m³ (high confidence):`);
  console.log(`  Count: ${highOutdoor.length} (${(100*highOutdoor.length/readings.length).toFixed(1)}%)`);
  if (highOutdoor.length > 0) {
    console.log(`  Efficiency: median ${median(highOutdoor.map(r=>r.efficiency)).toFixed(1)}%, avg ${average(highOutdoor.map(r=>r.efficiency)).toFixed(1)}%`);
    console.log(`  Negative readings: ${highOutdoor.filter(r=>r.efficiency<0).length}`);
    console.log(`  Below 50%: ${highOutdoor.filter(r=>r.efficiency<50).length}`);
  }

  console.log(`\nOutdoor PM2.5 >= 20 μg/m³ (very high confidence):`);
  console.log(`  Count: ${veryHighOutdoor.length} (${(100*veryHighOutdoor.length/readings.length).toFixed(1)}%)`);
  if (veryHighOutdoor.length > 0) {
    console.log(`  Efficiency: median ${median(veryHighOutdoor.map(r=>r.efficiency)).toFixed(1)}%, avg ${average(veryHighOutdoor.map(r=>r.efficiency)).toFixed(1)}%`);
  }

  // === COMPARE MEASUREMENT METHODS ===
  console.log('\n' + '─'.repeat(50));
  console.log('COMPARING MEASUREMENT METHODS (last 4 hours simulation)');
  console.log('─'.repeat(50));

  // Simulate what we'd get from last 96 readings
  const recent = readings.slice(-96);
  const recentHighConf = recent.filter(r => r.outdoorPM >= 10);

  if (recentHighConf.length >= 5) {
    const effValues = recentHighConf.map(r => r.efficiency);

    // Method 1: Simple median
    const simpleMedian = median(effValues);

    // Method 2: Average
    const simpleAvg = average(effValues);

    // Method 3: Trimmed mean (exclude top/bottom 10%)
    const sorted = effValues.slice().sort((a,b) => a-b);
    const trimCount = Math.floor(sorted.length * 0.1);
    const trimmed = sorted.slice(trimCount, sorted.length - trimCount);
    const trimmedMean = average(trimmed);

    // Method 4: Median excluding negatives
    const positiveOnly = effValues.filter(e => e >= 0);
    const medianPositive = median(positiveOnly);

    // Method 5: IQR-based (exclude outliers outside 1.5*IQR)
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    const iqrFiltered = effValues.filter(e => e >= q1 - 1.5*iqr && e <= q3 + 1.5*iqr);
    const iqrMedian = median(iqrFiltered);

    console.log(`\nRecent high-confidence readings: ${recentHighConf.length}`);
    console.log(`\nMethod comparison:`);
    console.log(`  1. Simple median:           ${simpleMedian.toFixed(1)}%`);
    console.log(`  2. Simple average:          ${simpleAvg.toFixed(1)}%`);
    console.log(`  3. Trimmed mean (10%):      ${trimmedMean.toFixed(1)}%`);
    console.log(`  4. Median (positives only): ${medianPositive.toFixed(1)}% (n=${positiveOnly.length})`);
    console.log(`  5. IQR-filtered median:     ${iqrMedian.toFixed(1)}% (n=${iqrFiltered.length})`);

    console.log(`\nRange in data:`);
    console.log(`  Min: ${Math.min(...effValues).toFixed(1)}%`);
    console.log(`  Max: ${Math.max(...effValues).toFixed(1)}%`);
    console.log(`  Q1: ${q1.toFixed(1)}%, Q3: ${q3.toFixed(1)}%, IQR: ${iqr.toFixed(1)}%`);
  } else {
    console.log(`\nInsufficient recent high-confidence data (${recentHighConf.length} readings)`);
  }

  // === RECOMMENDATION ===
  console.log('\n' + '═'.repeat(60));
  console.log('RECOMMENDATION');
  console.log('═'.repeat(60));

  const negPct = 100 * negativeCount / allEff.length;
  if (negPct > 5) {
    console.log(`\n⚠️ ${negPct.toFixed(1)}% negative readings detected`);
    console.log('   This suggests indoor PM spikes (cooking, cleaning).');
    console.log('   Recommend: Filter out negative values before calculating.');
  }

  if (highOutdoor.length < readings.length * 0.1) {
    console.log(`\n⚠️ Only ${(100*highOutdoor.length/readings.length).toFixed(1)}% of readings are high-confidence`);
    console.log('   Your outdoor air is often clean (good for health, hard for measurement).');
    console.log('   Recommend: Lower threshold to 5 μg/m³ or use longer time windows.');
  }

  console.log('\nCurrent implementation uses: Simple median with outdoor PM >= 10 μg/m³');
}

/**
 * Analyze efficiency before/after filter replacements
 * Run this to see if replacements actually improved performance
 */
function analyzeFilterReplacements() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const data = sheet.getDataRange().getValues().slice(1);
  const filters = getFiltersFromSheet();

  console.log('═'.repeat(60));
  console.log('FILTER REPLACEMENT ANALYSIS');
  console.log('═'.repeat(60));

  Object.entries(filters).forEach(([name, filter]) => {
    if (!filter.lastChanged) return;

    const changeDate = filter.lastChanged;
    console.log(`\n📊 ${name.toUpperCase()} - Replaced ${changeDate.toISOString().split('T')[0]}`);
    console.log('─'.repeat(50));

    // Get 30 days before and after
    const before = data.filter(r => {
      const ts = new Date(r[COLS.TIMESTAMP]);
      return ts >= new Date(changeDate - 30*24*60*60*1000) && ts < changeDate;
    });

    const after = data.filter(r => {
      const ts = new Date(r[COLS.TIMESTAMP]);
      return ts >= changeDate && ts <= new Date(changeDate.getTime() + 30*24*60*60*1000);
    });

    // High-confidence readings only
    const beforeHC = before.filter(r => parseFloat(r[COLS.OUTDOOR_PM25]) >= 10);
    const afterHC = after.filter(r => parseFloat(r[COLS.OUTDOOR_PM25]) >= 10);

    if (beforeHC.length > 0) {
      const eff = median(beforeHC.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0));
      console.log(`BEFORE: ${eff.toFixed(0)}% efficiency (${beforeHC.length} readings)`);
    } else {
      console.log('BEFORE: insufficient data');
    }

    if (afterHC.length > 0) {
      const eff = median(afterHC.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0));
      console.log(`AFTER:  ${eff.toFixed(0)}% efficiency (${afterHC.length} readings)`);
    } else {
      console.log('AFTER:  insufficient data');
    }

    if (beforeHC.length > 0 && afterHC.length > 0) {
      const beforeEff = median(beforeHC.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0));
      const afterEff = median(afterHC.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0));
      const improvement = afterEff - beforeEff;
      console.log(`IMPROVEMENT: ${improvement >= 0 ? '+' : ''}${improvement.toFixed(0)}%`);
    }
  });
}

// ============================================================================
// SETUP & TESTING
// ============================================================================

function setupTriggers() {
  // Clear existing
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // Hourly check
  ScriptApp.newTrigger('runAllChecks').timeBased().everyHours(1).create();

  // Weekly report (Sunday 9am)
  ScriptApp.newTrigger('weeklyReport').timeBased().onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(9).create();

  // Monthly calibration (1st of month, 3am)
  ScriptApp.newTrigger('calibrateEfficiencyThresholds').timeBased().onMonthDay(1).atHour(3).create();

  console.log('✅ Triggers set up!');
  console.log('\nScript Properties to configure:');
  console.log('  ALERT_EMAIL       - Your email');
  console.log('  ALERT_EMAIL_2     - Wife email');
  console.log('  LOCATION_LAT      - Latitude');
  console.log('  LOCATION_LON      - Longitude');
  console.log('  LOCATION_NAME     - Display name');
  console.log('  LOCATION_TIMEZONE - Timezone');
  console.log('\nFunctions:');
  console.log('  test()                          - Test all checks');
  console.log('  testIndoorSpike()               - Test indoor spike detection');
  console.log('  calibrateEfficiencyThresholds() - Calibrate from your data');
  console.log('  analyzeFilterReplacements()     - See before/after performance');
}

function test() {
  console.log('═'.repeat(60));
  console.log('HVAC MONITOR v3');
  console.log('═'.repeat(60));

  console.log('\n📍 Location:', JSON.stringify(getLocation()));

  console.log('\n🔧 Filter History:');
  const filters = getFiltersFromSheet();
  Object.entries(filters).forEach(([k, v]) => {
    const days = v.lastChanged ? Math.floor((new Date() - v.lastChanged) / (1000*60*60*24)) : 'unknown';
    console.log(`  ${k}: ${days} days since change (${v.model || 'unknown model'})`);
  });

  console.log('\n📊 EFFICIENCY (ERV/Main change filter signal):');
  const efficiency = checkEfficiency();
  if (efficiency.medianEfficiency) {
    const thresh = efficiency.thresholds;
    console.log(`  Season: ${getSeason()}, using outdoor PM >= ${thresh.minOutdoorPM} μg/m³`);
    console.log(`  Current: ${efficiency.medianEfficiency.toFixed(0)}%`);
    console.log(`  Thresholds: warning < ${thresh.changeFilter}%, critical < ${thresh.critical}%`);
    console.log(`  Status: ${efficiency.medianEfficiency >= thresh.changeFilter ? '✅ Good' : efficiency.medianEfficiency >= thresh.critical ? '⚠️ Change soon' : '🚨 Change now!'}`);
    console.log(`  Based on ${efficiency.readingCount} reliable readings`);
  } else {
    console.log(`  Season: ${getSeason()}`);
    console.log('  Outdoor air too clean for reliable measurement');
  }

  console.log('\n🔄 ZONE FILTERS (time-based):');
  const zoneFilters = checkZoneFilters();
  Object.entries(CONFIG.ZONE_FILTER_DAYS).forEach(([key, maxDays]) => {
    const f = filters[key];
    if (f && f.lastChanged) {
      const days = Math.floor((new Date() - f.lastChanged) / (1000*60*60*24));
      const remaining = maxDays - days;
      console.log(`  ${key}: ${days}/${maxDays} days (${remaining > 0 ? remaining + ' days left' : 'REPLACE NOW'})`);
    } else {
      console.log(`  ${key}: no change date recorded`);
    }
  });

  console.log('\n🌡️ Pressure (wife - nerve pain):');
  const pressure = checkPressure();
  if (pressure.current) {
    console.log(`  Current: ${pressure.current.toFixed(0)} hPa`);
    console.log(`  Alerts: ${pressure.alerts.length}`);
  }

  console.log('\n🌬️ Outdoor AQI (wife - ERV control):');
  const aqi = checkOutdoorAQI();
  if (aqi.current) {
    console.log(`  Current PM2.5: ${aqi.current.toFixed(1)} μg/m³`);
    console.log(`  1h avg: ${aqi.avg1h?.toFixed(1)} μg/m³`);
    console.log(`  ERV state: ${aqi.state || 'NORMAL'}`);
  }

  console.log('\n🍳 Indoor PM Spike:');
  const indoorSpike = checkIndoorSpike();
  if (indoorSpike.spikeAmount && indoorSpike.spikeAmount > 0) {
    console.log(`  Indoor: ${indoorSpike.indoor?.toFixed(1)} μg/m³`);
    console.log(`  Outdoor: ${indoorSpike.outdoor?.toFixed(1)} μg/m³`);
    console.log(`  Spike: +${indoorSpike.spikeAmount?.toFixed(1)} μg/m³`);
    console.log(`  Status: ${indoorSpike.spikeAmount >= CONFIG.INDOOR_SPIKE.threshold ? '⚠️ SPIKE DETECTED' : 'Minor elevation'}`);
  } else {
    console.log(`  No spike (indoor <= outdoor)`);
  }

  console.log('\n💨 CO2:');
  const co2 = checkCO2();
  console.log(`  Current: ${co2.current?.toFixed(0) || 'N/A'} ppm`);

  console.log('\n📡 Data Collection:');
  const collection = checkDataCollection();
  console.log(`  Status: ${collection.status}`);
  Object.entries(CONFIG.EXPECTED_SENSORS).forEach(([type, spec]) => {
    const seen = collection.lastSeen && collection.lastSeen[type];
    const label = seen
      ? `${((new Date() - seen.timestamp) / 3600000).toFixed(1)}h ago`
      : `not seen in scan window`;
    console.log(`  ${type} (maxGap=${spec.maxGapHours}h): ${label}`);
  });
  if (collection.stoppedSensors && collection.stoppedSensors.length > 0) {
    console.log(`  ⚠️ stopped: ${collection.stoppedSensors.map(s => s.sensorType).join(', ')}`);
  }

  console.log('\n🏠 Indoor Baseline (master_bedroom):');
  const baseline = checkIndoorBaseline();
  if (baseline.sampleCount !== undefined) {
    console.log(`  Samples: ${baseline.sampleCount} over 90-min window`);
    console.log(`  30-min median: ${baseline.now30Med?.toFixed(1)} μg/m³ (threshold=${CONFIG.INDOOR_BASELINE.absoluteThreshold})`);
    console.log(`  Prev 30-min median: ${baseline.prev30Med?.toFixed(1)} μg/m³`);
    console.log(`  90-min median: ${baseline.full90Med?.toFixed(1)} μg/m³`);
    console.log(`  Latest outdoor: ${baseline.latestOutdoor?.toFixed(1)} μg/m³ (gate=${CONFIG.INDOOR_BASELINE.outdoorGate})`);
    console.log(`  Alerts: ${baseline.alerts.length}${baseline.alerts[0] ? ' — ' + baseline.alerts[0].level : ''}`);
  } else {
    console.log(`  ${baseline.note || 'no alerts'}`);
  }

  console.log('\n' + '═'.repeat(60));
  console.log(`Monitor version: ${MONITOR_VERSION}`);
  console.log('Running full check...');
  const results = runAllChecks();
  console.log(`Alerts for you: ${results.alerts.you.length}`);
  console.log(`Alerts for wife: ${results.alerts.wife.length}`);
}

function getStatus() {
  const pressure = checkPressure();
  const aqi = checkOutdoorAQI();
  const efficiency = checkEfficiency();
  const indoorSpike = checkIndoorSpike();

  return {
    timestamp: new Date().toISOString(),
    location: getLocation().name,

    // THE KEY METRIC - tells you when to change filter
    filterEfficiency: efficiency.medianEfficiency
      ? `${efficiency.medianEfficiency.toFixed(0)}% (${efficiency.medianEfficiency >= 75 ? 'good' : 'CHANGE FILTER'})`
      : 'insufficient data',

    // Indoor spike status
    indoorSpike: indoorSpike.spikeAmount > 0
      ? `+${indoorSpike.spikeAmount.toFixed(1)} μg/m³ (indoor: ${indoorSpike.indoor?.toFixed(1)}, outdoor: ${indoorSpike.outdoor?.toFixed(1)})`
      : 'none',

    // For wife
    pressure: pressure.current ? `${pressure.current.toFixed(0)} hPa` : 'N/A',
    outdoorPM25: aqi.current ? `${aqi.current.toFixed(1)} μg/m³` : 'N/A',
    ervState: aqi.state || 'NORMAL',
  };
}

/**
 * Test indoor spike detection
 * Run this to see current indoor/outdoor PM levels and spike status
 */
function testIndoorSpike() {
  console.log('═'.repeat(60));
  console.log('INDOOR SPIKE DETECTION TEST');
  console.log('═'.repeat(60));

  // Clear cooldown for testing
  const props = PropertiesService.getScriptProperties();
  const hadCooldown = props.getProperty('INDOOR_SPIKE_ALERTED');
  if (hadCooldown) {
    console.log(`\nNote: Clearing previous cooldown from ${hadCooldown}`);
    props.deleteProperty('INDOOR_SPIKE_ALERTED');
  }

  const result = checkIndoorSpike();

  console.log('\n📊 Current Readings:');
  console.log(`  Indoor PM2.5:  ${result.indoor?.toFixed(1) || 'N/A'} μg/m³`);
  console.log(`  Outdoor PM2.5: ${result.outdoor?.toFixed(1) || 'N/A'} μg/m³`);
  console.log(`  Difference:    ${result.spikeAmount?.toFixed(1) || 'N/A'} μg/m³`);

  console.log('\n⚙️ Thresholds:');
  console.log(`  Spike threshold:   ${CONFIG.INDOOR_SPIKE.threshold} μg/m³ (indoor must exceed outdoor by this)`);
  console.log(`  Max outdoor for ERV: ${CONFIG.INDOOR_SPIKE.maxOutdoorPM} μg/m³`);
  console.log(`  Cooldown:          ${CONFIG.INDOOR_SPIKE.cooldownMinutes} minutes`);

  const isSpike = (result.spikeAmount || 0) >= CONFIG.INDOOR_SPIKE.threshold;
  console.log('\n🔍 Analysis:');
  console.log(`  Is spike: ${isSpike ? 'YES' : 'NO'}`);
  if (isSpike) {
    console.log(`  Outdoor clean: ${result.outdoorClean ? 'YES - ERV will help' : 'NO - ERV won\'t help much'}`);
  }

  console.log('\n📧 Alerts generated:', result.alerts.length);
  result.alerts.forEach(a => {
    console.log('\n' + '─'.repeat(50));
    console.log(a.message);
  });

  // Restore cooldown if it was set
  if (hadCooldown) {
    props.setProperty('INDOOR_SPIKE_ALERTED', hadCooldown);
    console.log(`\nNote: Restored cooldown to ${hadCooldown}`);
  }

  console.log('\n' + '═'.repeat(60));
  return result;
}
