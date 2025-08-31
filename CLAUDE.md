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
# 2. Update CHANGELOG.md
git add -A
git commit -m "chore(release): prepare for vX.Y.Z"
git push

# 3. Create and push tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z

# 4. After release, bump to dev version
# Update pyproject.toml to X.Y.Z+1-dev
git add -A
git commit -m "chore: bump version to X.Y.Z+1-dev"
git push
```

## ⚠️ Package Management: Use UV, NOT pip!

```bash
# CORRECT ✅
uv sync                   # Install dependencies
uv add package-name       # Add new package
uv run pytest            # Run with uv environment

# WRONG ❌ - NEVER DO THIS:
pip install anything     # NO!
pip freeze > requirements.txt  # NO!
```

**Exception:** Unifi Gateway uses pip3 (no uv available there)

## ⚠️ This is NOT a Python Package!

- **Flat structure required** for Unifi Gateway compatibility
- Scripts stay in root directory, NOT src/
- GitHub releases create ZIP/TAR archives, NOT wheels
- `pyproject.toml` has `package = false` 

## 🔒 Security: Never Expose Network Info

**NEVER commit:**
- Device MAC addresses (d8:3b:da:XX:XX:XX)
- Local IP addresses (192.168.X.XX)  
- Device serial numbers
- API keys or credentials
- Personal email addresses

**Always use:** Generic placeholders in docs/examples

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

### Development
```bash
uv venv --python 3.12
source .venv/bin/activate  
uv sync --dev
```

### Testing & Quality
```bash
uv run pytest
uv run ruff check . --fix
uv run ruff format .
```

### Running Collectors
```bash
python collect_with_sheets_api.py  # Multi-sensor with Sheets API
python collect_multi_fixed.py      # For Unifi (hardcoded IPs)
```

## 🔍 Quick Fixes for Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `uv sync` |
| ".local doesn't resolve" | Use collect_multi_fixed.py with IPs |
| "No pip3 on Unifi" | `apt update && apt install python3-pip` |
| Release workflow fails | Check you ran tests/linting first |
| 49 linting errors | You forgot pre-release checks |

## 📚 Documentation Structure

- **This file**: Critical guardrails only
- [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md): What and why
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): How it works  
- [`docs/LESSONS_LEARNED.md`](docs/LESSONS_LEARNED.md): Historical context
- [`docs/ENVIRONMENT_SETUP.md`](docs/ENVIRONMENT_SETUP.md): Configuration
- [`RELEASING.md`](RELEASING.md): Detailed release process
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md): What we learned from v0.3.0

## Remember

1. **Always run tests/linting before release**
2. **Use uv, never pip (except Unifi)**  
3. **Wiki is separate - never embed it**
4. **Check for exposed secrets before pushing**
5. **This isn't a Python package - use flat structure**