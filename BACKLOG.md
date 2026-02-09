# HVAC Air Quality Project - Backlog

> Prioritized task list for Claude Code and human collaboration
> 
> Last updated: January 2026
> Target: LinkedIn post in March 2026

## Priority Legend

- 🔴 P0: Must do before LinkedIn post
- 🟡 P1: Should do, high impact
- 🟢 P2: Nice to have
- ⚪ P3: Future / someday

---

## Phase 1: Polish for LinkedIn (Target: March 2026)

### 🔴 P0: README Restructure

- [ ] **Surface the "Why" story in README**
  - Copy opening paragraph from Wiki "Why This Project Matters"
  - Add link to full Wiki story
  - Move technical content below the human story

- [ ] **Add "Results" section to README**
  ```markdown
  ## Results
  
  ### For My Family
  - Son's bedroom CO2: 1000+ ppm → 600 ppm (with ERV)
  - Son's sickness: every 45 days → healthy all fall/winter 2025
  - Sleep quality: improved (stable temps, no gas furnace cycling)
  
  ### From the Data (82,791 readings)
  - Filters maintain >85% efficiency for 120+ days (not 45 as marketed)
  - Filter at 197% of "max life" still performed at 87.3%
  - Saved $130-910/year on unnecessary filter replacements
  ```

- [ ] **Add architecture diagram to README**
  - Show sensor → collection → sheets → alerting flow
  - Mermaid diagram preferred (renders on GitHub)

### 🔴 P0: Visualizations

- [ ] **Create CO2 before/after chart**
  - Time series showing CO2 levels
  - Annotate "ERV installed" point
  - Show 1000 ppm threshold line
  - Export as PNG for README and LinkedIn

- [ ] **Create filter efficiency over time chart**
  - Show efficiency staying >85% past 120 days
  - Annotate manufacturer's "replace at 45 days" point
  - Prove the contrarian finding visually

- [ ] **Create indoor vs outdoor PM2.5 during wildfire**
  - If you have data from a high AQI day
  - Show "AQI 200+ outside, <20 inside"
  - California angle for broader appeal

### 🟡 P1: Documentation Cleanup

- [ ] **Add dashboard screenshot to README**
  - Screenshot of Google Sheets with data
  - Or create a simple HTML visualization

- [ ] **Sync Wiki content with README**
  - Ensure no duplication/contradiction
  - Wiki = deep dive, README = overview + results

- [ ] **Review and update LESSONS_LEARNED.md**
  - Add recent discoveries
  - Document what worked

---

## Phase 2: Webapp Dashboard (Target: May 2026)

### 🟡 P1: Dashboard MVP

- [ ] **Set up React/Next.js project**
  - Learn TSX through building
  - Simple, mobile-friendly design

- [ ] **Connect to Google Sheets API**
  - Read recent data
  - Service account auth

- [ ] **Dashboard views**
  - [ ] Current status (CO2, PM2.5, efficiency, ERV state)
  - [ ] 24-hour trends
  - [ ] Filter status (days since change, efficiency)
  - [ ] Room comparison (son's room vs master)

- [ ] **Host on DGX Spark**
  - Always-on home server
  - Local network access
  - Optional: expose via Tailscale

### 🟢 P2: Dashboard Enhancements

- [ ] Add historical views (7-day, 30-day)
- [ ] Add wildfire smoke alerts
- [ ] Add recommendations panel
- [ ] Mobile app wrapper (PWA)

---

## Phase 3: Automation (Target: Later 2026)

### 🟢 P2: ERV Control

- [ ] **Research ERV control options**
  - Smart relay on ERV power?
  - Integration with existing switches?
  - Home Assistant bridge?

- [ ] **Implement basic on/off control**
  - When outdoor AQI > 35, turn off
  - When outdoor AQI < 15, turn on
  - Cooldown periods to avoid cycling

### 🟢 P2: Carrier Integration

- [ ] **Research Carrier Infinity API**
  - Côr thermostat API?
  - Local control vs cloud?

- [ ] **Implement filter status sync**
  - Read filter runtime from Carrier
  - Correlate with efficiency data

---

## Phase 4: Make it Deployable (Target: 2027)

### ⚪ P3: Simplified Setup

- [ ] One-click sensor discovery
- [ ] Configuration wizard
- [ ] Pre-built Docker containers
- [ ] Setup documentation for non-engineers

### ⚪ P3: Multi-family Support

- [ ] Support different sensor combinations
- [ ] Configurable alerting rules
- [ ] Dashboard templates

---

## Wiki Repository Management

The GitHub Wiki is a **separate git repository**. Handle it carefully:

```bash
# Wiki repo location
/Users/ming/Documents/Github/hvac-air-quality-analysis/wiki-repo/

# Clone if not exists
git clone https://github.com/minghsuy/hvac-air-quality-analysis.wiki.git wiki-repo

# Update wiki
cd wiki-repo
git pull
# make changes
git add -A
git commit -m "Update wiki content"
git push

# NEVER do this (embeds git repo in git repo):
git add wiki-repo  # NO!
```

**Wiki is in .gitignore** - this is correct, keep it that way.

### Wiki Content Plan

| Page | Status | Notes |
|------|--------|-------|
| Home | ✅ Exists | Overview |
| Why This Project Matters | ✅ Exists | Personal story - the hook |
| Hardware Setup | ✅ Exists | Sensor details |
| Software Setup | ✅ Exists | Installation |
| Data Collection | ✅ Exists | How it works |
| Analysis Results | ✅ Exists | Findings |
| Analysis Techniques | ✅ Exists | Methodology |

---

## LinkedIn Post Draft (for March)

```
My mother lived next to a freeway for 20 years. The constant coughing. The asthma. The cancer.

After she passed, I became obsessed with air quality. My son was getting sick every 45 days. My wife has asthma.

So I built a monitoring system. 82,791 sensor readings later:

📊 Finding #1: Filters last 120+ days at >85% efficiency (manufacturers say 45)
📊 Finding #2: A bedroom with 2 people easily exceeds 1000 ppm CO2 (cognitive impairment threshold)
📊 Finding #3: My son hasn't been sick since fall 2025

The ROI on air quality monitoring beats tutoring and private school for cognitive development.

Open sourced so other families can benefit.

GitHub: [link]

#DataScience #AirQuality #ParentingWithData #OpenSource
```

---

## Notes for Claude Code

When working on this project:

1. **Read CLAUDE.md first** - contains git workflow, security checks, package management rules
2. **Use feature branches** - never push to main directly
3. **Run security grep before commits** - check for IPs, emails, credentials
4. **Use uv, not pip** - this project uses uv package manager
5. **Wiki is separate** - don't try to git add wiki-repo

When creating visualizations:
- Use Plotly or Matplotlib
- Export as PNG for README/LinkedIn
- Keep it simple - one insight per chart
- Add annotations to highlight key points
