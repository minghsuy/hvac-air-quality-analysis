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

const CONFIG = {
  SHEET_NAME: 'Cleaned_Data_20250831',
  FILTER_SHEET: 'Filter_Changes',

  // How long without data before alerting
  DATA_GAP_HOURS: 2,

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
  return { alerts, pressure, aqi, efficiency, indoorSpike, zoneFilters, co2, data };
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

  // Scan last 50 rows to find most recent timestamp per sensor type
  const numRows = Math.min(50, lastRow - 1);
  const data = sheet.getRange(lastRow - numRows + 1, 1, numRows, 4).getValues();
  const now = new Date();
  const props = PropertiesService.getScriptProperties();

  const lastSeen = {};  // { sensorType: { timestamp, room } }
  data.forEach(row => {
    const ts = new Date(row[COLS.TIMESTAMP]);
    const room = String(row[COLS.ROOM]);
    const sensorType = String(row[COLS.SENSOR_TYPE]);
    if (!sensorType || sensorType === 'undefined') return;

    if (!lastSeen[sensorType] || ts > lastSeen[sensorType].timestamp) {
      lastSeen[sensorType] = { timestamp: ts, room };
    }
  });

  const stoppedSensors = [];
  const resumedSensors = [];

  Object.entries(lastSeen).forEach(([sensorType, info]) => {
    const hoursSince = (now - info.timestamp) / (1000 * 60 * 60);
    const gapKey = `DATA_GAP_${sensorType}`;

    if (hoursSince > CONFIG.DATA_GAP_HOURS) {
      // Only alert once per sensor per gap
      if (!props.getProperty(gapKey)) {
        stoppedSensors.push({ sensorType, room: info.room, hoursSince });
        props.setProperty(gapKey, now.toISOString());
      }
    } else {
      // Check if this sensor is recovering from a gap
      const wasDown = props.getProperty(gapKey);
      if (wasDown) {
        resumedSensors.push({ sensorType, room: info.room, downSince: wasDown });
        props.deleteProperty(gapKey);
      }
    }
  });

  // Build alert
  let alert = null;
  if (stoppedSensors.length > 0) {
    const details = stoppedSensors
      .map(s => `  • ${s.room} (${s.sensorType}): ${s.hoursSince.toFixed(1)}h ago`)
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

  const status = stoppedSensors.length > 0 ? 'PARTIAL' :
                 Object.keys(lastSeen).length === 0 ? 'NO_DATA' : 'OK';

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
  const aqi = checkOutdoorAQI();
  const efficiency = checkEfficiency();

  let body = `📊 Weekly HVAC Report - ${location.name}\n`;
  body += '═'.repeat(50) + '\n\n';

  // Filter Efficiency - THE KEY METRIC
  body += '📈 FILTER EFFICIENCY (the "change filter" signal)\n';
  body += '─'.repeat(40) + '\n';
  if (efficiency.medianEfficiency) {
    const status = efficiency.medianEfficiency >= 75 ? '✅ Good' :
                   efficiency.medianEfficiency >= 65 ? '⚠️ Change soon' : '🚨 Change now';
    body += `Current: ${efficiency.medianEfficiency.toFixed(0)}% - ${status}\n`;
    body += `Based on ${efficiency.readingCount} reliable readings\n`;
  } else {
    body += 'Outdoor air too clean for reliable measurement this week\n';
  }

  // Filter Ages
  body += '\n🔧 FILTER STATUS\n';
  body += '─'.repeat(40) + '\n';
  Object.entries(filters).forEach(([name, f]) => {
    if (f.lastChanged) {
      const days = Math.floor((new Date() - f.lastChanged) / (1000 * 60 * 60 * 24));
      const isZone = name.includes('zone');
      if (isZone) {
        const maxDays = CONFIG.ZONE_FILTER_DAYS[name] || 90;
        const remaining = maxDays - days;
        body += `${name}: ${days} days (${remaining > 0 ? remaining + ' days until replace' : 'REPLACE NOW'})\n`;
      } else {
        body += `${name}: ${days} days (efficiency-based alerts)\n`;
      }
    }
  });

  // Pressure
  body += '\n🌡️ PRESSURE (for nerve pain tracking)\n';
  body += '─'.repeat(40) + '\n';
  if (pressure.current) {
    body += `Current: ${pressure.current.toFixed(0)} hPa\n`;
  }

  // Outdoor AQI
  body += '\n🌬️ OUTDOOR AIR (for ERV control)\n';
  body += '─'.repeat(40) + '\n';
  if (aqi.current) {
    body += `Current PM2.5: ${aqi.current.toFixed(1)} μg/m³\n`;
    body += `ERV recommendation: ${aqi.state || 'NORMAL'}\n`;
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

  console.log('\n📡 Data Collection:', checkDataCollection().status);

  console.log('\n' + '═'.repeat(60));
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
