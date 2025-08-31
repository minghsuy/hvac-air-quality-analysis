#!/usr/bin/env python3
"""
Fixed version for Ubiquiti with hardcoded IPs
"""

# Monkey-patch the requests to use fixed IPs
import requests

original_get = requests.get


def requests_get_fixed(url, *args, **kwargs):
    # Replace .local URLs with fixed IPs
    if "airgradient_OUTDOOR_SERIAL.local" in url:
        url = url.replace("airgradient_OUTDOOR_SERIAL.local", "192.168.X.XX")  # Configure your outdoor IP
    elif "airgradient_INDOOR_SERIAL.local" in url:
        url = url.replace("airgradient_INDOOR_SERIAL.local", "192.168.X.XX")  # Configure your indoor IP
    return original_get(url, *args, **kwargs)


requests.get = requests_get_fixed

# Now import and run the original script
import collect_with_sheets_api  # noqa: E402

collect_with_sheets_api.main()
