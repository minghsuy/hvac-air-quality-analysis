# Google Form Setup for Air Quality Data

## Create Your Form

1. Go to [Google Forms](https://forms.google.com)
2. Create a new blank form
3. Title: "HVAC Air Quality Data Logger"

## Add These Questions (All "Short answer" type)

Create questions in this exact order:

1. **Timestamp**
2. **Indoor PM2.5**
3. **Outdoor PM2.5**
4. **Filter Efficiency**
5. **Indoor CO2**
6. **Indoor VOC**
7. **Indoor Temperature**
8. **Indoor Humidity**
9. **Outdoor CO2**
10. **Outdoor Temperature**
11. **Outdoor Humidity**
12. **Outdoor VOC**
13. **Outdoor NOX**

## Get Your Form ID

1. Click the "Send" button
2. Click the link icon 🔗
3. Your form URL looks like: `https://forms.google.com/d/e/1FAIpQLSdXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/viewform`
4. Copy the part between `/e/` and `/viewform` - this is your `GOOGLE_FORM_ID`

## Get Field Entry IDs

1. Open your form in a browser
2. Right-click → "Inspect" or press F12
3. Go to the Network tab
4. Fill out and submit the form once with test data
5. Look for a request to `formResponse`
6. In the Form Data, you'll see entries like:
   - `entry.1234567890: test value`
7. Copy each entry ID

## Update Your .env File

```bash
# Google Forms Configuration
GOOGLE_FORM_ID=1FAIpQLSdXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Form field IDs (from inspection)
FORM_TIMESTAMP=entry.1234567890
FORM_INDOOR_PM25=entry.2345678901
FORM_OUTDOOR_PM25=entry.3456789012
FORM_EFFICIENCY=entry.4567890123
FORM_INDOOR_CO2=entry.5678901234
FORM_INDOOR_VOC=entry.6789012345
FORM_INDOOR_TEMP=entry.7890123456
FORM_INDOOR_HUMIDITY=entry.8901234567
FORM_OUTDOOR_CO2=entry.9012345678
FORM_OUTDOOR_TEMP=entry.0123456789
FORM_OUTDOOR_HUMIDITY=entry.1234567890
FORM_OUTDOOR_VOC=entry.2345678901
FORM_OUTDOOR_NOX=entry.3456789012
```

## Link to Google Sheets

1. In your form, go to "Responses" tab
2. Click the Google Sheets icon
3. Create a new spreadsheet
4. This will automatically collect all form submissions

## Track Filter Changes Separately

Create a second sheet tab called "Filter Changes" with columns:
- Date
- Filter Type (HVAC/ERV)
- Brand
- MERV Rating
- Cost
- Notes

Update this manually when you change filters. Then in your analysis, you can:
1. Look up the most recent change date for each filter
2. Calculate days since change
3. Track cost per day
4. See replacement patterns over time

## Why So Many Fields?

- **PM2.5**: Primary metric for filter efficiency
- **CO2**: Indicates ventilation effectiveness
- **VOC/NOX**: Additional air quality indicators
- **Temperature/Humidity**: Affects filter performance and comfort

## Data You'll See

Each hour, a new row will appear with:
```
2025-07-26 14:00:00 | 3.2 | 18.5 | 82.7% | 420 | 85 | 72.1 | 45% | 398 | 75.2 | 52% | 105 | 1
```

This gives you a complete picture of:
- How well your filters are working
- Indoor vs outdoor conditions
- Environmental factors affecting performance
