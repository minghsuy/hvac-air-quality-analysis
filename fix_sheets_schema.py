#!/usr/bin/env python3
"""
Fix the Google Sheets schema mess - align old and new data formats
This script will:
1. Backup existing data
2. Convert old schema to new schema
3. Create a clean, consistent dataset
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import json

# Load environment variables
load_dotenv()

class SheetsFixer:
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            "google-credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.service = build("sheets", "v4", credentials=self.credentials)
        self.spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        
    def backup_data(self):
        """Step 1: Backup all existing data"""
        print("\n📦 STEP 1: Creating backup...")
        
        sheet = self.service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A:Z"
        ).execute()
        
        values = result.get("values", [])
        
        # Save backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/backup_sheets_{timestamp}.json"
        
        os.makedirs("data", exist_ok=True)
        with open(backup_file, "w") as f:
            json.dump(values, f, indent=2)
        
        print(f"✅ Backup saved to {backup_file}")
        print(f"   Total rows: {len(values)}")
        
        return values
    
    def analyze_schemas(self, data):
        """Step 2: Analyze the different schemas"""
        print("\n🔍 STEP 2: Analyzing schemas...")
        
        # Expected new schema
        new_headers = [
            "Timestamp",
            "Sensor_ID", 
            "Room",
            "Sensor_Type",
            "Indoor_PM25",
            "Outdoor_PM25",
            "Filter_Efficiency",
            "Indoor_CO2",
            "Indoor_VOC",
            "Indoor_NOX",
            "Indoor_Temp",
            "Indoor_Humidity",
            "Indoor_Radon",
            "Outdoor_CO2",
            "Outdoor_Temp",
            "Outdoor_Humidity",
            "Outdoor_VOC",
            "Outdoor_NOX",
        ]
        
        # Old schema (Google Forms) - 14 columns
        old_schema_mapping = {
            0: "Timestamp",           # 7/26/2025 13:27:51
            1: "ISO_Timestamp",       # 2025-07-26T13:27:50.470360 (will be ignored)
            2: "Indoor_PM25",         # 0
            3: "Outdoor_PM25",        # 3.15
            4: "Filter_Efficiency",   # 100
            5: "Indoor_CO2",          # 427
            6: "Indoor_VOC",          # 61
            7: "Days_Since_Install",  # 2.49 (will be ignored)
            8: "Indoor_Temp",         # 20.6
            9: "Indoor_Humidity",     # 59.5
            10: "Outdoor_CO2",        # 454
            11: "Outdoor_Temp",       # 28.7
            12: "Outdoor_Humidity",   # 66
            13: "Outdoor_VOC",        # 125
        }
        
        # Detect transition point
        transition_row = None
        for i, row in enumerate(data[1:], start=2):  # Skip header
            if len(row) > 0 and "/" not in row[0]:
                transition_row = i
                break
        
        print(f"✅ Schema transition detected at row {transition_row}")
        print(f"   Old schema: rows 2-{transition_row-1} (14 columns)")
        print(f"   New schema: rows {transition_row}-{len(data)} (18 columns)")
        
        return new_headers, old_schema_mapping, transition_row
    
    def convert_old_data(self, data, old_mapping, transition_row):
        """Step 3: Convert old data to new schema"""
        print("\n🔄 STEP 3: Converting old data to new schema...")
        
        converted_rows = []
        
        # Process old schema rows
        for i, row in enumerate(data[1:transition_row-1], start=2):
            if len(row) < 14:  # Skip incomplete rows
                continue
                
            # Parse old timestamp format "7/26/2025 13:27:51" to ISO
            try:
                old_timestamp = row[0]
                dt = datetime.strptime(old_timestamp, "%m/%d/%Y %H:%M:%S")
                iso_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                iso_timestamp = row[0]  # Keep as is if parsing fails
            
            # Create new row with proper schema
            new_row = [
                iso_timestamp,                    # Timestamp
                "airthings_129430",               # Sensor_ID (default for old data)
                "master_bedroom",                 # Room (default for old data)
                "airthings",                      # Sensor_Type (default for old data)
                row[2] if len(row) > 2 else "",  # Indoor_PM25
                row[3] if len(row) > 3 else "",  # Outdoor_PM25
                row[4] if len(row) > 4 else "",  # Filter_Efficiency
                row[5] if len(row) > 5 else "",  # Indoor_CO2
                row[6] if len(row) > 6 else "",  # Indoor_VOC
                "",                               # Indoor_NOX (didn't exist in old schema)
                row[8] if len(row) > 8 else "",  # Indoor_Temp
                row[9] if len(row) > 9 else "",  # Indoor_Humidity
                "",                               # Indoor_Radon (not in old schema)
                row[10] if len(row) > 10 else "", # Outdoor_CO2
                row[11] if len(row) > 11 else "", # Outdoor_Temp
                row[12] if len(row) > 12 else "", # Outdoor_Humidity
                row[13] if len(row) > 13 else "", # Outdoor_VOC
                "",                               # Outdoor_NOX (didn't exist in old schema)
            ]
            
            converted_rows.append(new_row)
        
        print(f"✅ Converted {len(converted_rows)} old rows to new schema")
        
        # Add the new schema rows (already in correct format)
        new_rows = []
        for row in data[transition_row-1:]:
            if len(row) == 18:  # Only include complete rows
                new_rows.append(row)
        
        print(f"✅ Found {len(new_rows)} rows already in new schema")
        
        return converted_rows, new_rows
    
    def create_clean_sheet(self, headers, converted_old, existing_new):
        """Step 4: Create a clean sheet with all data"""
        print("\n📝 STEP 4: Creating clean sheet...")
        
        # Option 1: Update existing sheet (be careful!)
        # Option 2: Create new sheet tab (safer)
        
        print("\n⚠️  IMPORTANT: Choose how to proceed:")
        print("1. Create NEW sheet tab 'Cleaned_Data' (SAFE - keeps original)")
        print("2. Replace existing data (DANGEROUS - overwrites everything)")
        print("3. Just save to CSV file (SAFEST - no Google Sheets changes)")
        
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        all_data = [headers] + converted_old + existing_new[1:]  # Skip duplicate header
        
        if choice == "1":
            # Create new sheet tab
            self.create_new_tab(all_data)
        elif choice == "2":
            # Replace existing (with confirmation)
            confirm = input("⚠️  Are you SURE you want to replace all data? Type 'yes': ")
            if confirm.lower() == "yes":
                self.replace_existing_data(all_data)
            else:
                print("❌ Cancelled - no changes made")
        else:
            # Save to CSV
            self.save_to_csv(all_data)
    
    def create_new_tab(self, data):
        """Create a new sheet tab with cleaned data"""
        try:
            # Add new sheet
            batch_update_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': f'Cleaned_Data_{datetime.now().strftime("%Y%m%d")}',
                            'gridProperties': {
                                'rowCount': len(data) + 100,
                                'columnCount': 26
                            }
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=batch_update_body
            ).execute()
            
            new_sheet_title = response['replies'][0]['addSheet']['properties']['title']
            
            # Write data to new sheet
            body = {'values': data}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{new_sheet_title}!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Created new sheet tab: {new_sheet_title}")
            print(f"   Total rows: {len(data)}")
            
        except Exception as e:
            print(f"❌ Error creating new tab: {e}")
    
    def replace_existing_data(self, data):
        """Replace all data in the main sheet"""
        try:
            # Clear existing data
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range="A:Z"
            ).execute()
            
            # Write new data
            body = {'values': data}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("✅ Replaced all data in main sheet")
            print(f"   Total rows: {len(data)}")
            
        except Exception as e:
            print(f"❌ Error replacing data: {e}")
    
    def save_to_csv(self, data):
        """Save cleaned data to CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"data/cleaned_data_{timestamp}.csv"
        
        df = pd.DataFrame(data[1:], columns=data[0])
        df.to_csv(csv_file, index=False)
        
        print(f"✅ Saved cleaned data to {csv_file}")
        print(f"   Total rows: {len(df)}")
    
    def run(self):
        """Run the complete fix process"""
        print("=" * 60)
        print("🔧 GOOGLE SHEETS SCHEMA FIXER")
        print("=" * 60)
        
        # Step 1: Backup
        data = self.backup_data()
        
        # Step 2: Analyze
        headers, old_mapping, transition_row = self.analyze_schemas(data)
        
        # Step 3: Convert
        converted_old, existing_new = self.convert_old_data(data, old_mapping, transition_row)
        
        # Step 4: Create clean sheet
        self.create_clean_sheet(headers, converted_old, existing_new)
        
        print("\n" + "=" * 60)
        print("✅ Process complete!")
        print("\nNext steps:")
        print("1. Verify the cleaned data looks correct")
        print("2. Update any Apps Script to use the new schema")
        print("3. Test the data collection pipeline")
        print("=" * 60)

if __name__ == "__main__":
    fixer = SheetsFixer()
    fixer.run()