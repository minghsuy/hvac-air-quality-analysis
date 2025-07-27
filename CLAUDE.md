# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an HVAC air quality monitoring system designed to track filter efficiency and predict replacement timing to prevent asthma symptoms. The system compares indoor air quality (Airthings) vs outdoor air quality (AirGradient) to calculate real-time filter efficiency.

## Key Commands

### Development Environment Setup
```bash
# Install uv and create environment
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

### Running Tests
```bash
# Run tests with pytest
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Fix linting issues
ruff check --fix .
```

### Running the Collector
```bash
# Run locally (test mode)
python collect_air_quality.py

# Run analysis on historical data
python analyze_historical.py
```

## Architecture Overview

### Data Collection Flow
1. **Unifi Gateway** (every 5 minutes):
   - Runs `collect_air.py` via cron
   - Fetches indoor data from Airthings API
   - Fetches outdoor data from AirGradient local API
   - Calculates filter efficiency
   - Logs to Google Sheets and local JSONL

2. **Local Analysis** (on-demand):
   - `analyze_historical.py`: Analyzes CSV exports from Airthings
   - `analysis.ipynb`: Interactive Jupyter notebook for Claude-assisted analysis

### Key Thresholds
- **Filter Efficiency < 85%**: Alert threshold
- **Filter Efficiency < 80%**: Plan replacement
- **Indoor PM2.5 > 12 μg/m³**: Replace immediately (WHO guideline)

### API Integrations
- **Airthings**: OAuth2 client credentials flow for indoor air quality
- **AirGradient**: Local mDNS API (no auth) for outdoor air quality
- **Google Sheets**: Form submission API for data logging

## Project Structure

```
hvac-air-quality-analysis/
├── collect_air_quality.py    # Main data collector (runs on Unifi)
├── analyze_historical.py     # Historical data analyzer
├── analysis.ipynb           # Interactive analysis notebook
├── setup_unifi.sh          # Unifi Gateway setup script
├── pyproject.toml          # uv package management
├── .env.example            # Environment variable template
└── data/                   # Data directory (gitignored)
```

## Environment Variables

All secrets are stored in `.env` (never commit!):
- `AIRTHINGS_CLIENT_ID/SECRET`: OAuth credentials
- `AIRTHINGS_DEVICE_SERIAL`: Device to monitor
- `AIRGRADIENT_SERIAL`: Local sensor serial
- `GOOGLE_FORM_ID`: Form for data logging
- `FORM_*`: Field IDs for form submission

## Unifi Gateway Setup

The system runs on a Unifi Cloud Gateway Ultra:
1. SSH access enabled (see `ssh_into_uni_fi_cloud_gateway_ultra.md`)
2. Python3 and minimal dependencies installed
3. Cron job runs collector every 5 minutes
4. Data persists in `/data/scripts/` and `/data/logs/`

## Cost Tracking

Current filter costs:
- HVAC filter (MERV 15): $130
- ERV filter (MERV 13): $50
- Goal: Extend filter life from 45 days to 120+ days
- Target daily cost: < $1.50/day

## Health Correlation

The system aims to prevent asthma symptoms by replacing filters before efficiency drops too low. Key events tracked:
- Filter installation dates
- Efficiency degradation rates
- Indoor air quality exceedances
- Health symptoms (optional manual tracking)

## Important Security Reminders

**NEVER commit or expose:**
- Device MAC addresses (e.g., `d8:3b:da:XX:XX:XX`)
- Local IP addresses (e.g., `192.168.X.XX`)
- Device serial numbers in logs or examples
- Any network-specific identifiers

Always use generic placeholders (XX, X.XX) in documentation and examples. Check all commits for accidentally exposed network information before pushing to public repositories.

## GitHub Wiki Management (Learned: July 27, 2025)

### Key Learnings About GitHub Wiki

1. **Wiki is a Separate Repository**
   - Main repo: `https://github.com/username/project.git`
   - Wiki repo: `https://github.com/username/project.wiki.git`
   - They are completely separate git repositories

2. **Directory Structure**
   - Wiki has a flat structure - all pages are .md files in root
   - No subdirectories for organization
   - Page names become URLs (spaces → hyphens)

3. **Cloning and Working with Wiki**
   ```bash
   # Clone wiki to a separate directory
   git clone https://github.com/username/project.wiki.git
   
   # Or if inside main project, use a subdirectory
   git clone https://github.com/username/project.wiki.git wiki-repo
   cd wiki-repo
   ```

4. **Image Handling in Wiki**
   - Wiki cannot directly embed images from main repo
   - Images show as links, not embedded
   - Options:
     - Upload images to wiki repo itself
     - Use external image hosting
     - Reference raw GitHub content URLs from main repo

5. **Common Confusion Points**
   - Forgetting which directory you're in (main vs wiki)
   - Trying to use relative paths between repos
   - Expecting wiki pages in main repo to auto-sync
   - Working directory confusion when using `cd` commands

6. **Best Practices**
   - Keep wiki content in wiki repo only
   - Don't duplicate wiki content in main repo
   - Use wiki for documentation, main repo for code
   - Clone wiki separately when doing major updates
   - Always verify current directory with `pwd`

### For This Project
- Wiki URL: https://github.com/minghsuy/hvac-air-quality-analysis/wiki
- Wiki clone: `git clone https://github.com/minghsuy/hvac-air-quality-analysis.wiki.git`
- Pages created: Home, Hardware-Setup, Data-Collection, Analysis-Results, Analysis-Techniques
- Images referenced from: `/data/figures/` in main repo (as links)

### Lesson Learned
Don't assume wiki pages can be managed from main repo - they're separate! Always check which directory/repo you're working in. The wiki is its own git repository with its own commit history.

### ⚠️ Wiki Repository Critical Warning
**See global CLAUDE.md (`~/.claude/CLAUDE.md`) for critical warnings about wiki-repo management!**

Quick reminder:
- `wiki-repo/` is a SEPARATE Git repository
- NEVER `git add wiki-repo` or `git rm --cached wiki-repo`
- It's already in .gitignore for safety
- When in doubt, check the global CLAUDE.md for full wiki safety guidelines

## Plotly X-Axis Date Formatting (Learned: July 27, 2025)

### Problem
When exporting Plotly charts to PNG using kaleido, datetime x-axis values often display as scientific notation (e.g., 1.745×10¹⁸), making the charts unreadable.

### Solution
Convert datetime index to string format before plotting to avoid scientific notation:

```python
# Bad - causes scientific notation in exported images
fig.add_trace(go.Scatter(x=df.index, y=df['value']))

# Good - readable date labels
x_dates = df.index.strftime('%b %d')  # Convert to string format
fig.add_trace(go.Scatter(x=x_dates, y=df['value']))

# For sparse labels on long timeseries
num_ticks = 5
tick_step = len(x_dates) // num_ticks
fig.update_xaxes(
    tickmode='array',
    tickvals=x_dates[::tick_step],
    ticktext=x_dates[::tick_step],
    tickangle=-45,
    row=1, col=2  # if using subplots
)
```

### Additional Fixes for Subplots with Dates

1. **Use shapes instead of vlines for datetime x-axis in subplots**:
```python
# Bad - causes TypeError with datetime
fig.add_vline(x=event_date, line_dash="dash")

# Good - works with datetime
fig.add_shape(
    type="line",
    x0=event_date, x1=event_date,
    y0=0, y1=1,
    xref="x", yref="paper",
    line=dict(color="gray", width=1, dash="dash")
)
```

2. **Handle string dates in annotations/shapes**:
```python
# When using string x-axis, find the corresponding string label
merv13_idx = (df.index.date == event_date.date()).argmax()
merv13_label = x_dates[merv13_idx]
fig.add_shape(x0=merv13_label, x1=merv13_label, ...)
```

### Key Learnings
1. **String conversion**: Always use `strftime()` when exporting Plotly to static images
2. **Sparse ticks**: Use array slicing to show fewer labels for readability  
3. **Type consistency**: Keep x-axis data type consistent (all datetime or all strings)
4. **Cache busting**: If GitHub shows old images, rename files (e.g., `image.png` → `image_v2.png`)

### Common Pitfall
Even if the plot looks fine in Jupyter/browser, kaleido export may still show scientific notation. Always check the exported PNG file!

## Visualization Workflow Best Practices (Learned: July 27, 2025)

### Key Learning: Use Existing Tools, Don't Reinvent

After initially trying to build a custom visualization pipeline, I learned from the research in `docs/compass_artifact_*.md` that excellent solutions already exist:

1. **Quarto** - The modern "write once, deploy everywhere" solution
   - Converts Jupyter notebooks to multiple formats automatically
   - Handles figure exports properly
   - Built-in support for GitHub Flavored Markdown and Hugo

2. **Playwright > Kaleido** - For reliable Plotly exports
   - Kaleido has issues with datetime axes (scientific notation)
   - Playwright is more reliable and maintained
   - Simple wrapper function solves export problems

3. **nb2hugo** - Direct Jupyter to Hugo integration
   - No intermediate steps needed
   - Preserves markdown and code structure
   - Handles front matter automatically

### Recommended Workflow

```bash
# For new projects: Use Quarto
quarto convert analysis.ipynb
quarto render analysis.qmd --to gfm    # For GitHub Wiki
quarto render analysis.qmd --to hugo   # For Hugo blog

# For existing Hugo sites: Use nb2hugo
pip install nb2hugo
nb2hugo analysis.ipynb --site-dir hugo-site --section posts

# For reliable Plotly exports: Use Playwright
from playwright.sync_api import sync_playwright
# See VISUALIZATION_WORKFLOW.md for implementation
```

### Visualization Best Practices

1. **Scale Appropriately**
   - Don't add reference lines far outside your data range
   - WHO guideline at 15 μg/m³ is useless when your data is 0-3 μg/m³
   - Focus on what's relevant to YOUR data

2. **Context Matters**
   - Add annotations for important events
   - Use color meaningfully (red=bad, green=good)
   - Include period markers (vacation, system failures)
   - Show before/after averages when relevant

3. **Platform Awareness**
   - GitHub Wiki: Use PNGs with proper paths
   - Hugo: Can handle interactive HTML/JSON
   - Both: Need self-contained images

### Anti-Patterns to Avoid

1. ❌ Building custom export pipelines when Quarto exists
2. ❌ Using kaleido for datetime axes (use Playwright)
3. ❌ Adding every possible reference line
4. ❌ Forgetting to check exported images
5. ❌ Ignoring existing research and solutions

### The Golden Rule

**Always check if someone has already solved your problem before building a custom solution.**

In this case, the `docs/compass_artifact_*.md` file had already researched and found the best solutions. Read existing research before implementing!

## Wiki Documentation Best Practices (Learned: July 27, 2025)

### Key Learning: Maintain Coherence Across Wiki Pages

When creating or updating wiki documentation, several issues can arise that break the user experience:

1. **Broken Internal Links**
   - Always verify linked pages actually exist
   - Use exact page names (GitHub Wiki is case-sensitive)
   - Remove references to planned but unimplemented pages

2. **Inconsistent Information**
   - Cost savings numbers should match across all pages
   - Timeline descriptions must be clear (e.g., "6 months total, 70 days with MERV 13")
   - Technical specifications should be identical everywhere mentioned

3. **Navigation Flow**
   - Each page should link to the next logical step
   - Add navigation footers: "**Ready for next step?** → [Next Page](Next-Page)"
   - Ensure circular references don't trap users

4. **Personal Story Integration**
   - Technical documentation becomes more compelling with personal context
   - Add "Why This Matters" sections to connect features to real impact
   - Don't just list specs - explain why you chose them

### Wiki Creation Checklist

Before publishing wiki updates:
- [ ] Run link checker: `grep -r '\[.*\](' . | grep -v '.git'`
- [ ] Verify all internal links resolve to actual pages
- [ ] Check cost/savings numbers are consistent
- [ ] Ensure timeline descriptions match across pages
- [ ] Add personal impact sections where relevant
- [ ] Include navigation footers on each page
- [ ] Test the user journey from start to finish

### Example: Coherent Cost Messaging
```markdown
# Bad - Inconsistent across pages
Page 1: "Save $910/year"
Page 2: "Save up to $1000 annually"  
Page 3: "Savings of $500+"

# Good - Consistent and accurate
All pages: "Save $130-910/year depending on replacement schedule"
```

### Example: Clear Timeline Communication
```markdown
# Bad - Ambiguous
"After 6 months with MERV 13 filters"

# Good - Specific
"After 6 months of total monitoring (including 70 days with MERV 13 filters)"
```

### The Wiki Coherence Principle

**Every wiki page should stand alone AND work as part of the whole.** Readers might land on any page from search, so provide context while maintaining a coherent narrative across all pages.

## Release Process and Versioning (Added: July 27, 2025)

### ⚠️ CRITICAL: This is NOT a Packaged Project!
- **Flat file structure** - Python scripts in root directory
- **NOT using src/ layout** - Scripts must remain in root for Unifi Gateway
- **NOT publishing to PyPI** - GitHub releases only
- **No package building** - Just archive the scripts

### What Actually Works (Learned the Hard Way)
1. **Project Structure**: Keep it flat!
   ```
   hvac-air-quality-analysis/
   ├── *.py                    # All Python scripts in root
   ├── scripts/                # Utility scripts
   ├── tests/                  # Test files
   └── .github/workflows/      # CI/CD
   ```

2. **Release Workflow**: Creates ZIP/TAR archives, NOT Python packages
   ```yaml
   # This FAILS - don't use!
   uv build  # ❌ Will fail with "Multiple top-level modules"
   
   # This WORKS - use archives!
   zip -r dist/hvac-air-quality-v0.2.0.zip *.py scripts/ tests/  # ✅
   ```

3. **Version Tracking**: Only in `pyproject.toml` (no __init__.py)

### Release Checklist (Do This EXACTLY)
```bash
# 1. Update version in pyproject.toml (remove -dev suffix)
# 2. Update CHANGELOG.md - move items from Unreleased to new version section
# 3. Update the comparison links at bottom of CHANGELOG.md
# 4. Commit changes
git add -A
git commit -m "chore(release): prepare for vX.Y.Z"
git push origin main

# 5. Create and push tag (this triggers release)
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z

# 6. If release fails, fix the issue, then:
git tag -d vX.Y.Z                    # Delete local tag
git push origin :refs/tags/vX.Y.Z    # Delete remote tag
# Then recreate tag after fixing
```

### Common Release Failures and Fixes
1. **"Multiple top-level modules" error**
   - Cause: `uv build` trying to create Python package
   - Fix: Use ZIP/TAR archives instead

2. **Tar command fails**
   - Cause: Wrong argument order
   - Fix: `tar --exclude="*.pyc" -czf archive.tar.gz files...`

3. **No release appears**
   - Cause: Workflow failed
   - Fix: Check `gh run list --workflow=release.yml`

### pyproject.toml Configuration
```toml
[tool.uv]
package = false  # CRITICAL: Tell uv this isn't a package!
```

### What Gets Released
- `hvac-air-quality-vX.Y.Z.zip` - ZIP archive
- `hvac-air-quality-vX.Y.Z.tar.gz` - Tarball
- Automated release notes from CHANGELOG.md
- NO Python wheels or sdist (not a package!)

### GitHub Actions Workflows
- `.github/workflows/test.yml` - Runs on every push
- `.github/workflows/release.yml` - Runs on version tags (v*)
- Uses `uv sync --dev` (NOT `uv build`)

### Important Notes
- Author: Ming Yang (not Ming Hsuy)
- No email in public package metadata for privacy
- This is a collection of scripts, NOT a Python package
- Keep the flat structure for Unifi Gateway compatibility