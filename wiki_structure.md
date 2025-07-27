# Suggested GitHub Wiki Structure for HVAC Air Quality Monitoring

## Wiki Pages to Create:

### 1. **Home** (Landing Page)
- Project overview and goals
- Quick links to all major sections
- Current system status (filters installed, days in service)
- Latest findings summary

### 2. **Hardware Setup**
#### 2.1 Indoor Monitoring
- Airthings View Plus setup and placement
- API configuration
- Known limitations (whole number rounding)

#### 2.2 Outdoor Monitoring  
- AirGradient ONE setup
- Weatherproofing considerations
- Network configuration
- Calibration procedures

#### 2.3 Unifi Gateway Integration
- SSH setup guide
- Python environment configuration
- Cron job scheduling
- Troubleshooting common issues

### 3. **Data Collection**
#### 3.1 Automated Collection
- `collect_air_quality.py` documentation
- Google Sheets integration
- API rate limits and best practices

#### 3.2 Manual Data Export
- Airthings dashboard export process
- Data cleaning procedures
- Handling missing data

### 4. **Analysis Techniques**
#### 4.1 Filter Efficiency Calculations
- Mathematical formula: (Outdoor - Indoor) / Outdoor × 100%
- Why indoor-only monitoring fails
- Precision requirements at low PM2.5 levels

#### 4.2 Performance Metrics
- Rolling averages (7-day, 24-hour)
- Seasonal adjustments
- Degradation rate calculations

#### 4.3 Cost Analysis
- Total cost of ownership calculations
- Manufacturer schedules vs data-driven replacement
- ROI of outdoor monitoring

### 5. **Decision Framework**
#### 5.1 Replacement Triggers
- Efficiency thresholds (85%, 80%, 75%)
- Absolute PM2.5 limits
- Event-based replacement (wildfires, construction)

#### 5.2 Emergency Scenarios
- Wildfire response protocol
- High pollen days
- System failure detection

### 6. **Technical Reference**
#### 6.1 API Documentation
- Airthings API endpoints and authentication
- AirGradient API structure
- Rate limiting and error handling

#### 6.2 Data Schemas
- CSV export formats
- Time zone handling
- Unit conversions

### 7. **Troubleshooting**
- Common issues and solutions
- ERV failure detection (vacation CO2 spike)
- Sensor drift and calibration
- Network connectivity problems

### 8. **Blog Posts & Reports**
- Links to published articles
- Key visualizations and findings
- Community feedback and discussions

### 9. **Future Enhancements**
- Planned improvements
- Integration ideas (Home Assistant, etc.)
- Research questions
- Community contributions

## Wiki Benefits:

1. **Versioned Documentation**: Track changes to procedures over time
2. **Searchable Knowledge Base**: Easy to find specific information
3. **Community Contributions**: Others can suggest improvements
4. **Separate from Code**: Keeps repository clean while maintaining detailed docs
5. **Rich Formatting**: Better for long-form explanations than README files

## Implementation Tips:

```bash
# Clone wiki locally for bulk editing
git clone https://github.com/yourusername/hvac-air-quality-analysis.wiki.git

# Create initial pages
cd hvac-air-quality-analysis.wiki
touch Home.md Hardware-Setup.md Data-Collection.md Analysis-Techniques.md

# Edit with your favorite editor
code .

# Commit and push
git add .
git commit -m "Initial wiki structure"
git push
```

## Automation Ideas:

1. **Auto-update Home page** with current filter stats via GitHub Actions
2. **Generate weekly reports** and append to performance tracking page
3. **Create alerts** when documentation needs updating (e.g., after 30 days of new data)

This structure separates operational knowledge (wiki) from code (repository), making both more maintainable and accessible.