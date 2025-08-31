#!/usr/bin/env python3
"""
Template for Ubiquiti deployment with hardcoded IPs
IMPORTANT: Copy this to collect_multi_fixed.py and configure your actual IPs
DO NOT commit the configured version!
"""

# Monkey-patch the requests to use fixed IPs
import requests

original_get = requests.get


def requests_get_fixed(url, *args, **kwargs):
    # Replace .local URLs with your actual fixed IPs
    # CONFIGURE THESE WITH YOUR ACTUAL VALUES:
    if "airgradient_OUTDOOR_SERIAL.local" in url:
        url = url.replace("airgradient_OUTDOOR_SERIAL.local", "YOUR_OUTDOOR_IP")
    elif "airgradient_INDOOR_SERIAL.local" in url:
        url = url.replace("airgradient_INDOOR_SERIAL.local", "YOUR_INDOOR_IP")
    return original_get(url, *args, **kwargs)


requests.get = requests_get_fixed

# Now import and run the original script
import collect_with_sheets_api  # noqa: E402

collect_with_sheets_api.main()
