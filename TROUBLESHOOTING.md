# 🔧 Troubleshooting Guide - HVAC Air Quality Monitoring

Common issues and solutions when setting up the system on Unifi Gateway.

## Quick Diagnosis

| Symptom | Most Likely Issue | Jump To |
|---------|------------------|---------|
| `ModuleNotFoundError: No module named 'dotenv'` | Running wrong script | [Wrong Script](#1-wrong-script-on-unifi-gateway) |
| Outdoor PM2.5 shows 0 | AirGradient connection failed | [AirGradient Issues](#2-airgradient-connection-issues) |
| `pip3: command not found` | Normal on Unifi Gateway | [Missing Dependencies](#3-missing-dependencies) |
| Can't find AirGradient device | mDNS not working | [Finding Device IP](#4-finding-device-ip-addresses) |
| Google Sheets not updating | Form configuration | [Google Sheets](#5-google-sheets-issues) |

---

## 1. Wrong Script on Unifi Gateway

### ❌ Problem
```bash
root@Cloud-Gateway-Ultra:/data/scripts# python3 collect_air_quality.py
ModuleNotFoundError: No module named 'dotenv'
```

### ✅ Solution
Use `collect_air.py` (simplified version), NOT `collect_air_quality.py`:
```bash
python3 /data/scripts/collect_air.py
```

**Why?** The setup script creates a simplified version without Python dependencies that aren't available on the gateway.

---

## 2. AirGradient Connection Issues

### ❌ Problem
```
Indoor: 0.0 μg/m³, Outdoor: 0 μg/m³, Efficiency: 0.0%
```

### ✅ Solution

**Step 1: Find your AirGradient's IP address**
```bash
# Check ARP table for devices with AirGradient MAC prefix
arp -a | grep -i 'd8:3b:da'

# Example output:
# esp32c3-XXXXXX (192.168.X.XX) at d8:3b:da:XX:XX:XX [ether] on brXX
```

**Step 2: Test the connection**
```bash
# Replace with your IP
curl -s http://192.168.X.XX/measures/current | python3 -m json.tool | head -10
```

**Step 3: Update the script with the IP**
```bash
# Replace the hostname with IP address
sed -i 's|http://airgradient.*local|http://192.168.X.XX|' /data/scripts/collect_air.py
```

**Step 4: Test again**
```bash
python3 /data/scripts/collect_air.py
```

---

## 3. Missing Dependencies

### ❌ Problem
```bash
./setup_unifi.sh: line 13: pip3: command not found
```

### ✅ Solution
This is **normal** - Unifi Gateway doesn't have pip3. The simplified script uses only built-in Python modules.

If you absolutely need additional packages:
```bash
# Fix apt sources first (bullseye-backports is deprecated)
sed -i '/bullseye-backports/d' /etc/apt/sources.list
apt-get update

# Install python3-requests (if needed)
apt-get install -y python3-requests
```

---

## 4. Finding Device IP Addresses

### ❌ Problem
mDNS hostnames like `airgradient_SERIAL.local` don't resolve on Unifi Gateway.

### ✅ Solution

**Option A: Check ARP table (recommended)**
```bash
# Find by MAC prefix (d8:3b:da for AirGradient)
arp -a | grep -i 'd8:3b:da'
```

**Option B: Check your Unifi Controller**
1. Open Unifi Network app
2. Go to Clients
3. Look for devices named "esp32" or containing your serial
4. Note the IP address

**Option C: Scan the network**
```bash
# If nmap is available
nmap -sn 192.168.X.0/24 | grep -B2 -i "d8:3b:da"
```

---

## 5. Google Sheets Issues

### ❌ Problem
Data collection works but Google Sheets doesn't update.

### ✅ Solution

**Step 1: Verify form configuration**
```bash
# Check your .env has all required fields
grep FORM_ /data/scripts/.env
```

**Step 2: Test form submission manually**
```bash
# Get a recent log entry
tail -1 /data/logs/air_quality.jsonl

# Check for errors in collection log
grep -i error /data/logs/collection.log | tail -10
```

**Step 3: Common form field mapping issues**
- Make sure ALL form fields in `.env` have correct entry IDs
- Entry IDs look like: `entry.1234567890`
- Get them by: Form → Get pre-filled link → Inspect HTML

---

## 6. Cron Job Not Running

### ❌ Problem
No new entries in `/data/logs/collection.log`.

### ✅ Solution

**Check if cron job exists:**
```bash
crontab -l
# Should show: */5 * * * * /usr/bin/python3 /data/scripts/collect_air.py >> /data/logs/collection.log 2>&1
```

**If missing, add it:**
```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/python3 /data/scripts/collect_air.py >> /data/logs/collection.log 2>&1") | crontab -
```

**Check cron is running:**
```bash
ps aux | grep cron
# or
service cron status
```

---

## 7. SSH Access Issues

See [ssh_into_uni_fi_cloud_gateway_ultra.md](ssh_into_uni_fi_cloud_gateway_ultra.md) for detailed SSH setup.

Common fix:
```bash
# Clear old SSH key
ssh-keygen -R 192.168.X.X

# Reconnect
ssh root@192.168.X.X
```

---

## Complete Working Example

Here's what a successful run looks like:

```bash
root@Cloud-Gateway-Ultra:/data/scripts# python3 /data/scripts/collect_air.py
✓ Data sent to Google Sheets at 2025-07-26 15:28:36.924007
Indoor: 0.0 μg/m³, Outdoor: 3.23 μg/m³, Efficiency: 100.0%
```

If you see this, everything is working! The data is being:
1. ✅ Collected from Airthings (indoor)
2. ✅ Collected from AirGradient (outdoor)  
3. ✅ Sent to Google Sheets
4. ✅ Logged locally to `/data/logs/air_quality.jsonl`

---

## Still Stuck?

1. **Check the logs:**
   ```bash
   tail -50 /data/logs/collection.log
   ```

2. **Run with Python debugging:**
   ```bash
   python3 -u /data/scripts/collect_air.py
   ```

3. **Verify network connectivity:**
   ```bash
   # Can you reach Airthings?
   curl -I https://accounts-api.airthings.com/v1/token
   
   # Can you reach Google?
   curl -I https://docs.google.com
   ```

4. **Check file permissions:**
   ```bash
   ls -la /data/scripts/
   ls -la /data/logs/
   ```

Remember: The goal is to automate filter replacement decisions. Even if some features don't work perfectly, as long as you're getting PM2.5 data, you can track filter efficiency!