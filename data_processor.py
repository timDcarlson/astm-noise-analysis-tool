"""
ASTM Noise Analysis - Data Processing Module

This module handles the core data loading, processing, and noise calculation functionality.
Separated from GUI components for better maintainability and testability.
"""

import numpy as np
import os
import glob
import re
import math
import csv
from convexHull import calculate_max_noise
from config import DEFAULT_SUBSET_SIZE, DEFAULT_MAX_INTERVALS


class NoiseDataProcessor:
    """Handles loading and processing of noise data files"""
    
    def __init__(self, output_directory=None):
        self.output_directory = output_directory
        self.file_names = []
        self.all_main_noise_values = []
        self.all_ref_noise_values = []
        self.main_noise_intervals = []
        self.ref_noise_intervals = []
        self.raw_t_main, self.raw_i_main = [], []
        self.raw_t_ref, self.raw_i_ref = [], []
        
    def extract_timestamp(self, filename):
        """Extract timestamp from filename for chronological sorting"""
        basename = os.path.basename(filename)
        # Try specific timestamp pattern first
        match = re.match(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', basename)
        if match:
            return match.group(1)
        # Try other timestamp patterns
        match = re.search(r'(\d{4}-\d{2}-\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2})', basename)
        if match:
            return match.group(1)
        # Fall back to filename
        return basename
    
    def find_chronological_files(self, first_filepath):
        """Find all data files and sort them chronologically"""
        output_directory = os.path.dirname(first_filepath)
        selected_filename = os.path.basename(first_filepath)
        selected_timestamp = self.extract_timestamp(selected_filename)
        
        # Try multiple patterns to find data files
        patterns = [
            os.path.join(output_directory, "*_*_DataCollection.txt"),  # Original pattern
            os.path.join(output_directory, "*.txt")                   # All .txt files
        ]
        
        all_available_files = []
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                all_available_files = files
                break
        
        # Sort all files by timestamp
        all_available_files.sort(key=self.extract_timestamp)
        
        # Start with the selected file, then add files that come after it chronologically
        files_to_process = [first_filepath]  # Always start with the selected file
        
        # Find files that come after the selected file chronologically
        for filepath in all_available_files:
            if filepath != first_filepath:  # Don't add the selected file again
                file_timestamp = self.extract_timestamp(os.path.basename(filepath))
                # Add files that are chronologically after the selected file
                if file_timestamp > selected_timestamp:
                    files_to_process.append(filepath)
        
        return files_to_process, selected_timestamp
    
    def calculate_subset_size(self, data):
        """Calculate appropriate subset size for 30-second intervals"""
        num_rows = len(data)
        if num_rows < 2:
            return 100
        else:
            delta_val = abs(data[1, 0] - data[0, 0])
            return max(3, math.floor(30 / (delta_val if delta_val > 1e-9 else 0.15)))
    
    def process_subsets(self, points, channel_name, file_index, subset_size, time_offset_adjustment):
        """Process data subsets and calculate noise values"""
        noise_values = []
        intervals = []
        
        # Pre-calculate values to avoid repeated computation
        points_len = len(points)
        
        # Use numpy array slicing for better performance
        for i in range(0, points_len, subset_size):
            # only process full‐length subsets, skip any remainder shorter than subset_size
            if i + subset_size > points_len:
                break
            
            subset = points[i:i + subset_size]
            # Round only once and in-place
            subset = np.round(subset, decimals=2)
            
            if len(subset) > 2:
                noise_val = calculate_max_noise(subset)
                noise_values.append(noise_val)
                
                # Record interval info: (start_time, end_time, noise_value, file_index, channel, filename)
                start_time = subset[0, 0] + time_offset_adjustment
                end_time = subset[-1, 0] + time_offset_adjustment
                intervals.append((start_time, end_time, noise_val, file_index, channel_name, self.file_names[file_index]))
        
        return noise_values, intervals
    
    def process_single_file(self, filepath, file_index, time_offset):
        """Process a single data file and extract noise information"""
        filename = os.path.basename(filepath)
        if file_index >= len(self.file_names):
            self.file_names.append(filename)
        
        print(f"Processing file {file_index + 1}: {filename}")
        
        try:
            data = np.loadtxt(filepath, delimiter='\t', skiprows=2)

            # 1) scatter‐plot data uses offset times - optimized for memory
            times = data[:, 0]
            offset_times = times + time_offset
            
            # Use extend with numpy arrays converted to lists only when necessary
            self.raw_t_main.extend(offset_times)
            self.raw_i_main.extend(data[:, 2])
            self.raw_t_ref.extend(offset_times) 
            self.raw_i_ref.extend(data[:, 4])

            # update time_offset for next file
            new_time_offset = offset_times[-1]

            # 2) noise calculation uses original times - optimized column stacking
            pointsMain = np.column_stack((times, data[:, 2]))
            pointsRef = np.column_stack((times, data[:, 4]))
            
            subset_size = self.calculate_subset_size(data)
            time_offset_adjustment = new_time_offset - (offset_times[-1] - times[-1])
            
            main_noise_values, main_intervals = self.process_subsets(
                pointsMain, 'Main', file_index, subset_size, time_offset_adjustment)
            ref_noise_values, ref_intervals = self.process_subsets(
                pointsRef, 'Reference', file_index, subset_size, time_offset_adjustment)

            self.all_main_noise_values.extend(main_noise_values)
            self.all_ref_noise_values.extend(ref_noise_values)
            self.main_noise_intervals.extend(main_intervals)
            self.ref_noise_intervals.extend(ref_intervals)
            
            print(f"  Main: {len(main_noise_values)} intervals, Reference: {len(ref_noise_values)} intervals")
            print(f"  Total collected - Main: {len(self.all_main_noise_values)}, Reference: {len(self.all_ref_noise_values)}")
            
            return new_time_offset, True
            
        except FileNotFoundError:
            print(f"  Error: File not found - {filename}")
            return time_offset, False
        except ValueError:
            print(f"  Error: Invalid data format - {filename}")
            return time_offset, False
        except IndexError:
            print(f"  Error: Data structure issue - {filename}")
            return time_offset, False
        except Exception as e:
            print(f"  Error processing {filename}: {e}")
            return time_offset, False
    
    def process_files(self, files_to_process, max_intervals=DEFAULT_MAX_INTERVALS):
        """Process multiple files until target intervals are reached"""
        time_offset = 0.0
        
        for file_index, filepath in enumerate(files_to_process):
            # Check if we have enough data from both channels
            if len(self.all_main_noise_values) >= max_intervals and len(self.all_ref_noise_values) >= max_intervals:
                print(f"Target of {max_intervals} intervals reached for both channels, stopping at file {file_index + 1}")
                break  # Exit if we have enough data from both channels
                
            time_offset, success = self.process_single_file(filepath, file_index, time_offset)
        
        # Print final summary
        print(f"\nData collection complete:")
        print(f"Main Channel: {len(self.all_main_noise_values)} intervals collected")
        print(f"Reference Channel: {len(self.all_ref_noise_values)} intervals collected")
        print(f"Files processed: {len([f for f in self.file_names if f])}")
    
    def get_statistics(self, max_intervals=DEFAULT_MAX_INTERVALS):
        """Calculate noise statistics from collected data"""
        # Truncate the lists if they are longer than max_intervals
        main_noise_truncated = self.all_main_noise_values[:max_intervals]
        ref_noise_truncated = self.all_ref_noise_values[:max_intervals]

        main_mean = np.mean(main_noise_truncated) if main_noise_truncated else np.nan
        main_max = np.max(main_noise_truncated) if main_noise_truncated else np.nan
        ref_mean = np.mean(ref_noise_truncated) if ref_noise_truncated else np.nan
        ref_max = np.max(ref_noise_truncated) if ref_noise_truncated else np.nan
        
        return {
            'main_mean': main_mean,
            'main_max': main_max,
            'ref_mean': ref_mean,
            'ref_max': ref_max,
            'main_count': len(main_noise_truncated),
            'ref_count': len(ref_noise_truncated)
        }
    
    def export_csv(self, output_directory, stats):
        """Export noise statistics to CSV file"""
        if not output_directory:
            return False, "No output directory specified"
            
        output_filename = os.path.join(output_directory, 'noise_analysis_results_python.csv')
        try:
            with open(output_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Channel', 'Mean', 'Max'])
                writer.writerow(['Main', stats['main_mean'], stats['main_max']])
                writer.writerow(['Reference', stats['ref_mean'], stats['ref_max']])
            return True, f"Results exported to {output_filename}"
        except Exception as e:
            return False, f"Error exporting to CSV: {e}"
    
    def get_high_noise_intervals(self, n_intervals=0, noise_threshold=None):
        """Analyze and return high noise intervals"""
        # Combine all intervals from both channels
        all_intervals = self.main_noise_intervals + self.ref_noise_intervals
        
        # Filter intervals to only include those between 0 and 3600 seconds
        filtered_time_intervals = []
        for interval in all_intervals:
            start_time, end_time, noise_val, file_idx, channel, filename = interval
            # Only include intervals that start within the first hour (0-3600 seconds)
            if 0 <= start_time <= 3600:
                filtered_time_intervals.append(interval)
        
        # Choose filtering method: threshold or top-N
        if noise_threshold is not None:
            # Filter by threshold - get all intervals above the threshold
            filtered_intervals = [interval for interval in filtered_time_intervals if interval[2] >= noise_threshold]
            # Sort by noise value (descending)
            sorted_intervals = sorted(filtered_intervals, key=lambda x: x[2], reverse=True)
            top_intervals = sorted_intervals
        else:
            # Original top-N method
            sorted_intervals = sorted(filtered_time_intervals, key=lambda x: x[2], reverse=True)
            top_intervals = sorted_intervals[:n_intervals]
        
        # Create a dictionary to group intervals by time and file for comprehensive display
        interval_groups = {}
        for start_time, end_time, noise_val, file_idx, channel, filename in top_intervals:
            # Use start_time and file_idx as key to group intervals from same time period
            key = (start_time, file_idx)
            if key not in interval_groups:
                interval_groups[key] = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'file_idx': file_idx,
                    'filename': filename,
                    'main_noise': None,
                    'ref_noise': None,
                    'max_noise': 0
                }
            
            # Store noise value for the appropriate channel
            if channel == 'Main':
                interval_groups[key]['main_noise'] = noise_val
            else:
                interval_groups[key]['ref_noise'] = noise_val
            
            # Track the maximum noise value for sorting
            interval_groups[key]['max_noise'] = max(interval_groups[key]['max_noise'], noise_val)
        
        # Sort grouped intervals by maximum noise value
        sorted_groups = sorted(interval_groups.values(), key=lambda x: x['max_noise'], reverse=True)
        
        return sorted_groups
