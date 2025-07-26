# GitHub Repository Setup

## What to Commit vs What to Keep Private

### ✅ Safe to Commit to GitHub

These files contain no sensitive information:

```
hvac-air-quality/
├── README.md               # Documentation
├── QUICKSTART.md          # Setup guide
├── pyproject.toml         # Python dependencies
├── .gitignore            # Tells git what to ignore
├── .env.example          # Template (no real values)
├── analysis.ipynb        # Analysis notebook
├── analyze_historical.py # Historical data analyzer
├── collect_air_quality.py # Data collector script
└── setup_unifi.sh        # Unifi setup script
```

### ❌ Never Commit to GitHub

These contain personal/sensitive data:

```
.env                      # Your actual credentials
data/                     # Your air quality data
logs/                     # System logs
*.csv                     # Exported data files
*.json                    # API responses with your data
airthings_config.json     # If you create one
```

## Why Make This Public?

1. **Help others** with similar air quality concerns
2. **Get contributions** from the community
3. **Track your code changes** over time
4. **Portfolio** for showing your data science work

Your **actual data** stays private - only the code is public.

## Initial GitHub Setup

```bash
# 1. Create repository on GitHub (via web)
# Name: hvac-air-quality
# Make it public, add README

# 2. In your local project
git init
git add .
git commit -m "Initial commit - HVAC air quality monitoring"

# 3. Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/hvac-air-quality.git
git branch -M main
git push -u origin main

# 4. Verify .env is NOT in the repository
git status  # Should not show .env
```

## Before Every Commit

```bash
# Always check what you're about to commit
git status
git diff --staged

# If you accidentally staged .env
git reset .env

# Good practice: commit message explains what changed
git add analyze_historical.py
git commit -m "Add historical CSV analyzer with 2025 timeline"
```

## Example Repository Description

> 🏠 **Smart HVAC Filter Monitoring**
> 
> Track filter efficiency using Airthings (indoor) and AirGradient (outdoor) sensors to optimize replacement timing and prevent asthma triggers. Runs on Unifi Gateway with Google Sheets logging.
> 
> **Goal**: Replace filters based on actual performance, not arbitrary schedules.
> 
> **Features**:
> - Hourly efficiency calculations
> - Predictive replacement alerts
> - Cost optimization analysis
> - Health event correlation

## Adding a License

Consider adding a LICENSE file:

```
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

This lets others use and improve your code while giving you credit.

## Security Checklist

- [ ] `.env` is in `.gitignore`
- [ ] No API keys in any Python files
- [ ] No device serial numbers in committed files
- [ ] No personal health data in repository
- [ ] Used `.env.example` as template only

## If You Accidentally Commit Secrets

```bash
# If you haven't pushed yet
git reset --soft HEAD~1
# Remove the file and recommit

# If you already pushed (requires force push)
# 1. Delete and recreate your API credentials first!
# 2. Then remove from history
git filter-branch --tree-filter 'rm -f .env' HEAD
git push --force
```

Remember: Once something is on GitHub, assume it's public forever - that's why we rotate credentials if exposed.
