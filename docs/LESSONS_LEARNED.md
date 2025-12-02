# Lessons Learned

## July 27, 2025: GitHub Wiki Management

**Problem**: Tried to manage wiki pages from main repository, leading to confusion.

**Discovery**: GitHub Wiki is a completely separate Git repository.
- Main repo: `https://github.com/username/project.git`
- Wiki repo: `https://github.com/username/project.wiki.git`

**Solution**: Clone wiki separately and manage independently.

## July 27, 2025: Plotly Export Issues

**Problem**: Datetime x-axis showing as scientific notation (1.745×10¹⁸) in exported PNGs.

**Discovery**: Kaleido has issues with datetime axes.

**Solution**: Convert datetime to string format before plotting:
```python
x_dates = df.index.strftime('%b %d')
fig.add_trace(go.Scatter(x=x_dates, y=df['value']))
```

## July 27, 2025: Visualization Tools Research

**Problem**: Building custom visualization pipeline when solutions already existed.

**Discovery**: Found excellent existing tools in research:
- **Quarto**: Modern "write once, deploy everywhere"
- **Playwright > Kaleido**: More reliable for Plotly exports
- **nb2hugo**: Direct Jupyter to Hugo integration

**Lesson**: Always check if someone has already solved your problem.

## Aug 8, 2025: Data Collection Outage

**Problem**: Data collection stopped unexpectedly.

**Discovery**: Firmware update removed cron job configuration.

**Solution**: Migrated to systemd user services with linger for true persistence.

## Aug 29, 2025: Filter Efficiency Confusion

**Problem**: 71% efficiency with brand new filter seemed wrong.

**Discovery**: Low outdoor PM2.5 (< 5 μg/m³) makes efficiency % unreliable.

**Solution**: Focus on absolute indoor PM2.5 values when outdoor air is clean.

## Aug 30, 2025: Multi-Sensor Deployment

**Problem**: .local domains don't resolve on some network configurations.

**Discovery**: mDNS support varies by network setup.

**Solution**: Created IP discovery script to update sensors.json with current IPs.

## Aug 30, 2025: Release Process Failure

**Problem**: Released v0.3.0 with 49 linting errors.

**Discovery**: Skipped pre-release quality checks.

**Solution**: Created RELEASE_CHECKLIST.md with mandatory pre-release steps:
1. Run tests first
2. Fix linting issues
3. Format code
4. Then proceed with release

## Package Management Confusion

**Problem**: Suggesting pip install commands when project uses uv.

**Discovery**: This project exclusively uses uv package manager.

**Solution**: Added clear warnings in CLAUDE.md about uv vs pip.

## Not a Python Package

**Problem**: GitHub Actions trying to build Python package.

**Discovery**: This is a collection of scripts, not a package.

**Solution**: Set `package = false` in pyproject.toml, create archives instead.