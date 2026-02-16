# CLAUDE.md - Critical Guardrails

**PURPOSE:** Prevent common mistakes when working with this codebase. Read this FIRST.

## 📖 Project Context Files

| File | Purpose |
|------|--------|
| `CLAUDE_CODE_CONTEXT.md` | **Read this for project vision, architecture, and constraints** |
| `BACKLOG.md` | Prioritized task list (P0 = before March LinkedIn post) |
| `wiki-repo/Why-This-Project-Matters.md` | Personal story - the "why" |

**TL;DR Vision**: Transform this into a family health dashboard. North star = one family's kid gets sick less.

### Available Skills (user-level)
| Skill | Purpose |
|-------|---------|
| `/push-changes` | Commit with conventional format, blocks main pushes |
| `/release` | Full release workflow with version bump |
| `/review-loop` | Iterate on PR review comments |
| `/pr-comments` | Fetch and categorize PR review comments |
| `/hvac-status` | Check sensor collection status (project-level) |

## 🚨 CRITICAL: Release Process (Do This EXACTLY)

```bash
# BEFORE RELEASE - ALWAYS RUN THESE FIRST:
uv run pytest                     # Must pass all tests
uv run ruff check . --fix         # Fix linting issues  
uv run ruff format .              # Format code

# If any issues found, fix them BEFORE proceeding!

# RELEASE STEPS:
# 1. Update version in pyproject.toml (remove -dev)
# 2. Update CHANGELOG.md - move items to new version section
# 3. Update version links at bottom of CHANGELOG.md
git add -A
git commit -m "chore(release): prepare for vX.Y.Z"
git push

# 4. Create and push tag (this triggers release workflow)
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z

# 5. After release, bump to dev version
# Update pyproject.toml to X.Y.Z+1-dev
git add pyproject.toml
git commit -m "chore: bump version to X.Y.Z+1-dev"
git push
```

## ⚠️ This is NOT a Python Package!

- **Flat structure required** - scripts stay in root directory, NOT src/
- GitHub releases create ZIP/TAR archives, NOT wheels
- `pyproject.toml` has `package = false` 

## 🔒 Security: STOP! Check Before EVERY Commit

### Before EVERY git add:
```bash
# RUN THIS CHECK FIRST - ALWAYS!
grep -r "192\.168\." . --exclude-dir=.git --exclude-dir=.venv
grep -r "d8:3b:da" . --exclude-dir=.git --exclude-dir=.venv
grep -r "@.*\.com" . --exclude-dir=.git --exclude-dir=.venv
grep -r "GOOGLE_SPREADSHEET_ID.*=" . --exclude-dir=.git --exclude-dir=.venv

# If ANY results show up, YOU MUST fix them before committing!
```

**NEVER commit:**
- Device MAC addresses (d8:3b:da:XX:XX:XX)
- Local IP addresses (192.168.X.XX)  
- Device serial numbers (2960XXXXXX)
- API keys or credentials
- Personal email addresses
- Hardcoded spreadsheet IDs

**Replace with:**
- `192.168.X.XX` for IPs
- `XXXXXX` for serials/MACs
- `your_value_here` for credentials
- Use environment variables for IDs

## 📋 Essential Commands

### Development Setup
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment
uv venv --python 3.12
source .venv/bin/activate  
uv sync --dev
```

### Testing & Quality
```bash
uv run pytest                    # Run tests
uv run ruff check . --fix       # Fix linting
uv run ruff format .            # Format code
uv run mypy .                   # Type checking (if configured)
```

### Running Collectors
```bash
# Test locally with v2 (multi-room support)
python collect_with_sheets_api_v2.py

# Update sensor IPs
python scripts/update_airgradient_ips.py
```

### Dashboard
```bash
# Run dashboard (port 8501)
streamlit run scripts/dashboard.py --server.port 8501

# Parquet cache at .cache/air_quality.parquet (18ms vs 3.5s Sheets API)
# Use Spearman correlation for sensor data (robust to outliers, non-linear)
```

## 🔍 Quick Fixes for Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `uv sync --dev` |
| ".local doesn't resolve" | Run `scripts/update_airgradient_ips.py` |
| Release workflow fails | Check you ran tests/linting first |
| Sheet not updating | Check GOOGLE_SHEET_TAB in .env |
| Data collection stops after reboot/logout | Enable linger: `loginctl enable-linger $USER` |

## 🔄 Systemd User Services & Linger

When running the collector as a **user service** (`systemctl --user`), you must enable **linger** to keep services running after logout:

```bash
# Check if linger is enabled
loginctl show-user $USER | grep Linger

# Enable linger (required for services to survive logout/reboot)
loginctl enable-linger $USER

# Verify timer is running
systemctl --user status air-quality-collector.timer
```

**Why this matters:**
- Without linger: Services stop when you log out
- With linger: Services start at boot and run 24/7

**After system updates/reboots**, verify the timer is running:
```bash
journalctl --user -u air-quality-collector.timer --since "1 hour ago"
```

## 📊 Data Schema (v0.4.0)

### Current Implementation
- **18 columns** in Google Sheets (see DATA_DICTIONARY.md)
- **Multi-room support** with sensor identification
- **Smart alerting** with confidence levels
- **Native API units** (Bq/m³ for radon, not pCi/L)
- **Compensated values** for PM2.5 and temperature

### Key Fields
```python
# Always use compensated values when available
"pm02Compensated"  # NOT "pm02"
"atmpCompensated"  # NOT "atmp"
"rhumCompensated"  # NOT "rhum"

# Correct field names (camelCase)
"tvocIndex"        # NOT "tvoc_index"
"noxIndex"         # NOT "nox_index"
```

## 📚 Documentation Structure

- **README.md**: Project overview and quick start
- **TROUBLESHOOTING.md**: Common issues and solutions
- **DATA_DICTIONARY.md**: Complete field definitions
- **PROJECT_STRUCTURE.md**: File organization
- **RELEASE_CHECKLIST.md**: Release process details
- **docs/ARCHITECTURE.md**: System design
- **docs/LESSONS_LEARNED.md**: Historical insights

## 🚨 Pre-Commit Reminders

1. **Run security checks** (grep commands above)
2. **Test locally** before pushing
3. **Check logs** for errors
4. **Verify .env** has all required variables
5. **Update documentation** if changing functionality

## Google Apps Script Updates

When updating `apps_script_code.gs`:
1. Copy entire file contents
2. Open Google Sheets → Extensions → Apps Script
3. Replace all code
4. Save and test with `test()` function
5. Check Script Properties has `ALERT_EMAIL` and `ALERT_EMAIL_2` set

## HVACMonitor.gs (Google Apps Script)

**Current version:** `HVACMonitor_v3.gs` - simplified, efficiency-based monitoring

### Key Design Decisions

1. **Efficiency-based alerts, NOT load-based predictions**
   - Load-based filter life prediction doesn't work (proven by data)
   - Measure actual efficiency: `((outdoor - indoor) / outdoor) * 100`
   - Alert when efficiency drops below thresholds

2. **Seasonal minimum outdoor PM2.5 thresholds**
   ```javascript
   minOutdoorPM: {
     winter: 10,  // Dec-Feb: higher pollution
     summer: 5,   // Jun-Aug: clean air
     default: 7,  // Spring/Fall
   }
   ```

3. **Two types of filter tracking**
   - **Main/ERV filters**: Efficiency-based (measurable)
   - **Zone filters (12x12x1)**: Time-based only (90 days default)

4. **Configuration via Script Properties**
   - `LOCATION_LAT`, `LOCATION_LON`, `LOCATION_NAME`, `LOCATION_TIMEZONE`
   - `ALERT_EMAIL` for your alerts, `ALERT_EMAIL_2` for spouse alerts

### Updating HVACMonitor
1. Copy contents of `HVACMonitor_v3.gs`
2. Paste into Google Sheets → Extensions → Apps Script
3. Set Script Properties for your location
4. Set up triggers: `runAllChecks` (hourly), `weeklyReport` (weekly)
5. Run `calibrateEfficiencyThresholds()` monthly for your data

### Testing Functions
- `test()` - Test all alert checks (efficiency, indoor spike, AQI, pressure, CO2, data gaps, zone filters)
- `testIndoorSpike()` - Test indoor PM spike detection specifically
- `analyzeFilterReplacements()` - Compare before/after replacement
- `analyzeEfficiencyData()` - Validate measurement robustness

## Remember

1. **Always run tests/linting before release**
2. **Use uv, never pip**
3. **Wiki is separate - never embed it**
4. **Check for exposed secrets before pushing**
5. **This isn't a Python package - use flat structure**
6. **Test v2 collector before deploying**
7. **Update sensor IPs when network changes**