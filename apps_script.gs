/**
 * Google Apps Script for Air Quality Monitoring
 * Add this to your Google Sheet: Extensions > Apps Script
 * 
 * Features:
 * - Alert if no data for 1 hour
 * - Daily summary email at 9 AM
 * - Low efficiency alerts
 * - Filter replacement predictions
 */

// Configuration - UPDATE THESE
const EMAIL_ADDRESS = 'your-email@gmail.com'; // Your email for alerts
const SHEET_NAME = 'Form Responses 1'; // Name of your data sheet
const EFFICIENCY_ALERT_THRESHOLD = 85; // Alert when efficiency drops below this
const NO_DATA_ALERT_MINUTES = 60; // Alert if no data for this many minutes

/**
 * Set up time-based triggers
 * Run this once to set up automated monitoring
 */
function setupTriggers() {
  // Clear existing triggers
  ScriptApp.getProjectTriggers().forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
  });
  
  // Check for missing data every 30 minutes
  ScriptApp.newTrigger('checkDataCollection')
    .timeBased()
    .everyMinutes(30)
    .create();
  
  // Send daily summary at 9 AM
  ScriptApp.newTrigger('sendDailySummary')
    .timeBased()
    .atHour(9)
    .everyDays(1)
    .create();
  
  // Check efficiency after each form submission
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit()
    .create();
  
  SpreadsheetApp.getUi().alert('Triggers set up successfully!');
}

/**
 * Check if data collection is working
 */
function checkDataCollection() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  
  if (lastRow < 2) return; // No data yet
  
  // Get the last timestamp
  const timestampCol = 1; // Assuming timestamp is in column A
  const lastTimestamp = sheet.getRange(lastRow, timestampCol).getValue();
  
  if (!lastTimestamp) return;
  
  // Calculate time since last data
  const now = new Date();
  const lastTime = new Date(lastTimestamp);
  const minutesSinceLastData = (now - lastTime) / (1000 * 60);
  
  // Alert if no data for too long
  if (minutesSinceLastData > NO_DATA_ALERT_MINUTES) {
    const subject = '🚨 Air Quality Monitor - No Data Received';
    const body = `
No data received for ${Math.round(minutesSinceLastData)} minutes!

Last data received: ${lastTime}
Current time: ${now}

Possible issues:
1. Unifi Gateway cron job stopped
2. Network connectivity issue
3. Sensor offline

Action needed:
1. SSH to gateway: ssh root@[your-gateway-ip]
2. Check cron: crontab -l
3. Test manually: python3 /data/scripts/collect_air.py
    `.trim();
    
    MailApp.sendEmail(EMAIL_ADDRESS, subject, body);
    
    // Log the alert
    console.log(`Alert sent: No data for ${minutesSinceLastData} minutes`);
  }
}

/**
 * Check efficiency on new data submission
 */
function onFormSubmit(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  
  // Find column indices
  const efficiencyCol = headers.indexOf('Filter Efficiency') + 1;
  const indoorPM25Col = headers.indexOf('Indoor PM2.5') + 1;
  const outdoorPM25Col = headers.indexOf('Outdoor PM2.5') + 1;
  
  if (efficiencyCol === 0) return; // Column not found
  
  // Get the new row data
  const lastRow = sheet.getLastRow();
  const efficiency = sheet.getRange(lastRow, efficiencyCol).getValue();
  const indoorPM25 = sheet.getRange(lastRow, indoorPM25Col).getValue();
  const outdoorPM25 = sheet.getRange(lastRow, outdoorPM25Col).getValue();
  
  // Check if efficiency is low (only meaningful when outdoor PM2.5 > 10)
  if (efficiency < EFFICIENCY_ALERT_THRESHOLD && outdoorPM25 > 10) {
    const subject = `⚠️ Low Filter Efficiency: ${efficiency}%`;
    const body = `
Filter efficiency has dropped to ${efficiency}%

Current readings:
- Indoor PM2.5: ${indoorPM25} μg/m³
- Outdoor PM2.5: ${outdoorPM25} μg/m³
- Efficiency: ${efficiency}%

Threshold: ${EFFICIENCY_ALERT_THRESHOLD}%

Consider planning filter replacement soon.
    `.trim();
    
    MailApp.sendEmail(EMAIL_ADDRESS, subject, body);
  }
  
  // Alert if indoor PM2.5 is high
  if (indoorPM25 > 12) {
    const subject = `🚨 High Indoor PM2.5: ${indoorPM25} μg/m³`;
    const body = `
Indoor air quality is poor!

Indoor PM2.5: ${indoorPM25} μg/m³
WHO Guideline: 15 μg/m³
Recommended: < 12 μg/m³

Immediate action recommended:
- Check filter condition
- Consider replacement
    `.trim();
    
    MailApp.sendEmail(EMAIL_ADDRESS, subject, body);
  }
}

/**
 * Send daily summary email
 */
function sendDailySummary() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  
  if (lastRow < 2) return; // No data
  
  // Get last 24 hours of data (288 rows if collecting every 5 minutes)
  const rowsToAnalyze = Math.min(288, lastRow - 1);
  const startRow = lastRow - rowsToAnalyze + 1;
  
  // Get headers
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  
  // Get data range
  const dataRange = sheet.getRange(startRow, 1, rowsToAnalyze, sheet.getLastColumn());
  const data = dataRange.getValues();
  
  // Find columns
  const efficiencyCol = headers.indexOf('Filter Efficiency');
  const indoorPM25Col = headers.indexOf('Indoor PM2.5');
  const outdoorPM25Col = headers.indexOf('Outdoor PM2.5');
  
  // Calculate statistics
  let efficiencies = [];
  let indoorPM25s = [];
  let outdoorPM25s = [];
  
  data.forEach(row => {
    if (row[efficiencyCol]) efficiencies.push(row[efficiencyCol]);
    if (row[indoorPM25Col]) indoorPM25s.push(row[indoorPM25Col]);
    if (row[outdoorPM25Col]) outdoorPM25s.push(row[outdoorPM25Col]);
  });
  
  const avgEfficiency = average(efficiencies);
  const minEfficiency = Math.min(...efficiencies);
  const maxEfficiency = Math.max(...efficiencies);
  
  const avgIndoor = average(indoorPM25s);
  const avgOutdoor = average(outdoorPM25s);
  
  // Calculate trend (comparing last 12 hours to previous 12 hours)
  const midPoint = Math.floor(efficiencies.length / 2);
  const firstHalf = average(efficiencies.slice(0, midPoint));
  const secondHalf = average(efficiencies.slice(midPoint));
  const trend = secondHalf - firstHalf;
  const trendText = trend > 0 ? `📈 +${trend.toFixed(1)}%` : `📉 ${trend.toFixed(1)}%`;
  
  // Predict days until replacement (simple linear regression)
  const daysToReplacement = predictDaysToThreshold(efficiencies, 80);
  
  // Create email
  const subject = `📊 Daily Air Quality Report - Efficiency: ${avgEfficiency.toFixed(1)}%`;
  const body = `
Good morning! Here's your air quality summary for the last 24 hours:

📈 FILTER EFFICIENCY
Average: ${avgEfficiency.toFixed(1)}%
Range: ${minEfficiency.toFixed(1)}% - ${maxEfficiency.toFixed(1)}%
Trend: ${trendText}
${avgEfficiency < 90 ? '⚠️ Efficiency below 90% - monitor closely' : '✅ Efficiency is good'}

💨 AIR QUALITY
Indoor PM2.5: ${avgIndoor.toFixed(1)} μg/m³
Outdoor PM2.5: ${avgOutdoor.toFixed(1)} μg/m³
${avgIndoor < 12 ? '✅ Indoor air quality is excellent' : '⚠️ Indoor air quality needs attention'}

📅 PREDICTION
${daysToReplacement > 0 ? 
  `Estimated days until 80% threshold: ${Math.round(daysToReplacement)} days` : 
  'Unable to predict - efficiency may be improving!'}

Filter installed: August 29, 2025
Days in use: ${Math.floor((new Date() - new Date('2025-08-29')) / (1000 * 60 * 60 * 24))} days

View full data: ${SpreadsheetApp.getActiveSpreadsheet().getUrl()}

---
This is an automated report from your Air Quality Monitoring System
  `.trim();
  
  MailApp.sendEmail(EMAIL_ADDRESS, subject, body);
  
  console.log('Daily summary sent');
}

/**
 * Helper function to calculate average
 */
function average(arr) {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/**
 * Predict days until efficiency reaches threshold
 */
function predictDaysToThreshold(efficiencies, threshold) {
  if (efficiencies.length < 10) return -1;
  
  // Simple linear regression
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  const n = efficiencies.length;
  
  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += efficiencies[i];
    sumXY += i * efficiencies[i];
    sumX2 += i * i;
  }
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  
  // If improving, return -1
  if (slope >= 0) return -1;
  
  // Calculate readings until threshold
  const currentEfficiency = efficiencies[efficiencies.length - 1];
  const readingsToThreshold = (threshold - currentEfficiency) / slope;
  
  // Convert to days (288 readings per day at 5-minute intervals)
  return readingsToThreshold / 288;
}

/**
 * Manual test function
 */
function testAlerts() {
  checkDataCollection();
  console.log('Test complete - check logs');
}