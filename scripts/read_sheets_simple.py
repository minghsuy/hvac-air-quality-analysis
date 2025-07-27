#!/usr/bin/env python3
"""
Simple method to read Google Sheets data created by Forms
Uses the publish to web feature - no authentication needed
"""

import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_sheet_as_csv(sheet_id=None, gid='0'):
    """
    Read Google Sheets data using the export URL
    No authentication required if sheet is viewable by anyone with link
    
    Args:
        sheet_id: The Google Sheets ID from the URL
        gid: The sheet/tab ID (default is 0 for first sheet)
    """
    if not sheet_id:
        sheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
        
    if not sheet_id:
        print("Please provide the Google Sheets ID")
        print("You can find this in your sheet URL:")
        print("https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit")
        return None
    
    # Construct the export URL
    csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        print(f"Reading from Google Sheets...")
        df = pd.read_csv(csv_export_url)
        print(f"✓ Successfully loaded {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error reading sheet: {e}")
        print("\nMake sure:")
        print("1. The sheet is shared (Anyone with link can view)")
        print("2. The GOOGLE_SPREADSHEET_ID in .env is correct")
        return None

def find_sheet_id_from_form():
    """Help user find their Google Sheets ID from Form"""
    print("\n=== How to Find Your Google Sheets ID ===")
    print("1. Open your Google Form")
    print("2. Go to 'Responses' tab")
    print("3. Click the green Sheets icon")
    print("4. This opens the linked Google Sheet")
    print("5. Copy the ID from the URL:")
    print("   https://docs.google.com/spreadsheets/d/[THIS_IS_YOUR_SHEET_ID]/edit")
    print("\nAdd to .env file:")
    print("GOOGLE_SPREADSHEET_ID=your_sheet_id_here")

def analyze_air_quality_data(df):
    """Analyze the air quality data"""
    print("\n=== Data Overview ===")
    print(f"Total records: {len(df)}")
    print(f"Columns: {', '.join(df.columns)}")
    
    # Show recent data
    print("\n=== Last 5 Readings ===")
    print(df.tail(5))
    
    # Try to parse timestamp and numeric columns
    # Adjust these column names based on your actual form
    possible_timestamp_cols = ['Timestamp', 'timestamp', 'Time', 'Date']
    possible_pm25_indoor = ['Indoor PM2.5', 'indoor_pm25', 'PM2.5 Indoor']
    possible_pm25_outdoor = ['Outdoor PM2.5', 'outdoor_pm25', 'PM2.5 Outdoor']
    possible_efficiency = ['Filter Efficiency', 'filter_efficiency', 'Efficiency']
    
    # Find actual column names
    timestamp_col = next((col for col in possible_timestamp_cols if col in df.columns), None)
    indoor_col = next((col for col in possible_pm25_indoor if col in df.columns), None)
    outdoor_col = next((col for col in possible_pm25_outdoor if col in df.columns), None)
    efficiency_col = next((col for col in possible_efficiency if col in df.columns), None)
    
    if timestamp_col:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df = df.sort_values(timestamp_col)
        print(f"\n✓ Found timestamp column: {timestamp_col}")
    
    # Convert numeric columns
    numeric_cols = []
    for col in [indoor_col, outdoor_col, efficiency_col]:
        if col and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            numeric_cols.append(col)
    
    if numeric_cols:
        print(f"✓ Found numeric columns: {', '.join(numeric_cols)}")
        
        # Calculate statistics
        print("\n=== Statistics ===")
        for col in numeric_cols:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Mean: {data.mean():.2f}")
                print(f"  Min: {data.min():.2f}")
                print(f"  Max: {data.max():.2f}")
                print(f"  Latest: {data.iloc[-1]:.2f}")
        
        # Check filter efficiency
        if efficiency_col:
            low_efficiency = df[df[efficiency_col] < 85]
            if len(low_efficiency) > 0:
                print(f"\n⚠️  Alert: {len(low_efficiency)} readings with efficiency < 85%")
                recent_low = low_efficiency.tail(3)
                print("\nRecent low efficiency readings:")
                if timestamp_col:
                    for _, row in recent_low.iterrows():
                        print(f"  {row[timestamp_col]}: {row[efficiency_col]:.1f}%")
    
    return df

def main():
    """Main function"""
    print("=== Google Sheets Data Reader ===\n")
    
    # Try to read from environment variable first
    sheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    
    if not sheet_id:
        find_sheet_id_from_form()
        print("\nYou can also manually enter the Sheet ID:")
        sheet_id = input("Sheet ID (or press Enter to skip): ").strip()
    
    if sheet_id:
        df = get_sheet_as_csv(sheet_id)
        
        if df is not None:
            # Analyze the data
            df = analyze_air_quality_data(df)
            
            # Save locally
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"air_quality_export_{timestamp}.csv"
            df.to_csv(output_file, index=False)
            print(f"\n✓ Data saved to {output_file}")
    else:
        print("\nNo Sheet ID provided. Please add GOOGLE_SPREADSHEET_ID to your .env file")

if __name__ == "__main__":
    main()