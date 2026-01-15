"""
ASTM Noise Analysis Tool

A Python-based tool for analyzing noise in deuterium lamp data according to ASTM standards.
Provides GUI interface for loading data files, calculating noise parameters, and visualizing results.

Version: 3.1.1
Author: Tim Carlson
"""

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
import math, csv, os, copy
import argparse
import glob
import re
import datetime

# new imports for embedding plots
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from convexHull import calculate_max_noise
from config import APP_VERSION, APP_NAME


def load_and_calculate_noise_multiple(show_complete_dataset=False, show_high_noise_intervals=False, n_intervals=0, noise_threshold=None, max_intervals_to_plot=8):
    """
    Prompts for tab-delimited files, skips the header, analyzes subsets,
    and continues until enough noise values are collected, then exports to CSV.
    
    Args:
        show_complete_dataset (bool): Whether to show the complete dataset plot (default: False)
        show_high_noise_intervals (bool): Whether to show plot of highest noise intervals (default: False)
        n_intervals (int): Number of highest noise intervals to track and plot (default: 0)
        noise_threshold (float): Threshold value - show all intervals above this noise level (default: None)
        max_intervals_to_plot (int): Maximum number of intervals to plot in detailed view (default: 8)
    """
    all_main_noise_values = []
    all_ref_noise_values = []
    # new lists for scatter data
    raw_t_main, raw_i_main = [], []
    raw_t_ref,  raw_i_ref  = [], []
    # new lists for tracking noise intervals
    main_noise_intervals = []  # (start_time, end_time, noise_value, file_index, filename)
    ref_noise_intervals = []
    time_offset = 0.0     # <— accumulates end‐of‐last‐segment time
    output_directory = None
    file_names = []  # Track filenames for each file index

    # Get the first file from user
    first_filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not first_filepath:
        return
    
    output_directory = os.path.dirname(first_filepath)
    
    # Find all matching data files in the same directory
    # Get the selected file's timestamp for comparison
    selected_filename = os.path.basename(first_filepath)
    
    def extract_timestamp(filename):
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
    
    selected_timestamp = extract_timestamp(selected_filename)
    
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
    all_available_files.sort(key=extract_timestamp)
    
    # Start with the selected file, then add files that come after it chronologically
    files_to_process = [first_filepath]  # Always start with the selected file
    
    # Find files that come after the selected file chronologically
    for filepath in all_available_files:
        if filepath != first_filepath:  # Don't add the selected file again
            file_timestamp = extract_timestamp(os.path.basename(filepath))
            # Add files that are chronologically after the selected file
            if file_timestamp > selected_timestamp:
                files_to_process.append(filepath)
    
    # Store first filepath for later use in exports
    first_processed_file = files_to_process[0]
    
    print(f"Starting with selected file: {os.path.basename(first_filepath)}")
    print(f"Selected file timestamp: {selected_timestamp}")
    print(f"Total files to process: {len(files_to_process)}")
    if len(files_to_process) > 1:
        print(f"Subsequent files: {[os.path.basename(f) for f in files_to_process[1:6]]}" + 
              (f" ... and {len(files_to_process) - 6} more" if len(files_to_process) > 6 else ""))
    else:
        print("No subsequent files found - will process only the selected file")
    
    # Process files automatically until we have enough data
    for file_index, filepath in enumerate(files_to_process):
            
        # Track filename for this file index
        filename = os.path.basename(filepath)
        if file_index >= len(file_names):
            file_names.append(filename)
        
        print(f"Processing file {file_index + 1}/{len(files_to_process)}: {filename}")

        try:
            data = np.loadtxt(filepath, delimiter='\t', skiprows=2)

            # Capture where this file starts in the concatenated timeline so plotting and interval timestamps agree.
            file_start_offset = time_offset

            # 1) scatter-plot data uses offset times - optimized for memory
            times = data[:, 0]
            offset_times = times + file_start_offset
            
            # Use extend with numpy arrays converted to lists only when necessary
            raw_t_main.extend(offset_times)
            raw_i_main.extend(data[:, 2])
            raw_t_ref.extend(offset_times) 
            raw_i_ref.extend(data[:, 4])

            # update time_offset for next file
            time_offset = offset_times[-1]

            # 2) noise calculation uses original times - optimized column stacking
            pointsMain = np.column_stack((times, data[:, 2]))
            pointsRef = np.column_stack((times, data[:, 4]))
            num_rows = len(data)

            if num_rows < 2:
                subset_size = 100
            else:
                delta_val = abs(data[1, 0] - data[0, 0])
                subset_size = max(3, math.floor(30 / (delta_val if delta_val > 1e-9 else 0.15)))

            def process_subsets(points, channel_name, file_start_offset_local):
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
                        start_time = subset[0, 0] + file_start_offset_local
                        end_time = subset[-1, 0] + file_start_offset_local
                        intervals.append((start_time, end_time, noise_val, file_index, channel_name, file_names[file_index]))
                
                return noise_values, intervals

            main_noise_values, main_intervals = process_subsets(pointsMain, 'Main', file_start_offset)
            ref_noise_values, ref_intervals = process_subsets(pointsRef, 'Reference', file_start_offset)

            all_main_noise_values.extend(main_noise_values)
            all_ref_noise_values.extend(ref_noise_values)
            main_noise_intervals.extend(main_intervals)
            ref_noise_intervals.extend(ref_intervals)
            
            print(f"  Main: {len(main_noise_values)} intervals, Reference: {len(ref_noise_values)} intervals")
            print(f"  Total collected - Main: {len(all_main_noise_values)}, Reference: {len(all_ref_noise_values)}")

            # Stop once we have at least 120 intervals per channel inside the analysis window (post warm-up)
            main_window_count = sum(1 for start_time, _, _, _, _, _ in main_noise_intervals if analysis_start_seconds <= start_time <= analysis_end_seconds)
            ref_window_count = sum(1 for start_time, _, _, _, _, _ in ref_noise_intervals if analysis_start_seconds <= start_time <= analysis_end_seconds)
            if main_window_count >= 120 and ref_window_count >= 120:
                print(f"Target of 120 intervals in analysis window reached for both channels, stopping at file {file_index + 1}")
                break
        
        except FileNotFoundError:
            print(f"  Error: File not found - {filename}")
            continue
        except ValueError:
            print(f"  Error: Invalid data format - {filename}")
            continue
        except IndexError:
            print(f"  Error: Data structure issue - {filename}")
            continue
        except Exception as e:
            print(f"  Error processing {filename}: {e}")
            continue
    
    # Print final summary
    print(f"\nData collection complete:")
    print(f"Main Channel: {len(all_main_noise_values)} intervals collected")
    print(f"Reference Channel: {len(all_ref_noise_values)} intervals collected")
    print(f"Files processed: {len([f for f in file_names if f])}")
    
    # Remove the old file index increment since we're using enumerate now
    # file_index += 1

    # Filter noise values to only include those after warm-up (30 min) across a 3600-second window
    analysis_start_seconds = 1800  # 30 minutes warm-up
    analysis_window_seconds = 3600 # 120 intervals * 30 seconds
    analysis_end_seconds = analysis_start_seconds + analysis_window_seconds

    main_noise_window = []
    ref_noise_window = []
    
    # Extract noise values only from intervals that start within the analysis window
    for start_time, end_time, noise_val, file_idx, channel, filename in main_noise_intervals:
        if analysis_start_seconds <= start_time <= analysis_end_seconds:
            main_noise_window.append(noise_val)
    
    for start_time, end_time, noise_val, file_idx, channel, filename in ref_noise_intervals:
        if analysis_start_seconds <= start_time <= analysis_end_seconds:
            ref_noise_window.append(noise_val)
    
    # Truncate to first 120 intervals from the analysis window
    main_noise_truncated = main_noise_window[:120]
    ref_noise_truncated = ref_noise_window[:120]
    
    print(f"\nNoise statistics calculated from {analysis_start_seconds/60:.1f}-{analysis_end_seconds/60:.1f} minutes (post warm-up):")
    print(f"Main Channel: {len(main_noise_truncated)} intervals")
    print(f"Reference Channel: {len(ref_noise_truncated)} intervals")

    main_mean = np.mean(main_noise_truncated) if main_noise_truncated else np.nan
    main_max = np.max(main_noise_truncated) if main_noise_truncated else np.nan
    ref_mean = np.mean(ref_noise_truncated) if ref_noise_truncated else np.nan
    ref_max = np.max(ref_noise_truncated) if ref_noise_truncated else np.nan

    # === High Noise Interval Analysis ===
    if show_high_noise_intervals and (n_intervals > 0 or noise_threshold is not None):
        # Combine all intervals from both channels
        all_intervals = main_noise_intervals + ref_noise_intervals
        
        # Filter intervals to only include those inside the analysis window (post warm-up)
        filtered_time_intervals = []
        for interval in all_intervals:
            start_time, end_time, noise_val, file_idx, channel, filename = interval
            if analysis_start_seconds <= start_time <= analysis_end_seconds:
                filtered_time_intervals.append(interval)
        
        # Choose filtering method: threshold or top-N
        if noise_threshold is not None:
            # Filter by threshold - get all intervals above the threshold
            filtered_intervals = [interval for interval in filtered_time_intervals if interval[2] >= noise_threshold]
            # Sort by noise value (descending)
            sorted_intervals = sorted(filtered_intervals, key=lambda x: x[2], reverse=True)
            top_intervals = sorted_intervals
            interval_mode = f"above {noise_threshold}"
        else:
            # Original top-N method
            sorted_intervals = sorted(filtered_time_intervals, key=lambda x: x[2], reverse=True)
            top_intervals = sorted_intervals[:n_intervals]
            interval_mode = f"top {n_intervals}"
        
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
        
        # Display high noise intervals with both channel values
        if noise_threshold is not None:
            interval_text = f"\nHigh Noise Intervals Above {noise_threshold} ({analysis_start_seconds/60:.1f}-{analysis_end_seconds/60:.1f} min window, {len(sorted_groups)} found):\n"
        else:
            interval_text = f"\nTop {len(sorted_groups)} High Noise Intervals ({analysis_start_seconds/60:.1f}-{analysis_end_seconds/60:.1f} min window):\n"
        interval_text += "=" * 70 + "\n"
        for i, group in enumerate(sorted_groups, 1):
            start_min = group['start_time'] / 60.0
            end_min = group['end_time'] / 60.0
            interval_text += f"{i:2d}. Time: {start_min:.1f} - {end_min:.1f} min ({group['filename']})\n"
            
            # Display both channel values
            if group['main_noise'] is not None:
                interval_text += f"    Main Channel: {group['main_noise']:.3f}\n"
            else:
                interval_text += f"    Main Channel: N/A\n"
                
            if group['ref_noise'] is not None:
                interval_text += f"    Reference Channel: {group['ref_noise']:.3f}\n"
            else:
                interval_text += f"    Reference Channel: N/A\n"
        
        # Show in a popup window
        interval_window = tk.Toplevel()
        if noise_threshold is not None:
            interval_window.title(f"High Noise Intervals (Above {noise_threshold})")
        else:
            interval_window.title("High Noise Intervals")
        interval_window.geometry("900x800")  # Made wider and taller for file selection and buttons
        
        # Create main frame to hold text area and buttons separately
        main_frame = tk.Frame(interval_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text frame for the text widget and scrollbar
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        text_widget = tk.Text(text_frame, font=("Courier", 10), wrap=tk.WORD)
        text_widget.insert(tk.END, interval_text)
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add file selection frame for computing noise values
        file_selection_frame = tk.Frame(main_frame)
        file_selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a label for the file selection section
        file_label = tk.Label(file_selection_frame, text="Compute Noise Values for Additional Files:", 
                             font=("Arial", 10, "bold"))
        file_label.pack(anchor=tk.W)
        
        # Create a scrollable frame for file checkboxes with fixed height
        file_scroll_frame = tk.Frame(file_selection_frame, height=120)  # Fixed height
        file_scroll_frame.pack(fill=tk.X, pady=(5, 0))
        file_scroll_frame.pack_propagate(False)  # Maintain fixed height
        
        # Create canvas and scrollbar for the checkbox area
        canvas = tk.Canvas(file_scroll_frame, height=120)
        scrollbar_files = tk.Scrollbar(file_scroll_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_files.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_files.pack(side="right", fill="y")
        
        # Add mouse wheel scrolling support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas and scrollable frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Also bind to the checkboxes for better UX
        def bind_mousewheel_to_children(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_to_children(child)
        
        # Get all available files in the directory
        
        def extract_timestamp_local(filename):
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
        
        all_files_pattern = os.path.join(output_directory, "*_*_DataCollection.txt")
        all_available_files = glob.glob(all_files_pattern)
        all_available_files.sort(key=extract_timestamp_local)
        
        # Create checkboxes for each file in the scrollable frame
        file_checkboxes = {}  # Dictionary to store checkbox variables
        
        # First, create the individual file checkboxes
        for i, filepath in enumerate(all_available_files):
            filename = os.path.basename(filepath)
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(scrollable_frame, text=filename, variable=var, 
                                     font=("Arial", 9), anchor="w")
            checkbox.pack(fill="x", padx=5, pady=1)
            checkbox.bind("<MouseWheel>", _on_mousewheel)  # Add mouse wheel support to each checkbox
            file_checkboxes[filepath] = var

        # Add "Select All Files" checkbox after individual checkboxes are created
        select_all_frame = tk.Frame(file_selection_frame)
        select_all_frame.pack(fill=tk.X, pady=(5, 0))
        
        select_all_var = tk.BooleanVar()
        
        def update_select_all_state():
            """Update Select All checkbox based on individual file selections"""
            total_files = len(file_checkboxes)
            selected_files = sum(1 for var in file_checkboxes.values() if var.get())
            
            if selected_files == 0:
                select_all_var.set(False)
            elif selected_files == total_files:
                select_all_var.set(True)
            # For partial selection, we could add an indeterminate state, but keeping it simple
        
        def toggle_all_files():
            """Toggle all file checkboxes based on Select All state"""
            select_all_state = select_all_var.get()
            for var in file_checkboxes.values():
                var.set(select_all_state)
        
        select_all_checkbox = tk.Checkbutton(select_all_frame, 
                                           text="☑ Select All Files (Compute noise for entire dataset)", 
                                           variable=select_all_var,
                                           command=toggle_all_files,
                                           font=("Arial", 10, "bold"),
                                           fg="blue")
        select_all_checkbox.pack(anchor=tk.W, padx=5)
        
        # Add helpful information label
        info_label = tk.Label(select_all_frame, 
                             text="Tip: Use 'Select All Files' to analyze noise values for the complete dataset",
                             font=("Arial", 9, "italic"),
                             fg="gray")
        info_label.pack(anchor=tk.W, padx=20)
        
        # Now add the trace callbacks to individual checkboxes to update select all state
        for var in file_checkboxes.values():
            var.trace_add('write', lambda *args: update_select_all_state())
        
        # Add button to plot 30-second intervals
        def plot_30_second_intervals():
            # Get the max intervals value from the popup window's entry field
            try:
                max_intervals = int(max_intervals_var.get())
                if max_intervals <= 0:
                    raise ValueError("Max intervals must be positive")
            except ValueError:
                messagebox.showerror("Invalid Input", 
                                   "Please enter a valid positive number for max intervals to plot.")
                return
            
            # Use the max_intervals value when high noise intervals are shown
            plot_detailed_intervals(sorted_groups, raw_t_main, raw_i_main, raw_t_ref, raw_i_ref, output_directory, max_intervals)
        
        # Function to compute noise values for selected files
        def compute_selected_file_noise():
            selected_files = [filepath for filepath, var in file_checkboxes.items() if var.get()]
            if not selected_files:
                messagebox.showwarning("No Files Selected", "Please select at least one file to compute noise values.")
                return
            
            # Create a new window to show the results
            results_window = tk.Toplevel(interval_window)
            results_window.title("Selected Files Noise Analysis")
            results_window.geometry("600x500")
            
            # Create text widget for results
            results_frame = tk.Frame(results_window)
            results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            results_text = tk.Text(results_frame, font=("Courier", 10), wrap=tk.WORD)
            results_scrollbar = tk.Scrollbar(results_frame, command=results_text.yview)
            results_text.config(yscrollcommand=results_scrollbar.set)
            
            results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Compute noise for each selected file
            results_output = "Noise Analysis Results for Selected Files:\n"
            results_output += "=" * 60 + "\n\n"
            
            for filepath in selected_files:
                filename = os.path.basename(filepath)
                results_output += f"File: {filename}\n"
                results_output += "-" * 50 + "\n"
                
                try:
                    # Load and process the file
                    data = np.loadtxt(filepath, delimiter='\t', skiprows=2)
                    times = data[:,0]
                    
                    # Process main and reference channels
                    pointsMain = np.column_stack((times, data[:,2]))
                    pointsRef = np.column_stack((times, data[:,4]))
                    
                    # Calculate subset size (same logic as main analysis for 30-second intervals)
                    num_rows = len(data)
                    if num_rows < 2:
                        subset_size = 100
                    else:
                        delta_val = abs(data[1, 0] - data[0, 0])
                        subset_size = max(3, math.floor(30 / (delta_val if delta_val > 1e-9 else 0.15)))
                    
                    # Process subsets for noise calculation
                    def calculate_file_noise(points, channel_name):
                        noise_values = []
                        for i in range(0, len(points), subset_size):
                            # only process full‐length subsets, skip any remainder shorter than subset_size
                            if i + subset_size > len(points):
                                break
                            subset = np.round(points[i:i + subset_size], decimals=2)
                            if len(subset) > 2:
                                noise_val = calculate_max_noise(subset)
                                noise_values.append(noise_val)
                        return noise_values
                    
                    main_noise_values = calculate_file_noise(pointsMain, 'Main')
                    ref_noise_values = calculate_file_noise(pointsRef, 'Reference')
                    
                    # Calculate statistics
                    if main_noise_values:
                        main_mean = np.mean(main_noise_values)
                        main_max = np.max(main_noise_values)
                    else:
                        main_mean = main_max = np.nan
                    
                    if ref_noise_values:
                        ref_mean = np.mean(ref_noise_values)
                        ref_max = np.max(ref_noise_values)
                    else:
                        ref_mean = ref_max = np.nan
                    
                    # Add results to output
                    results_output += f"Main Channel ({len(main_noise_values)} intervals):\n"
                    results_output += f"  Mean:   {main_mean:.3f}\n"
                    results_output += f"  Max:    {main_max:.3f}\n\n"
                    
                    results_output += f"Reference Channel ({len(ref_noise_values)} intervals):\n"
                    results_output += f"  Mean:   {ref_mean:.3f}\n"
                    results_output += f"  Max:    {ref_max:.3f}\n\n"
                    
                except Exception as e:
                    results_output += f"Error processing file: {e}\n\n"
                
                results_output += "\n"
            
            # Display results
            results_text.insert(tk.END, results_output)
            results_text.config(state=tk.DISABLED)
            
            # Add export button for results
            def export_file_noise_results():
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"selected_files_noise_analysis_{timestamp}.txt"
                filepath = os.path.join(output_directory, filename)
                
                try:
                    with open(filepath, 'w') as f:
                        f.write(results_output)
                    
                    success_label = tk.Label(results_window, text=f"Exported: {filename}", 
                                           fg="green", font=("Arial", 9, "bold"))
                    success_label.pack(pady=5)
                    results_window.after(3000, success_label.destroy)
                    
                except Exception as e:
                    messagebox.showerror("Export Error", f"Error exporting results: {e}")
            
            export_file_results_button = tk.Button(results_window, text="Export Results", 
                                                  command=export_file_noise_results, bg="lightgreen")
            export_file_results_button.pack(pady=5)
        
        # Add configuration frame for plot options
        config_frame = tk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        config_label = tk.Label(config_frame, text="Plot Configuration:", 
                               font=("Arial", 10, "bold"))
        config_label.pack(anchor=tk.W)
        
        # Max intervals to plot
        intervals_config_frame = tk.Frame(config_frame)
        intervals_config_frame.pack(fill=tk.X, pady=2)
        
        intervals_label = tk.Label(intervals_config_frame, text="Max intervals to plot:", 
                                  font=("Arial", 10))
        intervals_label.pack(side=tk.LEFT)
        
        max_intervals_var = tk.StringVar(value=str(max_intervals_to_plot))
        max_intervals_entry = tk.Entry(intervals_config_frame, textvariable=max_intervals_var, width=8)
        max_intervals_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Create button frame that spans the full width
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        plot_button = tk.Button(button_frame, text="Plot 30-Second Intervals", 
                               command=plot_30_second_intervals, bg="lightblue", 
                               font=("Arial", 10, "bold"), pady=8)
        plot_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add button to compute noise for selected files
        compute_button = tk.Button(button_frame, text="Compute Noise for Selected Files", 
                                 command=compute_selected_file_noise, bg="lightyellow",
                                 font=("Arial", 10, "bold"), pady=8)
        compute_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add export button for interval list
        def export_interval_list():
            if output_directory:
                # Create filename with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                if noise_threshold is not None:
                    filename = f"high_noise_intervals_above_{noise_threshold}_{timestamp}.txt"
                else:
                    filename = f"high_noise_intervals_top_{len(sorted_groups)}_{timestamp}.txt"
                filepath = os.path.join(output_directory, filename)
                
                try:
                    with open(filepath, 'w') as f:
                        f.write(interval_text)
                    
                    # Show success message
                    success_label = tk.Label(button_frame, text=f"Exported: {filename}", 
                                           fg="green", font=("Arial", 9, "bold"))
                    success_label.pack(side=tk.LEFT, padx=(20, 0))
                    # Remove message after 3 seconds
                    interval_window.after(3000, success_label.destroy)
                    
                except Exception as e:
                    messagebox.showerror("Export Error", f"Error exporting interval list: {e}")
        
        export_button = tk.Button(button_frame, text="Export Interval List", 
                                 command=export_interval_list, bg="lightgreen",
                                 font=("Arial", 10, "bold"), pady=8)
        export_button.pack(side=tk.LEFT)
    else:
        # Set empty sorted_groups for later use in plotting
        sorted_groups = []

    # Remove the unused text output variables
    # main_output = "Main Channel Noise Values:\n"
    # if main_noise_truncated:
    #     main_output += f"  Noise Mean: {main_mean:.3f}\n"
    #     main_output += f"  Noise Max: {main_max:.3f}\n"
    # else:
    #     main_output += "  No main channel noise values collected.\n"

    # ref_output = "\nReference Channel Noise Values:\n"
    # if ref_noise_truncated:
    #     ref_output += f"  Noise Mean: {ref_mean:.3f}\n"
    #     ref_output += f"  Noise Max: {ref_max:.3f}\n"
    # else:
    #     ref_output += "  No reference channel noise values collected.\n"

    # result_label.config(text="", font=("Arial", 12), justify="left", padx=20, pady=10)

    # Export results to CSV in the selected data folder
    if output_directory:
        output_filename = os.path.join(output_directory, 'noise_analysis_results_python.csv')
        try:
            with open(output_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Channel', 'Mean (0-3600s)', 'Max (0-3600s)'])
                writer.writerow(['Main', main_mean, main_max])
                writer.writerow(['Reference', ref_mean, ref_max])
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting to CSV: {e}")
    else:
        messagebox.showinfo("No Export", "No data file was successfully selected, so results were not exported.")

    # === Function to plot detailed 30-second intervals ===
    def plot_detailed_intervals(interval_groups, t_main, i_main, t_ref, i_ref, output_dir, max_intervals=None):
        """Plot detailed view of high noise 30-second intervals - each in separate window
        
        Args:
            interval_groups: List of interval dictionaries to plot
            t_main, i_main: Time and intensity data for main channel
            t_ref, i_ref: Time and intensity data for reference channel
            output_dir: Directory for saving plots
            max_intervals: Maximum number of intervals to plot (default: None for all)
        """
        n_intervals = len(interval_groups)
        if n_intervals == 0:
            return
        
        # Limit the number of intervals if max_intervals is specified
        if max_intervals is not None and max_intervals > 0:
            intervals_to_plot = interval_groups[:max_intervals]
            if n_intervals > max_intervals:
                print(f"Limiting plot to highest {max_intervals} of {n_intervals} intervals")
        else:
            intervals_to_plot = interval_groups
        
        # Create separate window for each interval
        for i, group in enumerate(intervals_to_plot):
            # Create individual window for this interval
            detail_window = tk.Toplevel()
            detail_window.title(f"Interval {i+1}: {group['start_time']/60.0:.1f}-{group['end_time']/60.0:.1f} min")
            detail_window.geometry("600x700")
            
            # Create individual figure for this interval
            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            
            # Convert to numpy arrays and minutes for better performance
            t_main_array = np.array(t_main) if not isinstance(t_main, np.ndarray) else t_main
            i_main_array = np.array(i_main) if not isinstance(i_main, np.ndarray) else i_main
            t_ref_array = np.array(t_ref) if not isinstance(t_ref, np.ndarray) else t_ref
            i_ref_array = np.array(i_ref) if not isinstance(i_ref, np.ndarray) else i_ref
            
            t_main_min = t_main_array / 60.0
            t_ref_min = t_ref_array / 60.0
            
            # Find data points within the interval
            start_min = group['start_time'] / 60.0
            end_min = group['end_time'] / 60.0
            
            # Plot all data in light colors
            ax.scatter(t_main_min, i_main_array, s=4, c='blue', alpha=0.5, label='Main (all)')
            
            # Create second y-axis for reference data
            ax2 = ax.twinx()
            ax2.scatter(t_ref_min, i_ref_array, s=4, c='orange', alpha=0.5, label='Ref (all)')
            
            # Use numpy boolean indexing for better performance
            interval_mask_main = (t_main_min >= start_min) & (t_main_min <= end_min)
            interval_mask_ref = (t_ref_min >= start_min) & (t_ref_min <= end_min)
            
            if np.any(interval_mask_main):
                interval_t_main = t_main_min[interval_mask_main]
                interval_i_main = i_main_array[interval_mask_main]
                ax.scatter(interval_t_main, interval_i_main, s=8, c='blue', label='Main (interval)')
                
                # Add convex hull for main channel interval data
                if len(interval_i_main) > 2:
                    # Create points array for convex hull calculation
                    main_points = np.column_stack((interval_t_main, interval_i_main))
                    try:
                        from scipy.spatial import ConvexHull
                        hull = ConvexHull(main_points)
                        # Plot convex hull boundary
                        for simplex in hull.simplices:
                            ax.plot(main_points[simplex, 0], main_points[simplex, 1], 'b-', alpha=0.7, linewidth=1.5)
                    except ImportError:
                        # Fallback if scipy not available - just connect min/max points
                        min_idx = np.argmin(interval_i_main)
                        max_idx = np.argmax(interval_i_main)
                        ax.plot([interval_t_main[min_idx], interval_t_main[max_idx]], 
                               [interval_i_main[min_idx], interval_i_main[max_idx]], 'b--', alpha=0.7, linewidth=1.5)
            
            if np.any(interval_mask_ref):
                interval_t_ref = t_ref_min[interval_mask_ref]
                interval_i_ref = i_ref_array[interval_mask_ref]
                ax2.scatter(interval_t_ref, interval_i_ref, s=8, c='orange', label='Ref (interval)')
                
                # Add convex hull for reference channel interval data
                if len(interval_i_ref) > 2:
                    # Create points array for convex hull calculation
                    ref_points = np.column_stack((interval_t_ref, interval_i_ref))
                    try:
                        from scipy.spatial import ConvexHull
                        hull = ConvexHull(ref_points)
                        # Plot convex hull boundary
                        for simplex in hull.simplices:
                            ax2.plot(ref_points[simplex, 0], ref_points[simplex, 1], 'orange', alpha=0.7, linewidth=1.5, linestyle='-')
                    except ImportError:
                        # Fallback if scipy not available - just connect min/max points
                        min_idx = np.argmin(interval_i_ref)
                        max_idx = np.argmax(interval_i_ref)
                        ax2.plot([interval_t_ref[min_idx], interval_t_ref[max_idx]], 
                               [interval_i_ref[min_idx], interval_i_ref[max_idx]], 'orange', alpha=0.7, linewidth=1.5, linestyle='--')
            
            # Set axis labels and title
            ax.set_xlabel("Time (minutes)")
            ax.set_ylabel("Main Intensity", color='blue')
            ax2.set_ylabel("Reference Intensity", color='orange')
            ax.tick_params(axis='y', colors='blue')
            ax2.tick_params(axis='y', colors='orange')
            
            # Set title with noise values
            main_noise_str = f"{group['main_noise']:.3f}" if group['main_noise'] is not None else "N/A"
            ref_noise_str = f"{group['ref_noise']:.3f}" if group['ref_noise'] is not None else "N/A"
            ax.set_title(f"Interval {i+1}: {start_min:.1f}-{end_min:.1f} min\nMain: {main_noise_str}, Ref: {ref_noise_str}", 
                        fontsize=10)
            
            # Set reasonable zoom around the interval
            time_buffer = 10.0 / 60.0  # 10 seconds buffer on each side (converted to minutes)
            ax.set_xlim(max(0, start_min - time_buffer), end_min + time_buffer)
            
            # Adjust Y-axis ranges for better visualization
            if np.any(interval_mask_main):
                # Main channel: extend range down by 80% and up by 20%
                main_interval_values = i_main_array[interval_mask_main]
                if len(main_interval_values) > 0:
                    main_min_val = np.min(main_interval_values)
                    main_max_val = np.max(main_interval_values)
                    main_range = main_max_val - main_min_val
                    ax.set_ylim(main_min_val - 0.8 * main_range, main_max_val + 0.2 * main_range)
            
            if np.any(interval_mask_ref):
                # Reference channel: extend range up by 80% and down by 20%
                ref_interval_values = i_ref_array[interval_mask_ref]
                if len(ref_interval_values) > 0:
                    ref_min_val = np.min(ref_interval_values)
                    ref_max_val = np.max(ref_interval_values)
                    ref_range = ref_max_val - ref_min_val
                    ax2.set_ylim(ref_min_val - 0.2 * ref_range, ref_max_val + 0.8 * ref_range)
            
            fig.tight_layout()
            
            # Create canvas and add to window
            canvas = FigureCanvasTkAgg(fig, master=detail_window)
            canvas.draw()
            canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
            
            # Add export button for this individual plot
            def create_export_function(fig, detail_window, interval_num):
                def export_detail_plot():
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"high_noise_interval_{interval_num}_{timestamp}.png"
                    filepath = os.path.join(output_dir, filename)
                    fig.savefig(filepath, dpi=300, bbox_inches='tight')
                    
                    # Show success message
                    success_label = tk.Label(detail_window, text=f"Exported: {filename}", 
                                           fg="green", font=("Arial", 10, "bold"))
                    success_label.pack()
                    detail_window.after(3000, success_label.destroy)
                return export_detail_plot
            
            export_detail_button = tk.Button(detail_window, text=f"Export Interval {i+1} Plot", 
                                            command=create_export_function(fig, detail_window, i+1), bg="lightgreen")
            export_detail_button.pack(pady=5)

    # === embed scatter plot of all raw data ===
    def plot_scatter(t_main, i_main, t_ref, i_ref, main_mean, main_max, ref_mean, ref_max, output_directory, high_noise_intervals=None):
        # Create separate window for ASTM noise plot
        astm_window = tk.Toplevel()
        astm_window.title("ASTM Noise Interval Plot")
        astm_window.geometry("1200x600")
        
        # Create figure and adjust right margin
        fig = Figure(figsize=(6, 4))
        fig.subplots_adjust(right=0.65)   # ← leave space for legend

        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()

        # Convert time from seconds to minutes using numpy
        t_main_array = np.array(t_main)
        t_ref_array = np.array(t_ref)
        i_main_array = np.array(i_main)
        i_ref_array = np.array(i_ref)
        
        t_main_minutes = t_main_array / 60.0
        t_ref_minutes = t_ref_array / 60.0
        
        pts1 = ax1.scatter(t_main_minutes, i_main_array, s=5, c='blue', label='Main')
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Main Intensity", color='blue', fontsize=10)
        ax1.tick_params(axis='y', colors='blue')

        pts2 = ax2.scatter(t_ref_minutes, i_ref_array, s=5, c='orange', label='Reference')
        ax2.set_ylabel("Reference Intensity", color='orange', fontsize=10)
        ax2.tick_params(axis='y', colors='orange')

        # Highlight high noise intervals if provided
        high_noise_legend_item = None
        if high_noise_intervals:
            for group in high_noise_intervals:
                start_min = group['start_time'] / 60.0
                end_min = group['end_time'] / 60.0
                # Add semi-transparent background highlighting
                highlight = ax1.axvspan(start_min, end_min, alpha=0.3, color='red')
                # Capture the first highlight for legend
                if high_noise_legend_item is None:
                    high_noise_legend_item = highlight

        # Adjust Y-limits using numpy operations
        #  - Main channel: extend lower limit by 20% of its range
        main_min_val, main_max_val = np.min(i_main_array), np.max(i_main_array)
        main_range = main_max_val - main_min_val
        ax1.set_ylim(main_min_val - 0.2 * main_range, main_max_val)

        #  - Reference channel: extend upper limit by 20% of its range
        ref_min_val, ref_max_val = np.min(i_ref_array), np.max(i_ref_array)
        ref_range = ref_max_val - ref_min_val
        ax2.set_ylim(ref_min_val, ref_max_val + 0.2 * ref_range)

        # Add vertical markers for warm-up end and analysis window end
        warmup_line = ax1.axvline(x=analysis_start_seconds/60.0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Warm-up end (30m)')
        analysis_end_line = ax1.axvline(x=analysis_end_seconds/60.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Analysis window end (90m)')

        # Default view: show the analysis window with ±5 minutes padding
        pad_seconds = 300  # 5 minutes
        display_start_min = max(0.0, (analysis_start_seconds - pad_seconds) / 60.0)
        display_end_min = (analysis_end_seconds + pad_seconds) / 60.0
        ax1.set_xlim(display_start_min, display_end_min)

        # Legend outside right - include high noise intervals if present
        main_label = f"Main\nNoise Mean (30-90m): {main_mean:.3f}\nNoise Max (30-90m): {main_max:.3f}"
        ref_label = f"Reference\nNoise Mean (30-90m): {ref_mean:.3f}\nNoise Max (30-90m): {ref_max:.3f}"
        
        legend_items = [pts1, pts2, warmup_line, analysis_end_line]
        legend_labels = [main_label, ref_label, "Warm-up end (30m)", "Analysis window end (90m)"]
        
        if high_noise_legend_item is not None:
            legend_items.append(high_noise_legend_item)
            legend_labels.append("High Noise Intervals")
        
        ax1.legend(legend_items, legend_labels,
                   loc='upper left',
                   bbox_to_anchor=(1.2, 1),
                   borderaxespad=0,
                   fontsize='small')

        # Add title using parent folder name
        parent_name = os.path.basename(output_directory) if output_directory else "ASTM"
        ax1.set_title(f"{parent_name} ASTM Noise", fontsize=12, pad=10)

        canvas = FigureCanvasTkAgg(fig, master=astm_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
        
        return fig, astm_window

    # Plot and capture the Figure for export
    # Pass high noise intervals if they were calculated
    high_intervals_to_plot = sorted_groups if show_high_noise_intervals and (n_intervals > 0 or noise_threshold is not None) and 'sorted_groups' in locals() else None
    scatter_fig, astm_window = plot_scatter(raw_t_main, raw_i_main, raw_t_ref, raw_i_ref,
                               main_mean, main_max, ref_mean, ref_max, output_directory, high_intervals_to_plot)

    # Add button to export the first plot
    def export_plot():
        # build default name: <parent_folder> noise containing the time <first_filename>.png
        parent_name = os.path.basename(output_directory)
        first_name  = os.path.basename(first_processed_file)
        # drop the last 19 characters from the first filename
        if len(first_name) > 19:
            trimmed_first = first_name[:-19]
        else:
            trimmed_first = first_name
        
        # Add timestamp and interval info if high noise intervals are shown
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if high_intervals_to_plot:
            interval_info = f"_with_{len(high_intervals_to_plot)}_intervals"
        else:
            interval_info = ""
        
        default_name = f"{parent_name}_ASTM_noise_{trimmed_first}{interval_info}_{timestamp}.png"
        save_path = os.path.join(output_directory, default_name)
        scatter_fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        # Show green success message
        success_label = tk.Label(astm_window, text=f"Exported: {default_name}", 
                               fg="green", font=("Arial", 10, "bold"))
        success_label.pack()
        # Remove message after 3 seconds
        astm_window.after(3000, success_label.destroy)

    export_button = tk.Button(astm_window, text="Export ASTM Noise Interval", command=export_plot)
    export_button.pack(pady=5)

    # === Create second plot with all files in folder ===
    def plot_all_files_in_folder(folder_path, main_mean, main_max, ref_mean, ref_max):
        # Find all files matching the naming convention
        pattern = os.path.join(folder_path, "*_*_DataCollection.txt")
        all_files = glob.glob(pattern)
        
        # Sort files by timestamp in filename
        def extract_timestamp(filename):
            basename = os.path.basename(filename)
            match = re.match(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_DataCollection\.txt', basename)
            return match.group(1) if match else basename
        
        all_files.sort(key=extract_timestamp)
        
        if not all_files:
            return None  # No files found
        
        # Pre-allocate lists for better performance
        all_t_main, all_i_main = [], []
        all_t_ref, all_i_ref = [], []
        time_offset = 0.0
        
        for i, filepath in enumerate(all_files):
            try:
                data = np.loadtxt(filepath, delimiter='\t', skiprows=2)
                times = data[:,0]
                offset_times = times + time_offset
                
                # Use extend with numpy arrays directly for better performance
                all_t_main.extend(offset_times)
                all_i_main.extend(data[:,2])
                all_t_ref.extend(offset_times)
                all_i_ref.extend(data[:,4])
                
                # Update time offset for next file
                time_offset = offset_times[-1]
                
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                continue
        
        if not all_t_main:
            return None  # No data loaded
        
        # Convert to numpy arrays for better performance
        all_t_main = np.array(all_t_main)
        all_i_main = np.array(all_i_main)
        all_t_ref = np.array(all_t_ref)
        all_i_ref = np.array(all_i_ref)
        
        # Create figure and adjust right margin
        fig = Figure(figsize=(6, 4))
        fig.subplots_adjust(right=0.65)   # ← leave space for legend

        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()

        # Convert time from seconds to hours using numpy
        t_main_hours = all_t_main / 3600.0
        t_ref_hours = all_t_ref / 3600.0
        
        pts1 = ax1.scatter(t_main_hours, all_i_main, s=5, c='blue', label='Main')
        ax1.set_xlabel("Time (hours)")
        ax1.set_ylabel("Main Intensity", color='blue', fontsize=10)
        ax1.tick_params(axis='y', colors='blue')

        pts2 = ax2.scatter(t_ref_hours, all_i_ref, s=5, c='orange', label='Reference')
        ax2.set_ylabel("Reference Intensity", color='orange', fontsize=10)
        ax2.tick_params(axis='y', colors='orange')

        # Adjust Y-limits using numpy operations
        #  - Main channel: extend lower limit by 20% of its range
        main_min_val, main_max_val = np.min(all_i_main), np.max(all_i_main)
        main_range = main_max_val - main_min_val
        ax1.set_ylim(main_min_val - 0.2 * main_range, main_max_val)

        #  - Reference channel: extend upper limit by 20% of its range
        ref_min_val, ref_max_val = np.min(all_i_ref), np.max(all_i_ref)
        ref_range = ref_max_val - ref_min_val
        ax2.set_ylim(ref_min_val, ref_max_val + 0.2 * ref_range)

        # Show warm-up end and analysis window end for the full dataset timeline
        warmup_line = ax1.axvline(x=analysis_start_seconds/3600.0, color='green', linestyle='--', 
                                linewidth=2, alpha=0.7, label='Warm-up end (0.5h)')
        analysis_end_line = ax1.axvline(x=analysis_end_seconds/3600.0, color='red', linestyle='--', 
                                       linewidth=2, alpha=0.7, label='Analysis window end (1.5h)')

        # Legend outside right
        main_label = f"Main\nNoise Mean (30-90m): {main_mean:.3f}\nNoise Max (30-90m): {main_max:.3f}"
        ref_label = f"Reference\nNoise Mean (30-90m): {ref_mean:.3f}\nNoise Max (30-90m): {ref_max:.3f}"
        
        # Build legend based on which lines exist
        legend_items = [pts1, pts2]
        legend_labels = [main_label, ref_label]
        
        legend_items.append(warmup_line)
        legend_labels.append("Warm-up end (0.5h)")
        legend_items.append(analysis_end_line)
        legend_labels.append("Analysis window end (1.5h)")
        
        ax1.legend(legend_items, legend_labels,
                   loc='upper left',
                   bbox_to_anchor=(1.2, 1),
                   borderaxespad=0,
                   fontsize='small')
        
        # Add title to distinguish from first plot
        total_time_hours = np.max(all_t_main) / 3600.0 if len(all_t_main) > 0 else 0
        ax1.set_title(f"Complete Dataset - {total_time_hours:.1f} hours total time", fontsize=12, pad=10)

        return fig, len(all_files), total_time_hours

    # Create second plot frame - remove since we're using separate windows
    # plot_frame2 = tk.Frame(root, width=800, height=400)
    # plot_frame2.pack(padx=10, pady=10)
    # plot_frame2.pack_propagate(False)

    # Generate the second plot if files are available and requested
    if output_directory and show_complete_dataset:
        all_files_fig, file_count, total_hours = plot_all_files_in_folder(output_directory, main_mean, main_max, ref_mean, ref_max)
        
        if all_files_fig is not None:
            # Create separate window for complete dataset plot
            complete_window = tk.Toplevel()
            complete_window.title("Complete Dataset Plot")
            complete_window.geometry("1200x600")
            
            canvas2 = FigureCanvasTkAgg(all_files_fig, master=complete_window)
            canvas2.draw()
            canvas2.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
            
            # Add export button for second plot
            def export_all_files_plot():
                parent_name = os.path.basename(output_directory)
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_name = f"{parent_name}_complete_dataset_{total_hours:.1f}h_{file_count}files_{timestamp}.png"
                save_path = os.path.join(output_directory, default_name)
                all_files_fig.savefig(save_path, dpi=300, bbox_inches='tight')
                
                # Show green success message
                success_label = tk.Label(complete_window, text=f"Exported: {default_name}", 
                                       fg="green", font=("Arial", 10, "bold"))
                success_label.pack()
                # Remove message after 3 seconds
                complete_window.after(3000, success_label.destroy)
            
            export_button2 = tk.Button(complete_window, text="Export Complete Dataset Plot", command=export_all_files_plot)
            export_button2.pack(pady=5)
        # else:
            # No message needed since we're not using a frame anymore


def create_gui():
    """Create and run the main GUI for ASTM Noise Analysis"""
    root = tk.Tk()
    root.title(f"{APP_NAME} v{APP_VERSION}")
    root.geometry("650x500")
    root.resizable(True, True)
    
    # Create main frame with padding
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = tk.Label(main_frame, text="ASTM Noise Analysis Configuration", 
                          font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 20))
    
    # Options frame
    options_frame = tk.LabelFrame(main_frame, text="Analysis Options", 
                                 font=("Arial", 12, "bold"), padx=10, pady=10)
    options_frame.pack(fill=tk.X, pady=(0, 15))
    
    # Complete dataset option
    show_complete_var = tk.BooleanVar()
    complete_check = tk.Checkbutton(options_frame, 
                                   text="Show Complete Dataset Plot", 
                                   variable=show_complete_var,
                                   font=("Arial", 10))
    complete_check.pack(anchor=tk.W, pady=2)
    
    # High noise intervals option
    show_intervals_var = tk.BooleanVar()
    intervals_check = tk.Checkbutton(options_frame, 
                                    text="Show High Noise Intervals", 
                                    variable=show_intervals_var,
                                    font=("Arial", 10),
                                    command=lambda: toggle_interval_options())
    intervals_check.pack(anchor=tk.W, pady=2)
    
    # Interval configuration frame
    interval_config_frame = tk.Frame(options_frame)
    interval_config_frame.pack(fill=tk.X, pady=(10, 0))
    
    # Threshold method (simplified - no radio buttons)
    threshold_frame = tk.Frame(interval_config_frame)
    threshold_frame.pack(fill=tk.X, pady=2)
    
    threshold_label = tk.Label(threshold_frame, text="Noise threshold:", 
                              font=("Arial", 10))
    threshold_label.pack(side=tk.LEFT)
    
    threshold_var = tk.StringVar(value="1200")
    threshold_entry = tk.Entry(threshold_frame, textvariable=threshold_var, width=8)
    threshold_entry.pack(side=tk.LEFT, padx=(5, 0))
    
    def toggle_interval_options():
        """Enable/disable interval configuration based on checkbox"""
        state = tk.NORMAL if show_intervals_var.get() else tk.DISABLED
        threshold_entry.config(state=state)
    
    # Initially disable interval options
    toggle_interval_options()
    
    # Instructions frame
    instructions_frame = tk.LabelFrame(main_frame, text="Instructions", 
                                      font=("Arial", 12, "bold"), padx=10, pady=10)
    instructions_frame.pack(fill=tk.X, pady=(0, 15))
    
    instructions_text = """1. Configure analysis options above
2. Click 'Start Analysis' to select data files
3. The tool will automatically process files chronologically
4. Results will appear in separate plot windows
5. Use the file selection features in High Noise Intervals popup"""
    
    instructions_label = tk.Label(instructions_frame, text=instructions_text, 
                                 font=("Arial", 9), justify=tk.LEFT)
    instructions_label.pack(anchor=tk.W)
    
    # Status frame
    status_frame = tk.Frame(main_frame)
    status_frame.pack(fill=tk.X, pady=(0, 15))
    
    status_label = tk.Label(status_frame, text="Ready to start analysis", 
                           font=("Arial", 10), fg="blue")
    status_label.pack()
    
    # Buttons frame
    buttons_frame = tk.Frame(main_frame)
    buttons_frame.pack(fill=tk.X)
    
    def start_analysis():
        """Start the ASTM noise analysis with selected options"""
        try:
            # Update status
            status_label.config(text="Starting analysis...", fg="orange")
            root.update()
            
            # Get configuration values
            show_complete = show_complete_var.get()
            show_intervals = show_intervals_var.get()
            
            # Determine interval parameters (threshold method only)
            n_intervals = 0
            noise_threshold = None
            max_intervals_to_plot = 8  # Default value for GUI mode
            
            if show_intervals:
                try:
                    noise_threshold = float(threshold_var.get())
                    if noise_threshold <= 0:
                        raise ValueError("Threshold must be positive")
                except ValueError as e:
                    messagebox.showerror("Invalid Input", f"Invalid threshold value: {e}")
                    status_label.config(text="Ready to start analysis", fg="blue")
                    return
            
            # Update status
            status_label.config(text="Analysis running...", fg="green")
            root.update()
            
            # Run the analysis
            load_and_calculate_noise_multiple(
                show_complete_dataset=show_complete,
                show_high_noise_intervals=show_intervals,
                n_intervals=n_intervals,
                noise_threshold=noise_threshold,
                max_intervals_to_plot=max_intervals_to_plot
            )
            
            # Update status
            status_label.config(text="Analysis completed successfully!", fg="green")
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"An error occurred during analysis:\n{str(e)}")
            status_label.config(text="Analysis failed", fg="red")
    
    def reset_options():
        """Reset all options to defaults"""
        show_complete_var.set(False)
        show_intervals_var.set(False)
        threshold_var.set("1200")
        toggle_interval_options()
        status_label.config(text="Options reset to defaults", fg="blue")
    
    # Start Analysis button
    start_button = tk.Button(buttons_frame, text="Start Analysis", 
                            command=start_analysis, bg="lightgreen",
                            font=("Arial", 12, "bold"), pady=8, width=15)
    start_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Reset button
    reset_button = tk.Button(buttons_frame, text="Reset Options", 
                            command=reset_options, bg="lightblue",
                            font=("Arial", 12, "bold"), pady=8, width=15)
    reset_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Exit button
    exit_button = tk.Button(buttons_frame, text="Exit", 
                           command=root.quit, bg="lightcoral",
                           font=("Arial", 12, "bold"), pady=8, width=10)
    exit_button.pack(side=tk.RIGHT)
    
    # Add keyboard shortcuts
    root.bind('<Return>', lambda e: start_analysis())
    root.bind('<Escape>', lambda e: root.quit())
    
    # Center the window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    return root


def main():
    """Main function with both GUI and command-line interface"""
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Parse command line arguments
        show_complete_dataset = '--show-complete-dataset' in sys.argv
        show_high_noise_intervals = '--show-high-noise-intervals' in sys.argv
        
        # Parse n_intervals parameter
        n_intervals = 8  # Default value
        if '--n-intervals' in sys.argv:
            try:
                idx = sys.argv.index('--n-intervals')
                if idx + 1 < len(sys.argv):
                    n_intervals = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                n_intervals = 8
        
        # Parse noise_threshold parameter
        noise_threshold = None
        if '--noise-threshold' in sys.argv:
            try:
                idx = sys.argv.index('--noise-threshold')
                if idx + 1 < len(sys.argv):
                    noise_threshold = float(sys.argv[idx + 1])
            except (ValueError, IndexError):
                noise_threshold = None
        
        # Parse max_intervals_to_plot parameter
        max_intervals_to_plot = 8  # Default value
        if '--max-intervals-to-plot' in sys.argv:
            try:
                idx = sys.argv.index('--max-intervals-to-plot')
                if idx + 1 < len(sys.argv):
                    max_intervals_to_plot = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                max_intervals_to_plot = 8
        
        # Run with command line arguments
        load_and_calculate_noise_multiple(
            show_complete_dataset=show_complete_dataset,
            show_high_noise_intervals=show_high_noise_intervals,
            n_intervals=n_intervals,
            noise_threshold=noise_threshold,
            max_intervals_to_plot=max_intervals_to_plot
        )
    else:
        # Create and run the GUI
        root = create_gui()
        root.mainloop()


if __name__ == "__main__":
    main()