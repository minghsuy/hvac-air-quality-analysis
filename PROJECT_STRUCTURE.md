# Project Structure (Cleaned)

## 📁 Main Directory

### Essential Files
- **collect_air_quality.py** - Main data collector (runs on Unifi)
- **analyze_historical.py** - Analyze your Airthings CSV export
- **analysis.ipynb** - Jupyter notebook for interactive analysis
- **setup_unifi.sh** - Script to setup on Unifi Gateway
- **pyproject.toml** - Python dependencies (for uv)

### Configuration
- **.env** - Your actual credentials (NEVER commit!)
- **.env.example** - Template for .env file
- **.gitignore** - Tells git what to ignore

### Documentation
- **README.md** - Project overview
- **START_HERE.md** - Quick start guide
- **filter_changes_template.csv** - Template for tracking filter replacements

### Directories
- **data/** - For your air quality data files
- **docs/** - Additional documentation
  - GITHUB_SETUP.md - How to use GitHub
  - QUICKSTART.md - Detailed setup instructions
  - google-form-setup.md - Google Form setup guide
  - sheets-formulas.md - Google Sheets formulas
- **old_versions/** - Backup of old/duplicate files
- **.venv/** - Python virtual environment
- **.git/** - Git repository data

## 🚀 Next Steps

1. Check your `.env` file has all credentials
2. Test the collector: `python collect_air_quality.py`
3. Deploy to Unifi: `scp collect_air_quality.py setup_unifi.sh root@gateway-ip:/data/scripts/`
4. Follow setup instructions in START_HERE.md
