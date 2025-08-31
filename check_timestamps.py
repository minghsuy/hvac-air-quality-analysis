#!/usr/bin/env python3
"""
Check timestamp handling and find the actual filter change time
"""

import pandas as pd
from datetime import datetime
import pytz

# Read the sample data
df = pd.read_csv('/tmp/sheets_sample.csv')

print("=" * 60)
print("TIMESTAMP ANALYSIS")
print("=" * 60)

# Check the two timestamp columns
print("\nFirst 5 rows of both timestamp columns:")
print("Column 1 (form format):", df.iloc[:5, 0].values)
print("Column 2 (ISO format):", df.iloc[:5, 1].values)

# Parse both timestamp formats
ts1 = pd.to_datetime(df.iloc[:, 0], format='%m/%d/%Y %H:%M:%S')
ts2 = pd.to_datetime(df.iloc[:, 1])

print("\n" + "=" * 60)
print("PARSED TIMESTAMPS")
print("=" * 60)

print("\nFirst timestamp parsed:")
print("  Raw:", df.iloc[0, 0])
print("  Parsed:", ts1.iloc[0])
print("  Type:", type(ts1.iloc[0]))
print("  Timezone aware?:", ts1.iloc[0].tz)

print("\nLast timestamp in data:")
print("  Raw:", df.iloc[-1, 0])
print("  Parsed:", ts1.iloc[-1])

# Current time analysis
print("\n" + "=" * 60)
print("CURRENT TIME CONTEXT")
print("=" * 60)

now_pdt = datetime.now(pytz.timezone('America/Los_Angeles'))
print(f"\nCurrent time (PDT): {now_pdt}")
print(f"Today's date: {now_pdt.date()}")
print(f"Yesterday: {now_pdt.date().replace(day=now_pdt.day-1)}")

# If you changed filter yesterday at 2pm PDT
filter_change_pdt = now_pdt.replace(day=29, hour=14, minute=0, second=0, microsecond=0)
print(f"\nFilter change time (Aug 29, 2pm PDT): {filter_change_pdt}")

# Check if we have data around filter change time
print("\n" + "=" * 60)
print("DATA AROUND FILTER CHANGE")
print("=" * 60)

# Convert sample timestamps to compare
ts_naive = pd.to_datetime(df.iloc[:, 0], format='%m/%d/%Y %H:%M:%S')

# Find data points around Aug 29, 2pm
aug29_start = pd.Timestamp('2025-08-29 12:00:00')
aug29_end = pd.Timestamp('2025-08-29 18:00:00')

# Since we only have last 100 rows, check the date range
print(f"\nData range in sample:")
print(f"  Earliest: {ts_naive.min()}")
print(f"  Latest: {ts_naive.max()}")

if ts_naive.min() > aug29_end:
    print("\n⚠️  Sample data starts AFTER filter change")
    print("    Need to fetch more historical data to see the change impact")
else:
    mask = (ts_naive >= aug29_start) & (ts_naive <= aug29_end)
    around_change = df[mask]
    if len(around_change) > 0:
        print(f"\n✅ Found {len(around_change)} data points around filter change:")
        print(around_change[['Timestamp', 'Filter Efficiency', 'Indoor PM2.5', 'Outdoor PM2.5']])

print("\n" + "=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)
print("""
1. Your timestamps appear to be in LOCAL TIME (PDT)
2. No timezone info in the data (naive timestamps)
3. Filter was changed Aug 29, 2025 at 2pm PDT
4. Need to fetch more historical data to see before/after comparison
5. The 71% efficiency might be AFTER the new filter installation
""")