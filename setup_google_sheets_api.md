# Setting Up Google Sheets API Access

This guide will help you set up secure, private access to your Google Sheets data.

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Name it: `hvac-air-quality` (or similar)
4. Click "Create"

## Step 2: Enable Google Sheets API

1. In your new project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click on it and press "Enable"

## Step 3: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service account"
3. Service account details:
   - Name: `hvac-sheets-reader`
   - ID: (auto-generated is fine)
   - Description: "Read air quality data from Google Sheets"
4. Click "Create and Continue"
5. Skip the optional steps (Grant access, Grant users)
6. Click "Done"

## Step 4: Download Credentials

1. Click on your new service account email
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON" format
5. Click "Create" - this downloads the credentials file
6. **IMPORTANT**: Save this file as `google-credentials.json` in your project directory
7. Add `google-credentials.json` to `.gitignore` immediately!

## Step 5: Get Service Account Email

From the credentials JSON file, copy the `client_email` value.
It looks like: `hvac-sheets-reader@your-project-id.iam.gserviceaccount.com`

## Step 6: Share Your Google Sheet

1. Open your Google Sheet (from Form responses)
2. Click "Share" button
3. Paste the service account email
4. Give "Viewer" access (read-only)
5. Uncheck "Notify people"
6. Click "Share"

## Step 7: Get Your Sheet ID

From your Google Sheets URL:
`https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`

Copy the SHEET_ID_HERE part.

## Step 8: Update .env File

Add these to your `.env` file:
```
GOOGLE_SPREADSHEET_ID=your_sheet_id_here
GOOGLE_CREDENTIALS_PATH=google-credentials.json
```

## Security Notes

- **Never commit** `google-credentials.json` to Git
- The service account only has read access to this specific sheet
- No one else can access your data without the credentials file
- Keep the credentials file secure on your local machine and Unifi Gateway

## Next Steps

Once you've completed these steps, run:
```bash
python setup_google_sheets_api.py
```

This will verify your setup and test reading data from your private Google Sheet.