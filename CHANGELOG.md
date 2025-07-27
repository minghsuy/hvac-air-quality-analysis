# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-07-27

### Added
- Secure Google Sheets API integration for reading data privately
- Comprehensive test suite with 17 tests covering all API integrations
- GitHub Actions workflows for automated testing and releases
- Pre-commit hooks for code quality
- Release documentation and changelog management
- Test scripts for verifying Airthings PM2.5 data collection
- Setup guide and verification scripts for Google Cloud authentication
- Support for reading both public (CSV export) and private (API) Google Sheets data

### Changed
- Updated pyproject.toml with Google API dependencies
- Reorganized project structure with tests/ and scripts/ directories
- Configured project as non-packaged for Unifi Gateway compatibility

### Fixed
- Linting and formatting issues across all Python files
- GitHub Actions workflow configuration

### Security
- Added google-credentials.json to .gitignore for credential protection
- Implemented secure authentication for Google Sheets access

## [0.1.0] - 2025-07-27

### Added
- Initial release with core air quality monitoring functionality
- Airthings API integration for indoor air quality data
- AirGradient local API integration for outdoor air quality data
- Filter efficiency calculation and monitoring
- Google Forms integration for data logging
- Automated data collection script for Unifi Gateway
- Historical data analysis tools
- Jupyter notebook for interactive analysis
- Wiki documentation for project setup and results

### Features
- Real-time PM2.5 monitoring (indoor vs outdoor)
- Filter efficiency tracking with alerts
- Cost analysis for filter replacements
- Health correlation tracking capabilities
- 5-minute automated data collection via cron

[Unreleased]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/minghsuy/hvac-air-quality-analysis/releases/tag/v0.1.0