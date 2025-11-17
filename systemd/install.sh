#!/bin/bash
# Installation script for HVAC Air Quality systemd services
# Run this with: sudo bash systemd/install.sh

set -e

echo "🔧 Installing HVAC Air Quality Monitoring Services..."

# Copy service files
echo "📋 Copying service files..."
cp systemd/air-quality-collector.service /etc/systemd/system/
cp systemd/air-quality-collector.timer /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable timer
echo "✅ Enabling air-quality-collector.timer..."
systemctl enable air-quality-collector.timer

# Start timer
echo "▶️  Starting air-quality-collector.timer..."
systemctl start air-quality-collector.timer

# Show status
echo ""
echo "📊 Service Status:"
systemctl status air-quality-collector.timer --no-pager

echo ""
echo "✅ Installation complete!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status air-quality-collector.timer    # Check timer status"
echo "  sudo systemctl status air-quality-collector.service  # Check last collection"
echo "  sudo journalctl -u air-quality-collector.service -f  # Follow logs"
echo "  tail -f ~/hvac-air-quality-analysis/logs/air_quality.log  # Application logs"
