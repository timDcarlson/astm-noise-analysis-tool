# Changelog

All notable changes to the ASTM Noise Analysis Tool will be documented in this file.

## [3.1.1] - 2025-07-18

### Added
- **Configurable Plot Limit**: Added option to limit the number of 30-second interval plots when showing high noise intervals
- **GUI Enhancement**: Max intervals configuration field in high noise intervals popup window (default: 8 plots)
- **Command Line Support**: New `--max-intervals-to-plot` parameter for PowerShell integration
- **PowerShell Enhancement**: Added `-MaxIntervalsToPlot` parameter to `run_astm_noise.ps1` launcher

### Changed
- **Improved User Experience**: "Max intervals to plot" setting moved from main GUI to high noise intervals window for better workflow
- **Better Plot Management**: System now prevents excessive plot window creation by limiting to user-specified number
- **Enhanced Documentation**: Updated help text and parameter descriptions for clarity

### Fixed
- **Workflow Optimization**: Plot limit option only appears when relevant (high noise intervals analysis)
- **Input Validation**: Added validation for max intervals parameter with user-friendly error messages

### Technical Details
- Modified `plot_detailed_intervals()` function to accept `max_intervals` parameter
- Updated `load_and_calculate_noise_multiple()` function signature and documentation
- Enhanced PowerShell script argument processing and help text
- Improved command-line argument parsing in main Python script

## [3.1.0] - 2025-07-15

### Added
- Individual windows for each high noise interval plot 
- 10-second padding around noise intervals for better visualization
- Comprehensive performance optimizations using NumPy arrays
- Export functionality for individual interval plots
- Convex hull visualization for noise intervals
- File selection feature for computing noise values on additional files
- Package structure with version information and configuration

### Changed
- High noise intervals now display in separate windows instead of subplots
- Optimized data processing with vectorized NumPy operations
- Improved memory efficiency for large dataset handling
- Enhanced GUI layout with better button visibility
- Upgraded export functionality with timestamped filenames

### Fixed
- Improved error handling for file processing
- Better handling of edge cases in data loading

### Performance
- Significantly reduced memory usage for large datasets
- Faster processing through vectorized operations
- Optimized convex hull calculations
- Reduced tool call overhead in data processing

## [2.1.0] - Previous Version

### Features
- Multi-file processing with chronological ordering
- GUI interface for configuration and analysis
- ASTM noise interval plotting
- Complete dataset visualization
- High noise interval identification
- CSV export functionality
- Statistical analysis (mean, max noise values)

### Core Functionality
- 30-second interval noise calculation
- Convex hull-based noise analysis
- Dual-channel processing (Main and Reference)
- Real-time progress feedback
