/**
 * Google Apps Script for HVAC Air Quality Monitoring
 * This script handles the new multi-sensor schema (18 columns)
 * 
 * NEW SCHEMA (as of 2025-08-30):
 * Columns: Timestamp, Sensor_ID, Room, Sensor_Type, Indoor_PM25, Outdoor_PM25, 
 *          Filter_Efficiency, Indoor_CO2, Indoor_VOC, Indoor_NOX, Indoor_Temp, 
 *          Indoor_Humidity, Indoor_Radon, Outdoor_CO2, Outdoor_Temp, 
 *          Outdoor_Humidity, Outdoor_VOC, Outdoor_NOX
 */

// Column indices (0-based)
const COLS = {
  TIMESTAMP: 0,
  SENSOR_ID: 1,
  ROOM: 2,
  SENSOR_TYPE: 3,
  INDOOR_PM25: 4,
  OUTDOOR_PM25: 5,
  FILTER_EFFICIENCY: 6,
  INDOOR_CO2: 7,
  INDOOR_VOC: 8,
  INDOOR_NOX: 9,
  INDOOR_TEMP: 10,
  INDOOR_HUMIDITY: 11,
  INDOOR_RADON: 12,
  OUTDOOR_CO2: 13,
  OUTDOOR_TEMP: 14,
  OUTDOOR_HUMIDITY: 15,
  OUTDOOR_VOC: 16,
  OUTDOOR_NOX: 17
};

/**
 * Get the latest readings for all sensors
 */
function getLatestReadings() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // Skip header row
  const readings = data.slice(1);
  
  // Get latest reading for each sensor
  const latestBySensor = {};
  
  for (let i = readings.length - 1; i >= 0; i--) {
    const row = readings[i];
    const sensorId = row[COLS.SENSOR_ID];
    
    if (sensorId && !latestBySensor[sensorId]) {
      latestBySensor[sensorId] = {
        timestamp: row[COLS.TIMESTAMP],
        sensorId: sensorId,
        room: row[COLS.ROOM],
        sensorType: row[COLS.SENSOR_TYPE],
        indoorPM25: parseFloat(row[COLS.INDOOR_PM25]) || 0,
        outdoorPM25: parseFloat(row[COLS.OUTDOOR_PM25]) || 0,
        filterEfficiency: parseFloat(row[COLS.FILTER_EFFICIENCY]) || 0,
        indoorCO2: parseFloat(row[COLS.INDOOR_CO2]) || 0,
        indoorVOC: parseFloat(row[COLS.INDOOR_VOC]) || 0,
        indoorNOX: parseFloat(row[COLS.INDOOR_NOX]) || 0,
        indoorTemp: parseFloat(row[COLS.INDOOR_TEMP]) || 0,
        indoorHumidity: parseFloat(row[COLS.INDOOR_HUMIDITY]) || 0,
        outdoorCO2: parseFloat(row[COLS.OUTDOOR_CO2]) || 0,
        outdoorTemp: parseFloat(row[COLS.OUTDOOR_TEMP]) || 0,
        outdoorHumidity: parseFloat(row[COLS.OUTDOOR_HUMIDITY]) || 0
      };
    }
  }
  
  return latestBySensor;
}

/**
 * Calculate filter efficiency statistics
 */
function getFilterStats() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // Skip header
  const readings = data.slice(1);
  
  // Get last 24 hours of data
  const now = new Date();
  const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  
  const recentReadings = readings.filter(row => {
    const timestamp = new Date(row[COLS.TIMESTAMP]);
    return timestamp > dayAgo;
  });
  
  if (recentReadings.length === 0) {
    return { message: "No readings in last 24 hours" };
  }
  
  // Calculate stats by sensor
  const statsBySensor = {};
  
  recentReadings.forEach(row => {
    const sensorId = row[COLS.SENSOR_ID];
    const efficiency = parseFloat(row[COLS.FILTER_EFFICIENCY]) || 0;
    
    if (!statsBySensor[sensorId]) {
      statsBySensor[sensorId] = {
        room: row[COLS.ROOM],
        efficiencies: [],
        pm25Indoor: [],
        pm25Outdoor: []
      };
    }
    
    statsBySensor[sensorId].efficiencies.push(efficiency);
    statsBySensor[sensorId].pm25Indoor.push(parseFloat(row[COLS.INDOOR_PM25]) || 0);
    statsBySensor[sensorId].pm25Outdoor.push(parseFloat(row[COLS.OUTDOOR_PM25]) || 0);
  });
  
  // Calculate averages
  const results = {};
  
  Object.keys(statsBySensor).forEach(sensorId => {
    const stats = statsBySensor[sensorId];
    results[sensorId] = {
      room: stats.room,
      avgEfficiency: average(stats.efficiencies),
      minEfficiency: Math.min(...stats.efficiencies),
      maxEfficiency: Math.max(...stats.efficiencies),
      avgIndoorPM25: average(stats.pm25Indoor),
      avgOutdoorPM25: average(stats.pm25Outdoor),
      readingCount: stats.efficiencies.length
    };
  });
  
  return results;
}

/**
 * Send alert if filter efficiency drops below threshold
 */
function checkFilterAlert() {
  const ALERT_THRESHOLD = 85; // Alert if efficiency drops below 85%
  const CRITICAL_THRESHOLD = 80; // Critical if below 80%
  
  const latest = getLatestReadings();
  const alerts = [];
  
  Object.values(latest).forEach(reading => {
    if (reading.filterEfficiency < CRITICAL_THRESHOLD) {
      alerts.push({
        level: 'CRITICAL',
        room: reading.room,
        efficiency: reading.filterEfficiency,
        message: `🚨 CRITICAL: Filter efficiency in ${reading.room} is ${reading.filterEfficiency}% - Replace filter immediately!`
      });
    } else if (reading.filterEfficiency < ALERT_THRESHOLD) {
      alerts.push({
        level: 'WARNING',
        room: reading.room,
        efficiency: reading.filterEfficiency,
        message: `⚠️ WARNING: Filter efficiency in ${reading.room} is ${reading.filterEfficiency}% - Plan replacement soon`
      });
    }
  });
  
  if (alerts.length > 0) {
    // Send email alert (configure email in script properties)
    sendAlertEmail(alerts);
  }
  
  return alerts;
}

/**
 * Send email alert
 */
function sendAlertEmail(alerts) {
  const emailAddress = PropertiesService.getScriptProperties().getProperty('ALERT_EMAIL');
  
  if (!emailAddress) {
    console.log('No alert email configured');
    return;
  }
  
  const subject = alerts.some(a => a.level === 'CRITICAL') 
    ? '🚨 CRITICAL: HVAC Filter Alert' 
    : '⚠️ WARNING: HVAC Filter Alert';
  
  let body = 'HVAC Filter Efficiency Alerts:\n\n';
  
  alerts.forEach(alert => {
    body += alert.message + '\n';
  });
  
  body += '\n\nView dashboard: ' + SpreadsheetApp.getActiveSpreadsheet().getUrl();
  
  MailApp.sendEmail({
    to: emailAddress,
    subject: subject,
    body: body
  });
}

/**
 * Create daily summary
 */
function createDailySummary() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // Get yesterday's data
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const dayBeforeYesterday = new Date(now.getTime() - 48 * 60 * 60 * 1000);
  
  const yesterdayData = data.slice(1).filter(row => {
    const timestamp = new Date(row[COLS.TIMESTAMP]);
    return timestamp > dayBeforeYesterday && timestamp <= yesterday;
  });
  
  if (yesterdayData.length === 0) {
    return { message: "No data for yesterday" };
  }
  
  // Calculate summary stats
  const summary = {
    date: yesterday.toDateString(),
    totalReadings: yesterdayData.length,
    sensors: {},
    overall: {
      avgIndoorPM25: 0,
      avgOutdoorPM25: 0,
      avgEfficiency: 0,
      minEfficiency: 100,
      hoursBelow85: 0
    }
  };
  
  // Group by sensor
  const bySensor = {};
  yesterdayData.forEach(row => {
    const sensorId = row[COLS.SENSOR_ID];
    if (!bySensor[sensorId]) {
      bySensor[sensorId] = [];
    }
    bySensor[sensorId].push(row);
  });
  
  // Calculate per-sensor stats
  Object.keys(bySensor).forEach(sensorId => {
    const sensorData = bySensor[sensorId];
    const efficiencies = sensorData.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0);
    const indoorPM25 = sensorData.map(r => parseFloat(r[COLS.INDOOR_PM25]) || 0);
    
    summary.sensors[sensorId] = {
      room: sensorData[0][COLS.ROOM],
      avgEfficiency: average(efficiencies),
      minEfficiency: Math.min(...efficiencies),
      maxEfficiency: Math.max(...efficiencies),
      avgIndoorPM25: average(indoorPM25),
      readingsBelow85: efficiencies.filter(e => e < 85).length
    };
  });
  
  // Calculate overall stats
  const allEfficiencies = yesterdayData.map(r => parseFloat(r[COLS.FILTER_EFFICIENCY]) || 0);
  const allIndoorPM25 = yesterdayData.map(r => parseFloat(r[COLS.INDOOR_PM25]) || 0);
  const allOutdoorPM25 = yesterdayData.map(r => parseFloat(r[COLS.OUTDOOR_PM25]) || 0);
  
  summary.overall.avgEfficiency = average(allEfficiencies);
  summary.overall.minEfficiency = Math.min(...allEfficiencies);
  summary.overall.avgIndoorPM25 = average(allIndoorPM25);
  summary.overall.avgOutdoorPM25 = average(allOutdoorPM25);
  summary.overall.hoursBelow85 = allEfficiencies.filter(e => e < 85).length * 5 / 60; // 5-minute intervals
  
  return summary;
}

/**
 * Helper function to calculate average
 */
function average(arr) {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/**
 * Set up triggers (run once)
 */
function setupTriggers() {
  // Remove existing triggers
  ScriptApp.getProjectTriggers().forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
  });
  
  // Check for alerts every hour
  ScriptApp.newTrigger('checkFilterAlert')
    .timeBased()
    .everyHours(1)
    .create();
  
  // Create daily summary at 8 AM
  ScriptApp.newTrigger('createDailySummary')
    .timeBased()
    .atHour(8)
    .everyDays(1)
    .create();
}

/**
 * Test function to verify everything works
 */
function test() {
  console.log('Testing Apps Script...');
  
  // Test latest readings
  const latest = getLatestReadings();
  console.log('Latest readings:', latest);
  
  // Test filter stats
  const stats = getFilterStats();
  console.log('Filter stats:', stats);
  
  // Test alerts
  const alerts = checkFilterAlert();
  console.log('Alerts:', alerts);
  
  // Test daily summary
  const summary = createDailySummary();
  console.log('Daily summary:', summary);
  
  return {
    latest: latest,
    stats: stats,
    alerts: alerts,
    summary: summary
  };
}