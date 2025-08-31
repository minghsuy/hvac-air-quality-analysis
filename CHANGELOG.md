# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive data dictionary (DATA_DICTIONARY.md) defining all fields and units
- Google Sheets schema migration tools for converting 14-column to 18-column format
- Migration guide (SHEETS_MIGRATION_GUIDE.md) with step-by-step instructions
- Data validation script to ensure compliance with data dictionary
- Updated Google Apps Script for new 18-column schema with alerts
- Test suite for Airthings API and Google Sheets integration

### Changed
- Migrated 3,985 rows from old Google Forms schema to new Sheets API schema
- Updated collector to write to specific sheet tab (Cleaned_Data_20250831)
- Switched to using compensated values from AirGradient (pm02Compensated, atmpCompensated)
- Standardized data types: numeric values with empty strings for missing data
- Store radon in native API units (Bq/m³) instead of display units (pCi/L)

### Fixed
- Airthings API response parsing for new "results" structure (was "sensors")
- AirGradient field names to use correct camelCase (tvocIndex, noxIndex)
- Filter efficiency calculation using compensated PM2.5 values
- Data type consistency issues between string and numeric values
- Unit conversion confusion for radon measurements

### Security
- Removed hardcoded MAC addresses and serial numbers from test files
- Fixed all bare except statements to specify exception types
- Added proper environment variable usage for sensor identifiers

## [0.3.0] - 2025-08-30

### Added
- Multi-sensor support for tracking multiple rooms independently
- Google Sheets API direct writing (replacing Forms for better scalability)
- Second bedroom monitoring with AirGradient indoor sensor
- Dynamic IP resolution for AirGradient sensors on Ubiquiti
- Wrapper script for .local domain issues on Ubiquiti Gateway
- Comprehensive data analysis scripts for filter change impact
- Google Apps Script for automated monitoring and alerts
- Room-specific efficiency calculations
- Sensor discovery and configuration system (sensors.json)

### Changed
- Switched from Google Forms to Sheets API for multi-sensor data structure
- Data now includes room identification for each sensor reading
- Updated collection to handle both Airthings and AirGradient indoor sensors
- Improved error handling for network connectivity issues
- Enhanced documentation with multi-sensor setup instructions

### Fixed
- Data collection outage caused by Ubiquiti firmware update removing cron job
- Ubiquiti Gateway mDNS resolution issues with .local domains
- Timestamp handling for proper timezone support
- Filter efficiency calculation accuracy at low PM2.5 levels

### Discovered
- Ubiquiti firmware updates can wipe custom cron jobs and scripts
- Need monitoring to detect when collection stops (implemented in Apps Script)
- Low outdoor PM2.5 (<5 μg/m³) makes efficiency percentage unreliable
- Ubiquiti Gateway requires special handling for Python dependencies

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

[Unreleased]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/minghsuy/hvac-air-quality-analysis/releases/tag/v0.1.0