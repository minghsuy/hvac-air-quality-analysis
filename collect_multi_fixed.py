#!/usr/bin/env python3
"""
Fixed version for Ubiquiti with hardcoded IPs
"""
import sys
import os

# Monkey-patch the requests to use fixed IPs
import requests
original_get = requests.get

def requests_get_fixed(url, *args, **kwargs):
    # Replace .local URLs with fixed IPs
    if 'airgradient_XXXXXX.local' in url:
        url = url.replace('airgradient_XXXXXX.local', '192.168.X.XX')
    elif 'airgradient_XXXXXX.local' in url:
        url = url.replace('airgradient_XXXXXX.local', '192.168.X.XX')
    return original_get(url, *args, **kwargs)

requests.get = requests_get_fixed

# Now import and run the original script
import collect_with_sheets_api
collect_with_sheets_api.main()