#!/usr/bin/env python3
"""
Read air quality data from Google Sheets (inserted via Google Forms)
"""

import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# Load environment variables
load_dotenv()

def read_sheets_with_api():
    """
    Read data using Google Sheets API
    Requires service account credentials
    """
    # You'll need to set up service account credentials
    # 1. Go to Google Cloud Console
    # 2. Create a service account
    # 3. Download credentials JSON
    # 4. Share your Google Sheet with the service account email
    
    CREDENTIALS_FILE = 'google-credentials.json'  # Path to your service account JSON
    SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')  # The ID from your sheet URL
    
    if not os.path.exists(CREDENTIALS_FILE):
        print("Service account credentials not found.")
        print("To use the API method:")
        print("1. Create a service account at https://console.cloud.google.com")
        print("2. Download the credentials JSON")
        print("3. Save as 'google-credentials.json'")
        print("4. Share your Google Sheet with the service account email")
        return None
    
    try:
        # Authenticate
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        # Read data (assuming data is in Sheet1)
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:Z'  # Adjust range as needed
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print('No data found.')
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
        
    except Exception as e:
        print(f"Error reading from Sheets API: {e}")
        return None

def read_sheets_csv_export():
    """
    Alternative method: Read from published CSV
    This works if you publish your sheet to web as CSV
    """
    # To use this method:
    # 1. File -> Share -> Publish to web
    # 2. Choose CSV format
    # 3. Copy the published URL
    
    PUBLISHED_CSV_URL = os.getenv('GOOGLE_SHEETS_CSV_URL')
    
    if not PUBLISHED_CSV_URL:
        print("No published CSV URL found in environment variables.")
        print("To use this method:")
        print("1. In Google Sheets: File -> Share -> Publish to web")
        print("2. Choose CSV format and publish")
        print("3. Add URL to .env as GOOGLE_SHEETS_CSV_URL")
        return None
    
    try:
        df = pd.read_csv(PUBLISHED_CSV_URL)
        return df
    except Exception as e:
        print(f"Error reading published CSV: {e}")
        return None

def analyze_recent_data(df):
    """Analyze recent air quality data"""
    if df is None or df.empty:
        print("No data to analyze")
        return
    
    # Convert timestamp column (adjust column name as needed)
    timestamp_col = 'Timestamp'  # Adjust based on your form
    if timestamp_col in df.columns:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values(timestamp_col)
    
    # Print recent readings
    print("\n=== Recent Air Quality Readings ===")
    print(df.tail(10))
    
    # Calculate statistics if PM2.5 columns exist
    indoor_col = 'Indoor PM2.5'  # Adjust based on your form
    outdoor_col = 'Outdoor PM2.5'  # Adjust based on your form
    efficiency_col = 'Filter Efficiency'  # Adjust based on your form
    
    if all(col in df.columns for col in [indoor_col, outdoor_col, efficiency_col]):
        # Convert to numeric
        df[indoor_col] = pd.to_numeric(df[indoor_col], errors='coerce')
        df[outdoor_col] = pd.to_numeric(df[outdoor_col], errors='coerce')
        df[efficiency_col] = pd.to_numeric(df[efficiency_col], errors='coerce')
        
        print("\n=== Summary Statistics ===")
        print(f"Indoor PM2.5 - Mean: {df[indoor_col].mean():.1f}, Max: {df[indoor_col].max():.1f}")
        print(f"Outdoor PM2.5 - Mean: {df[outdoor_col].mean():.1f}, Max: {df[outdoor_col].max():.1f}")
        print(f"Filter Efficiency - Mean: {df[efficiency_col].mean():.1f}%, Min: {df[efficiency_col].min():.1f}%")
        
        # Check for concerning readings
        low_efficiency = df[df[efficiency_col] < 85]
        if not low_efficiency.empty:
            print(f"\n⚠️  Warning: {len(low_efficiency)} readings with efficiency < 85%")
            print("Consider replacing filters soon!")

def download_sheets_data():
    """
    Simple method: Manual download
    Instructions for getting data from Google Sheets created by Forms
    """
    print("\n=== Manual Download Method ===")
    print("To download your Google Sheets data:")
    print("1. Open your Google Form")
    print("2. Click on 'Responses' tab")
    print("3. Click the Sheets icon to view in Google Sheets")
    print("4. In Google Sheets: File -> Download -> CSV")
    print("5. Save the file and update the path below")
    
    # Try to read local CSV if it exists
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'form' in f.lower()]
    if csv_files:
        print(f"\nFound CSV files: {csv_files}")
        latest_csv = csv_files[0]
        df = pd.read_csv(latest_csv)
        print(f"Loaded {len(df)} rows from {latest_csv}")
        return df
    else:
        print("\nNo CSV files found. Please download from Google Sheets.")
        return None

def main():
    """Main function to read Google Sheets data"""
    print("=== Reading Air Quality Data from Google Sheets ===\n")
    
    # Method 1: Try API (requires setup)
    print("Method 1: Google Sheets API")
    df = read_sheets_with_api()
    
    # Method 2: Try published CSV
    if df is None:
        print("\nMethod 2: Published CSV URL")
        df = read_sheets_csv_export()
    
    # Method 3: Manual download
    if df is None:
        print("\nMethod 3: Manual Download")
        df = download_sheets_data()
    
    # Analyze if we got data
    if df is not None:
        analyze_recent_data(df)
        
        # Save to local file
        output_file = f"air_quality_data_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✓ Data saved to {output_file}")

if __name__ == "__main__":
    main()