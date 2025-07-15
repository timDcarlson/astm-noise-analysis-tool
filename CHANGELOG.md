# Changelog

All notable changes to the ASTM Noise Analysis Tool will be documented in this file.

## [3.1.0] - 2025-07-15

### Added
- Individual windows for each high noise interval plot (600x700 geometry)
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
- Resolved "cannot access local variable 'glob'" scope error
- Fixed NumPy array boolean context ambiguity issues
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
