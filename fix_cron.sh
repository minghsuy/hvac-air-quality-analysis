#!/bin/bash
# Quick fix to restore cron job on Ubiquiti Gateway

echo "🔧 Fixing cron job for air quality collection..."

# Create logs directory if it doesn't exist
mkdir -p /data/logs

# Add cron job (will append if not exists)
(crontab -l 2>/dev/null | grep -v "collect_air.py"; echo "*/5 * * * * /usr/bin/python3 /data/scripts/collect_air.py >> /data/logs/air_quality.log 2>&1") | crontab -

# Verify it was added
echo "✓ Cron job added. Current crontab:"
crontab -l

# Test the script
echo "📊 Testing data collection..."
cd /data/scripts
python3 collect_air.py

echo "✅ Done! Data should now collect every 5 minutes."
echo "Check logs at: /data/logs/air_quality.log"