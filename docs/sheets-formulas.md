# Google Sheets Analysis Formulas

## Setting Up Your Sheets

### Tab 1: Form Responses (Automatic)
This is created automatically when you link your form to sheets.

### Tab 2: Filter Changes (Manual)
Create columns: Date | Filter_Type | Brand | MERV | Cost | Notes

Example entries:
```
2025-06-01 | HVAC | Carrier | 15 | 130 | Regular replacement
2025-06-01 | ERV  | Broan   | 13 | 50  | Upgraded from MERV 8
```

### Tab 3: Dashboard

## Useful Formulas

### Current Filter Age (Days)
```excel
# Days since last HVAC filter change
=TODAY() - MAXIFS('Filter Changes'!A:A, 'Filter Changes'!B:B, "HVAC")

# Days since last ERV filter change  
=TODAY() - MAXIFS('Filter Changes'!A:A, 'Filter Changes'!B:B, "ERV")
```

### Average Efficiency (Last 24 Hours)
```excel
=AVERAGEIFS('Form Responses'!D:D, 'Form Responses'!A:A, ">"&NOW()-1)
```

### Current Indoor PM2.5 (Latest Reading)
```excel
=INDEX('Form Responses'!B:B, COUNTA('Form Responses'!B:B))
```

### Alert When Efficiency < 85%
```excel
=IF(D2<85, "⚠️ CHECK FILTER", "✓ OK")
```

### Cost Per Day
```excel
# Total cost of current filters
=SUMIFS('Filter Changes'!E:E, 'Filter Changes'!A:A, "="&MAXIFS('Filter Changes'!A:A, 'Filter Changes'!B:B, "HVAC")) + 
 SUMIFS('Filter Changes'!E:E, 'Filter Changes'!A:A, "="&MAXIFS('Filter Changes'!A:A, 'Filter Changes'!B:B, "ERV"))

# Divide by days
=F1/MAX(E1,E2)  # Where E1/E2 are days since change
```

### Efficiency Trend (Sparkline)
```excel
=SPARKLINE(FILTER('Form Responses'!D:D, 'Form Responses'!A:A>TODAY()-7))
```

## Conditional Formatting Rules

### Efficiency Column
- Red: < 80%
- Yellow: 80-85%
- Green: > 85%

### Indoor PM2.5
- Red: > 12 μg/m³
- Yellow: 8-12 μg/m³
- Green: < 8 μg/m³

## Charts to Create

1. **Efficiency Over Time**
   - X-axis: Timestamp
   - Y-axis: Filter Efficiency %
   - Add reference line at 85%

2. **Indoor vs Outdoor PM2.5**
   - Dual axis showing both values
   - Shows how well filters are working

3. **Cost Analysis**
   - Bar chart: Monthly filter costs
   - Line: Cumulative annual cost

## Automated Reports

### Email Alert When Efficiency Drops
1. Tools → Notification rules
2. Set condition: Efficiency < 85%
3. Notify: Immediately

### Weekly Summary Email
Use Google Apps Script to send weekly summaries:
```javascript
function sendWeeklySummary() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var avgEfficiency = sheet.getRange("D2").getValue();
  var daysHVAC = sheet.getRange("E1").getValue();
  var daysERV = sheet.getRange("E2").getValue();
  
  var message = `Weekly Filter Report:
  - Average Efficiency: ${avgEfficiency}%
  - HVAC Filter Age: ${daysHVAC} days
  - ERV Filter Age: ${daysERV} days`;
  
  MailApp.sendEmail("your-email@gmail.com", "Weekly Filter Report", message);
}
```

Set trigger: Time-driven → Week timer → Every Monday
