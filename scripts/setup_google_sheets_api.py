#!/usr/bin/env python3
"""
Setup verification script for Google Sheets API
Helps you verify all steps are completed correctly
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_setup():
    """Check if Google Sheets API is properly configured"""
    print("=== Google Sheets API Setup Checker ===\n")

    all_good = True

    # 1. Check credentials file
    print("1. Checking for credentials file...")
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")

    if os.path.exists(creds_path):
        print(f"✓ Found credentials file: {creds_path}")

        # Read and display service account email
        try:
            with open(creds_path, "r") as f:
                creds = json.load(f)
                client_email = creds.get("client_email")
                project_id = creds.get("project_id")

                print(f"  Project ID: {project_id}")
                print(f"  Service Account: {client_email}")
                print("\n📋 IMPORTANT: Share your Google Sheet with this email:")
                print(f"   {client_email}")
        except Exception as e:
            print(f"✗ Error reading credentials: {e}")
            all_good = False
    else:
        print(f"✗ Credentials file not found: {creds_path}")
        print("  Follow steps 1-4 in setup_google_sheets_api.md")
        all_good = False

    # 2. Check .gitignore
    print("\n2. Checking .gitignore...")
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            gitignore = f.read()
            if "google-credentials.json" in gitignore:
                print("✓ google-credentials.json is in .gitignore")
            else:
                print("⚠️  WARNING: google-credentials.json not in .gitignore!")
                print("  Add it to prevent accidentally committing secrets")
                all_good = False

    # 3. Check environment variables
    print("\n3. Checking environment variables...")
    sheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if sheet_id:
        print(f"✓ GOOGLE_SPREADSHEET_ID is set: {sheet_id}")
    else:
        print("✗ GOOGLE_SPREADSHEET_ID not found in .env")
        print("  Get it from your Google Sheets URL:")
        print("  https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit")
        all_good = False

    # 4. Test import of Google libraries
    print("\n4. Checking Google API libraries...")
    try:
        import importlib.util

        if importlib.util.find_spec("google.oauth2.service_account") and importlib.util.find_spec(
            "googleapiclient.discovery"
        ):
            print("✓ Google API libraries installed correctly")
        else:
            print("✗ Google API libraries not found")
            all_good = False
    except ImportError as e:
        print(f"✗ Missing Google API libraries: {e}")
        print("  Run: uv sync")
        all_good = False

    # Summary
    print("\n" + "=" * 50)
    if all_good and sheet_id and os.path.exists(creds_path):
        print("✅ Setup looks good! Ready to test.")
        print("\nNext steps:")
        print("1. Make sure you've shared your Google Sheet with the service account email")
        print("2. Run: python read_google_sheets_secure.py")
    else:
        print("❌ Setup incomplete. Fix the issues above and run this again.")
        print("\nQuick setup reminder:")
        print("1. Create Google Cloud project and enable Sheets API")
        print("2. Create service account and download JSON credentials")
        print("3. Save credentials as 'google-credentials.json'")
        print("4. Add GOOGLE_SPREADSHEET_ID to .env")
        print("5. Share your Google Sheet with the service account email")


if __name__ == "__main__":
    check_setup()
