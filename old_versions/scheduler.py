#!/usr/bin/env python3
"""
Scheduled data collector for continuous monitoring
Can be run via cron or as a service
"""

import schedule
import time
import logging
from datetime import datetime
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.collect_data import AirthingsClient, save_data

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"collector_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def collect_and_save():
    """Collect data and save to timestamped file"""
    try:
        logger.info("Starting data collection...")
        
        # Initialize client
        client = AirthingsClient()
        
        # Get accounts
        accounts = client.get_accounts()
        if not accounts['accounts']:
            logger.error("No accounts found")
            return
            
        account_id = accounts['accounts'][0]['id']
        
        # Get sensor data
        sensor_data = client.get_latest_sensors(
            account_id,
            device_serials=[client.device_serial] if client.device_serial else None
        )
        
        # Save data
        filepath = save_data(sensor_data, "sensors")
        
        # Log summary
        if sensor_data['results']:
            result = sensor_data['results'][0]
            sensors = {s['sensorType']: s['value'] for s in result['sensors']}
            logger.info(f"Data collected successfully: {sensors}")
        
    except Exception as e:
        logger.error(f"Error during collection: {e}")

def run_scheduler():
    """Run the scheduler"""
    # Schedule data collection every hour
    schedule.every().hour.do(collect_and_save)
    
    # Also run at specific times for consistency
    schedule.every().day.at("06:00").do(collect_and_save)
    schedule.every().day.at("12:00").do(collect_and_save)
    schedule.every().day.at("18:00").do(collect_and_save)
    schedule.every().day.at("22:00").do(collect_and_save)
    
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    
    # Run once immediately
    collect_and_save()
    
    # Keep running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    # Run single collection if --once flag is provided
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        collect_and_save()
    else:
        run_scheduler()
