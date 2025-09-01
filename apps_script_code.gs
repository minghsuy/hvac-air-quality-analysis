/**
 * Google Apps Script for HVAC Air Quality Monitoring
 * Smart alerting system with outdoor PM2.5 confidence levels
 * 
 * Features:
 * - Weighted efficiency based on outdoor PM2.5 levels
 * - Activity spike filtering using median calculations
 * - Confidence-based alerting to reduce false positives
 * - Trend analysis for gradual filter degradation
 * 
 * SCHEMA (18 columns):
 * Timestamp, Sensor_ID, Room, Sensor_Type, Indoor_PM25, Outdoor_PM25, 
 * Filter_Efficiency, Indoor_CO2, Indoor_VOC, Indoor_NOX, Indoor_Temp, 
 * Indoor_Humidity, Indoor_Radon, Outdoor_CO2, Outdoor_Temp, 
 * Outdoor_Humidity, Outdoor_VOC, Outdoor_NOX
 */

// Configuration
const SHEET_NAME = 'Cleaned_Data_20250831';
const DATA_GAP_HOURS = 2;  // Alert if no data for 2 hours

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
 * Smart efficiency check with outdoor PM2.5 consideration
 * Main alerting function with confidence levels
 */
function checkLatestEfficiency() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  
  if (lastRow <= 100) return; // Need enough data
  
  // Get last 4 hours of data (48 readings per sensor)
  const numRows = Math.min(96, lastRow - 1);  // 96 = 48 readings * 2 sensors
  const startRow = Math.max(2, lastRow - numRows + 1);
  const recentData = sheet.getRange(startRow, 1, numRows, 18).getValues();
  
  // Group by sensor
  const sensorData = {};
  recentData.forEach(row => {
    const sensorId = row[COLS.SENSOR_ID];
    if (!sensorData[sensorId]) {
      sensorData[sensorId] = {
        room: row[COLS.ROOM],
        readings: []
      };
    }
    sensorData[sensorId].readings.push({
      efficiency: parseFloat(row[COLS.FILTER_EFFICIENCY]) || 0,
      indoorPM25: parseFloat(row[COLS.INDOOR_PM25]) || 0,
      outdoorPM25: parseFloat(row[COLS.OUTDOOR_PM25]) || 0,
      timestamp: new Date(row[COLS.TIMESTAMP])
    });
  });
  
  const alerts = [];
  
  Object.entries(sensorData).forEach(([sensorId, data]) => {
    // Separate readings by outdoor PM2.5 reliability
    const reliableReadings = data.readings.filter(r => r.outdoorPM25 >= 5);
    const veryReliableReadings = data.readings.filter(r => r.outdoorPM25 >= 10);
    const recent6 = data.readings.slice(-6); // Last 30 mins
    
    // PRIORITIZE high outdoor PM2.5 readings (most reliable)
    let efficiencyToCheck = null;
    let confidence = '';
    
    if (veryReliableReadings.length >= 3) {
      // HIGH CONFIDENCE: Outdoor PM2.5 > 10
      const efficiencies = veryReliableReadings.slice(-6).map(r => r.efficiency);
      efficiencyToCheck = median(efficiencies);
      confidence = 'HIGH CONFIDENCE (outdoor PM2.5 > 10)';
      
      // More aggressive thresholds when we're confident
      if (efficiencyToCheck < 85) {
        alerts.push({
          level: 'WARNING',
          message: `⚠️ ${confidence}: ${data.room} efficiency at ${efficiencyToCheck.toFixed(1)}% - Filter struggling with high pollution`
        });
      }
      if (efficiencyToCheck < 75) {
        alerts.push({
          level: 'CRITICAL',
          message: `🚨 ${confidence}: ${data.room} efficiency at ${efficiencyToCheck.toFixed(1)}% - Replace filter NOW!`
        });
      }
    } else if (reliableReadings.length >= 6) {
      // MEDIUM CONFIDENCE: Outdoor PM2.5 5-10
      const efficiencies = reliableReadings.slice(-12).map(r => r.efficiency);
      efficiencyToCheck = median(efficiencies);
      confidence = 'MEDIUM CONFIDENCE (outdoor PM2.5: 5-10)';
      
      // Standard thresholds
      if (efficiencyToCheck < 80) {
        alerts.push({
          level: 'WARNING',
          message: `⚠️ ${confidence}: ${data.room} efficiency at ${efficiencyToCheck.toFixed(1)}%`
        });
      }
    } else {
      // LOW CONFIDENCE: Outdoor PM2.5 < 5
      // Only alert if there's a clear problem across many readings
      const lowPMreadings = data.readings.filter(r => r.outdoorPM25 < 5);
      if (lowPMreadings.length >= 20) {
        const efficiencies = lowPMreadings.map(r => r.efficiency);
        const medianEff = median(efficiencies);
        
        // Only alert if consistently very low
        if (medianEff < 70) {
          alerts.push({
            level: 'INFO',
            message: `ℹ️ LOW CONFIDENCE: ${data.room} showing ${medianEff.toFixed(1)}% efficiency (outdoor PM2.5 < 5 - may be noise)`
          });
        }
      }
    }
    
    // Check absolute indoor PM2.5 (always relevant)
    const highIndoorReadings = recent6.filter(r => r.indoorPM25 > 12);
    const highOutdoorContext = recent6.filter(r => r.outdoorPM25 > 20);
    
    if (highIndoorReadings.length >= 4 && highOutdoorContext.length === 0) {
      // High indoor WITHOUT high outdoor = filter problem or indoor source
      const medianIndoor = median(highIndoorReadings.map(r => r.indoorPM25));
      alerts.push({
        level: 'WARNING',
        message: `⚠️ INDOOR SOURCE: ${data.room} PM2.5 at ${medianIndoor.toFixed(1)} μg/m³ (outdoor is clean)`
      });
    }
  });
  
  // Smart alert suppression based on conditions
  const shouldSend = shouldSendAlertNow(alerts);
  
  if (shouldSend && alerts.length > 0) {
    sendAlertEmail(alerts);
  }
  
  return alerts;
}

/**
 * Check if data collection has stopped
 */
function checkDataCollection() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  
  if (lastRow <= 1) return; // No data
  
  // Get the last timestamp
  const lastTimestamp = sheet.getRange(lastRow, COLS.TIMESTAMP + 1).getValue();
  const lastTime = new Date(lastTimestamp);
  const now = new Date();
  const hoursSinceLastData = (now - lastTime) / (1000 * 60 * 60);
  
  if (hoursSinceLastData > DATA_GAP_HOURS) {
    const emailAddress = PropertiesService.getScriptProperties().getProperty('ALERT_EMAIL');
    const subject = '🚨 Air Quality Data Collection Stopped';
    const body = `Data collection has stopped!\n\n` +
                 `Last data received: ${lastTime}\n` +
                 `Hours since last data: ${hoursSinceLastData.toFixed(1)}\n\n` +
                 `Check the Unifi Gateway:\n` +
                 `1. SSH to your gateway (192.168.X.X)\n` +
                 `2. Run: /data/scripts/STATUS.sh\n` +
                 `3. Run: /data/scripts/SETUP_AFTER_FIRMWARE_UPDATE.sh if needed`;
    
    MailApp.sendEmail(emailAddress, subject, body);
  }
}

/**
 * Determine if we should send alert based on context
 */
function shouldSendAlertNow(alerts) {
  const hour = new Date().getHours();
  const hasHighConfidence = alerts.some(a => a.message.includes('HIGH CONFIDENCE'));
  const hasCritical = alerts.some(a => a.level === 'CRITICAL');
  
  // Always send high confidence or critical alerts
  if (hasHighConfidence || hasCritical) {
    return true;
  }
  
  // Suppress low confidence during activity hours
  const isQuietHours = hour < 7 || hour > 22;
  const hasOnlyLowConfidence = alerts.every(a => a.message.includes('LOW CONFIDENCE'));
  
  if (hasOnlyLowConfidence && !isQuietHours) {
    return false; // Don't bother user with uncertain readings
  }
  
  return true;
}

/**
 * Calculate weighted efficiency score based on outdoor PM2.5
 */
function getWeightedEfficiencyScore(readings) {
  if (readings.length === 0) return null;
  
  let totalWeight = 0;
  let weightedSum = 0;
  
  readings.forEach(r => {
    // Weight based on outdoor PM2.5 (higher outdoor = more reliable)
    let weight = 0;
    if (r.outdoorPM25 < 2) {
      weight = 0.1; // Almost ignore
    } else if (r.outdoorPM25 < 5) {
      weight = 0.3; // Low confidence
    } else if (r.outdoorPM25 < 10) {
      weight = 0.7; // Medium confidence
    } else if (r.outdoorPM25 < 20) {
      weight = 1.0; // High confidence
    } else {
      weight = 1.5; // Very high confidence
    }
    
    weightedSum += r.efficiency * weight;
    totalWeight += weight;
  });
  
  return totalWeight > 0 ? weightedSum / totalWeight : null;
}

/**
 * Analyze performance during high pollution periods
 */
function analyzeHighPollutionPerformance() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues().slice(1);
  
  // Get last 24 hours
  const now = new Date();
  const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  
  const recentData = data.filter(row => new Date(row[COLS.TIMESTAMP]) > dayAgo);
  
  // Find high pollution periods (outdoor PM2.5 > 10)
  const highPollutionData = recentData.filter(row => 
    parseFloat(row[COLS.OUTDOOR_PM25]) > 10
  );
  
  if (highPollutionData.length === 0) {
    return {
      message: "No high pollution periods in last 24 hours - efficiency measurements may be unreliable"
    };
  }
  
  // Analyze performance during high pollution
  const performanceByRoom = {};
  
  highPollutionData.forEach(row => {
    const room = row[COLS.ROOM];
    if (!performanceByRoom[room]) {
      performanceByRoom[room] = {
        efficiencies: [],
        outdoorPM25: [],
        indoorPM25: []
      };
    }
    performanceByRoom[room].efficiencies.push(parseFloat(row[COLS.FILTER_EFFICIENCY]));
    performanceByRoom[room].outdoorPM25.push(parseFloat(row[COLS.OUTDOOR_PM25]));
    performanceByRoom[room].indoorPM25.push(parseFloat(row[COLS.INDOOR_PM25]));
  });
  
  const results = {};
  Object.entries(performanceByRoom).forEach(([room, data]) => {
    results[room] = {
      medianEfficiency: median(data.efficiencies),
      avgOutdoorPM25: average(data.outdoorPM25),
      avgIndoorPM25: average(data.indoorPM25),
      dataPoints: data.efficiencies.length,
      confidenceLevel: data.efficiencies.length >= 6 ? 'HIGH' : 'MEDIUM'
    };
  });
  
  return results;
}

/**
 * Weekly trend report with analysis
 */
function weeklyTrendReport() {
  const emailAddress = PropertiesService.getScriptProperties().getProperty('ALERT_EMAIL');
  if (!emailAddress) return;
  
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues().slice(1);
  
  // Get last 7 days
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  
  const weekData = data.filter(row => new Date(row[COLS.TIMESTAMP]) > weekAgo);
  
  // Analyze by room
  const roomStats = {};
  weekData.forEach(row => {
    const room = row[COLS.ROOM];
    const outdoorPM = parseFloat(row[COLS.OUTDOOR_PM25]);
    
    if (!roomStats[room]) {
      roomStats[room] = {
        allEfficiencies: [],
        reliableEfficiencies: [], // outdoor PM > 5
        veryReliableEfficiencies: [] // outdoor PM > 10
      };
    }
    
    const eff = parseFloat(row[COLS.FILTER_EFFICIENCY]);
    roomStats[room].allEfficiencies.push(eff);
    
    if (outdoorPM >= 5) {
      roomStats[room].reliableEfficiencies.push(eff);
    }
    if (outdoorPM >= 10) {
      roomStats[room].veryReliableEfficiencies.push(eff);
    }
  });
  
  // Build report
  let body = '📊 Weekly Air Quality Report\n';
  body += `Period: ${weekAgo.toDateString()} to ${now.toDateString()}\n\n`;
  
  Object.entries(roomStats).forEach(([room, stats]) => {
    body += `📍 ${room.toUpperCase()}\n`;
    
    if (stats.veryReliableEfficiencies.length > 0) {
      const medianEff = median(stats.veryReliableEfficiencies);
      body += `  High Confidence Efficiency: ${medianEff.toFixed(1)}% (${stats.veryReliableEfficiencies.length} readings with outdoor PM2.5 > 10)\n`;
    } else if (stats.reliableEfficiencies.length > 0) {
      const medianEff = median(stats.reliableEfficiencies);
      body += `  Medium Confidence Efficiency: ${medianEff.toFixed(1)}% (${stats.reliableEfficiencies.length} readings with outdoor PM2.5 > 5)\n`;
    } else {
      const medianEff = median(stats.allEfficiencies);
      body += `  Low Confidence Efficiency: ${medianEff.toFixed(1)}% (outdoor air too clean for reliable measurement)\n`;
    }
    
    // Trend analysis
    const firstHalf = stats.allEfficiencies.slice(0, Math.floor(stats.allEfficiencies.length / 2));
    const secondHalf = stats.allEfficiencies.slice(Math.floor(stats.allEfficiencies.length / 2));
    
    if (firstHalf.length > 0 && secondHalf.length > 0) {
      const trend = median(secondHalf) - median(firstHalf);
      if (trend < -3) {
        body += `  ⚠️ Declining trend: -${Math.abs(trend).toFixed(1)}% over the week\n`;
      } else if (trend > 3) {
        body += `  ✅ Improving trend: +${trend.toFixed(1)}% over the week\n`;
      } else {
        body += `  ➡️ Stable performance\n`;
      }
    }
    body += '\n';
  });
  
  // High pollution performance
  const pollutionPerf = analyzeHighPollutionPerformance();
  if (pollutionPerf.message) {
    body += `\n⚠️ ${pollutionPerf.message}\n`;
  } else {
    body += '\n📈 Performance During High Pollution Events:\n';
    Object.entries(pollutionPerf).forEach(([room, perf]) => {
      body += `  ${room}: ${perf.medianEfficiency.toFixed(1)}% efficiency (${perf.confidenceLevel} confidence)\n`;
    });
  }
  
  body += `\n\nView detailed data: ${SpreadsheetApp.getActiveSpreadsheet().getUrl()}`;
  
  MailApp.sendEmail(emailAddress, '📊 Weekly Air Quality Report', body);
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
  
  const criticalCount = alerts.filter(a => a.level === 'CRITICAL').length;
  const subject = criticalCount > 0 
    ? `🚨 CRITICAL: ${criticalCount} Filter Alert${criticalCount > 1 ? 's' : ''}` 
    : '⚠️ HVAC Filter Alert';
  
  let body = 'HVAC Filter Alerts:\n\n';
  
  // Sort by severity
  const sortedAlerts = alerts.sort((a, b) => {
    const levelOrder = { 'CRITICAL': 0, 'WARNING': 1, 'INFO': 2 };
    return levelOrder[a.level] - levelOrder[b.level];
  });
  
  sortedAlerts.forEach(alert => {
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
 * Helper: Calculate median (better than average for spiky data)
 */
function median(arr) {
  if (arr.length === 0) return 0;
  const sorted = arr.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Helper: Calculate average
 */
function average(arr) {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/**
 * Set up smart triggers with less noise
 */
function setupSmartTriggers() {
  // Remove existing triggers
  ScriptApp.getProjectTriggers().forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
  });
  
  // Check efficiency every hour (not 30 min - less noise)
  ScriptApp.newTrigger('checkLatestEfficiency')
    .timeBased()
    .everyHours(1)
    .create();
    
  // Check data collection every 2 hours
  ScriptApp.newTrigger('checkDataCollection')
    .timeBased()
    .everyHours(2)
    .create();
  
  // Weekly trend report (Sundays at 9 AM)
  ScriptApp.newTrigger('weeklyTrendReport')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(9)
    .create();
    
  console.log('Smart triggers set up successfully!');
}

/**
 * Test all functions
 */
function testAll() {
  console.log('Testing all functions...\n');
  
  // Test efficiency check
  console.log('1. Testing efficiency check with confidence levels...');
  const effAlerts = checkLatestEfficiency();
  console.log('Efficiency alerts:', effAlerts.length > 0 ? effAlerts : 'No alerts');
  
  // Test data collection check
  console.log('\n2. Testing data collection monitoring...');
  checkDataCollection();
  console.log('Data collection check complete');
  
  // Test high pollution analysis
  console.log('\n3. Testing high pollution performance analysis...');
  const pollPerf = analyzeHighPollutionPerformance();
  console.log('Pollution performance:', pollPerf);
  
  // Test weekly report (without sending)
  console.log('\n4. Generating weekly report preview...');
  weeklyTrendReport();
  
  console.log('\n✅ All tests complete! Check logs for details.');
}

/**
 * Manual test to send yourself a test alert
 */
function sendTestAlert() {
  const emailAddress = PropertiesService.getScriptProperties().getProperty('ALERT_EMAIL');
  
  if (!emailAddress) {
    console.log('No email configured in Script Properties');
    return;
  }
  
  const testAlerts = [
    {
      level: 'INFO',
      message: '✅ TEST: This is a test alert from your HVAC monitoring system'
    }
  ];
  
  sendAlertEmail(testAlerts);
  console.log(`Test alert sent to ${emailAddress}`);
}

/**
 * Get current status summary
 */
function getCurrentStatus() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  
  if (lastRow <= 1) return { error: 'No data in sheet' };
  
  // Get last 10 rows
  const startRow = Math.max(2, lastRow - 9);
  const recentData = sheet.getRange(startRow, 1, lastRow - startRow + 1, 18).getValues();
  
  const status = {
    lastUpdate: new Date(recentData[recentData.length - 1][COLS.TIMESTAMP]),
    sensors: {}
  };
  
  // Get latest for each sensor
  const seen = new Set();
  for (let i = recentData.length - 1; i >= 0; i--) {
    const row = recentData[i];
    const sensorId = row[COLS.SENSOR_ID];
    
    if (!seen.has(sensorId)) {
      seen.add(sensorId);
      status.sensors[sensorId] = {
        room: row[COLS.ROOM],
        efficiency: parseFloat(row[COLS.FILTER_EFFICIENCY]),
        indoorPM25: parseFloat(row[COLS.INDOOR_PM25]),
        outdoorPM25: parseFloat(row[COLS.OUTDOOR_PM25]),
        confidence: row[COLS.OUTDOOR_PM25] >= 10 ? 'HIGH' : 
                   row[COLS.OUTDOOR_PM25] >= 5 ? 'MEDIUM' : 'LOW'
      };
    }
  }
  
  console.log('Current Status:', JSON.stringify(status, null, 2));
  return status;
}