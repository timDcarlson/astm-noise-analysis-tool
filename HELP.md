# ASTM Noise Analysis Tool - User Guide

## Overview
The ASTM Noise Analysis Tool analyzes lamp stability data according to ASTM standards. It processes tab-delimited data files and generates noise statistics and visualization plots.

## Usage

### Basic Usage
```powershell
.\run_astm_noise.ps1
```
Runs the standard analysis showing only the ASTM noise interval plot (60-minute window).

### Advanced Usage
```powershell
.\run_astm_noise.ps1 -ShowCompleteDataset
```
Runs the analysis with both plots:
- ASTM Noise Interval plot (60-minute window)
- Complete Dataset plot (all files in folder, displayed in hours)

### Help
```powershell
.\run_astm_noise.ps1 -Help
```
Shows this help information.

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `-ShowCompleteDataset` | `-Show` | Display both ASTM interval and complete dataset plots |
| `-Help` | `-h` | Show this help information |

### Threshold-Based Analysis
```powershell
.\run_astm_noise.ps1 -Intervals -NoiseThreshold 1200
```
Shows ALL intervals where noise exceeds 1200 (or any specified threshold).

**Features for both modes:**
- **Interval Tracking**: Records time periods with highest noise values
- **Visual Highlighting**: Adds red background highlighting to problematic intervals on plots
- **Detailed Report**: Shows a popup window with:
  - Noise value for each high interval
  - Time range (start-end in minutes)
  - Channel information (Main or Reference)
  - File index for traceability
- **30-Second Detail Plotting**: Button to view zoomed plots of each high-noise interval
- **Export Capabilities**: Save interval lists and detailed plots with descriptive filenames

This feature is particularly useful for:
- Quality control and identifying problematic measurement periods
- Troubleshooting equipment issues
- Setting acceptance criteria based on noise thresholds

## What the Tool Does

1. **File Selection**: Prompts you to select the first tab-delimited data file after warm-up period (`*.txt`)
2. **Automatic File Processing**: 
   - Automatically finds and processes subsequent data files in the same directory
   - Files are processed in chronological order based on timestamps in filenames
   - Continues until 120 noise intervals are collected for both channels
   - If fewer files are available, analyzes whatever data is present
3. **Data Processing**: 
   - Skips header rows (first 2 lines)
   - Analyzes data in 30-second subsets based on time intervals
   - Collects noise values for both main and reference channels
3. **Analysis**: Calculates mean and maximum noise values
4. **Output**: 
   - CSV file with results (`noise_analysis_results_python.csv`)
   - Interactive plots showing intensity vs time
   - PNG exports of plots with descriptive filenames

## Data File Requirements

- **Format**: Tab-delimited text files (`.txt`)
- **Naming**: Should follow pattern `*_*_DataCollection.txt` for complete dataset analysis
- **Structure**: 
  - First 2 rows: Headers (skipped)
  - Column 0: Time (seconds)
  - Column 2: Main channel intensity
  - Column 4: Reference channel intensity

## Plot Types

### 1. ASTM Noise Interval Plot
- **Time Scale**: Minutes
- **Duration**: Up to 60 minutes (ASTM standard)
- **Features**:
  - Blue dots: Main channel data
  - Orange dots: Reference channel data
  - Red dashed line: 60-minute ASTM limit
  - Statistics in legend

### 2. Complete Dataset Plot (Optional)
- **Time Scale**: Hours
- **Duration**: All available data files
- **Features**:
  - Green dashed line: Start of ASTM interval
  - Red dashed line: End of ASTM interval (60 minutes later)
  - Total duration in title

## Output Files

### CSV Results
- **Filename**: `noise_analysis_results_python.csv`
- **Location**: Same folder as input data
- **Contents**:
  ```
  Channel,Mean,Max
  Main,<mean_value>,<max_value>
  Reference,<mean_value>,<max_value>
  ```

### Plot Images
- **ASTM Plot**: `<folder_name> noise containing the time <timestamp>.png`
- **Complete Dataset**: `<folder_name> complete dataset <hours> hours.png`
- **Location**: Same folder as input data

## Workflow Example

1. **Setup** (first time only):
   ```powershell
   .\setup_env.ps1
   ```

2. **Run Analysis**:
   ```powershell
   .\run_astm_noise.ps1 -ShowCompleteDataset
   ```

3. **Select Files**: Choose your data files when prompted

4. **View Results**: 
   - Interactive plots open in separate windows
   - Click "Export" buttons to save PNG files
   - CSV results automatically saved

## Troubleshooting

### Python Not Found
- Install Python from https://www.python.org/downloads/
- Make sure "Add Python to PATH" is checked during installation
- Run `setup_env.ps1` again

### File Format Errors
- Ensure files are tab-delimited
- Check that files have at least 2 header rows
- Verify column structure (time in column 0, intensities in columns 2 and 4)

### Virtual Environment Issues
- Run `setup_env.ps1` to recreate the environment
- Check that the virtual environment exists in `Documents\Python Environments\astm-noise-analysis`

## Technical Details

- **Subset Size**: Automatically calculated based on time intervals (minimum 3, typically 30 seconds worth of data)
- **Noise Calculation**: Uses convex hull method to determine maximum noise
- **Data Collection**: Continues until 120 noise values are collected for each channel
- **Memory Efficient**: Processes files incrementally to handle large datasets

## Version Information
- **Created**: July 2025
- **Python Requirements**: numpy, matplotlib, scipy, tkinter
- **Operating System**: Windows (PowerShell required)
