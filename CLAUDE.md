# CLAUDE.md - Critical Guardrails

**PURPOSE:** Prevent common mistakes when working with this codebase. Read this FIRST.

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

## ⚠️ Package Management: Use UV, NOT pip!

```bash
# CORRECT ✅
uv sync                   # Install dependencies
uv add package-name       # Add new package
uv run pytest            # Run with uv environment
uv run ruff format .     # Format code

# WRONG ❌ - NEVER DO THIS:
pip install anything     # NO!
pip freeze > requirements.txt  # NO!
python -m pip install    # NO!
```

**Exception:** Unifi Gateway uses pip3 (no uv available there)

## ⚠️ This is NOT a Python Package!

- **Flat structure required** for Unifi Gateway compatibility
- Scripts stay in root directory, NOT src/
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

## ⚠️ Wiki Repository Management

**GitHub Wiki = SEPARATE Git Repository!**

```bash
# CORRECT ✅
git clone https://github.com/username/project.wiki.git wiki-repo
cd wiki-repo
git add/commit/push  # Manage separately

# WRONG ❌ - DISASTER:
git add wiki-repo    # NO! Embedding git repo
git rm --cached wiki-repo  # NO! Can delete work
```

**Always:** Keep `wiki-repo/` in .gitignore

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

# Deploy to Unifi
./scripts/deploy_to_unifi.sh

# Update sensor IPs
python scripts/update_airgradient_ips.py
```

## 🔍 Quick Fixes for Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `uv sync --dev` |
| ".local doesn't resolve" | Run `scripts/update_airgradient_ips.py` |
| "No pip3 on Unifi" | `apt update && apt install python3-pip` |
| Release workflow fails | Check you ran tests/linting first |
| Sheet not updating | Check GOOGLE_SHEET_TAB in .env |
| Cron not running | Run `/data/scripts/SETUP_AFTER_FIRMWARE_UPDATE.sh` |

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
4. Save and test with `testAlert()` function
5. Check Script Properties has EMAIL_RECIPIENT set

## Remember

1. **Always run tests/linting before release**
2. **Use uv, never pip (except Unifi)**  
3. **Wiki is separate - never embed it**
4. **Check for exposed secrets before pushing**
5. **This isn't a Python package - use flat structure**
6. **Test v2 collector before deploying**
7. **Update sensor IPs when network changes**