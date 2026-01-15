"""
ASTM Noise Analysis - Plotting Module

This module handles all plotting functionality including scatter plots, 
complete dataset plots, and detailed interval plots.
"""

import tkinter as tk
import numpy as np
import os
import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import *


class ScatterPlotter:
    """Handles the main ASTM noise scatter plot"""
    
    def __init__(self, raw_data, stats, output_directory, first_filename, high_noise_intervals=None):
        self.raw_t_main, self.raw_i_main, self.raw_t_ref, self.raw_i_ref = raw_data
        self.stats = stats
        self.output_directory = output_directory
        self.first_filename = first_filename
        self.high_noise_intervals = high_noise_intervals
        
    def create_plot(self):
        """Create the main ASTM noise scatter plot"""
        # Create separate window for ASTM noise plot
        astm_window = tk.Toplevel()
        astm_window.title("ASTM Noise Interval Plot")
        astm_window.geometry(ASTM_PLOT_WINDOW_SIZE)
        
        # Create figure and adjust right margin
        fig = Figure(figsize=(6, 4))
        fig.subplots_adjust(right=0.65)   # ← leave space for legend

        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()

        # Convert time from seconds to minutes using numpy
        t_main_array = np.array(self.raw_t_main)
        t_ref_array = np.array(self.raw_t_ref)
        i_main_array = np.array(self.raw_i_main)
        i_ref_array = np.array(self.raw_i_ref)
        
        t_main_minutes = t_main_array / 60.0
        t_ref_minutes = t_ref_array / 60.0
        
        pts1 = ax1.scatter(t_main_minutes, i_main_array, s=5, c=MAIN_CHANNEL_COLOR, label='Main')
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Main Intensity", color=MAIN_CHANNEL_COLOR, fontsize=10)
        ax1.tick_params(axis='y', colors=MAIN_CHANNEL_COLOR)

        pts2 = ax2.scatter(t_ref_minutes, i_ref_array, s=5, c=REF_CHANNEL_COLOR, label='Reference')
        ax2.set_ylabel("Reference Intensity", color=REF_CHANNEL_COLOR, fontsize=10)
        ax2.tick_params(axis='y', colors=REF_CHANNEL_COLOR)

        # Highlight high noise intervals if provided
        high_noise_legend_item = None
        if self.high_noise_intervals:
            for group in self.high_noise_intervals:
                start_min = group['start_time'] / 60.0
                end_min = group['end_time'] / 60.0
                # Add semi-transparent background highlighting
                highlight = ax1.axvspan(start_min, end_min, alpha=0.3, color=HIGH_NOISE_HIGHLIGHT_COLOR)
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

        # Add vertical line at 60 minutes
        vline = ax1.axvline(x=60, color=ASTM_LIMIT_COLOR, linestyle='--', linewidth=2, alpha=0.7, label='ASTM Time Interval limit')

        # Legend outside right - include high noise intervals if present
        main_label = f"Main\nNoise Mean: {self.stats['main_mean']:.3f}\nNoise Max: {self.stats['main_max']:.3f}"
        ref_label = f"Reference\nNoise Mean: {self.stats['ref_mean']:.3f}\nNoise Max: {self.stats['ref_max']:.3f}"
        
        legend_items = [pts1, pts2, vline]
        legend_labels = [main_label, ref_label, "ASTM time limit"]
        
        if high_noise_legend_item is not None:
            legend_items.append(high_noise_legend_item)
            legend_labels.append("High Noise Intervals")
        
        ax1.legend(legend_items, legend_labels,
                   loc='upper left',
                   bbox_to_anchor=(1.2, 1),
                   borderaxespad=0,
                   fontsize='small')

        # Add title using parent folder name
        parent_name = os.path.basename(self.output_directory) if self.output_directory else "ASTM"
        ax1.set_title(f"{parent_name} ASTM Noise", fontsize=12, pad=10)

        canvas = FigureCanvasTkAgg(fig, master=astm_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
        
        # Add export button
        export_button = tk.Button(astm_window, text="Export ASTM Noise Interval", 
                                 command=lambda: self._export_plot(fig, astm_window))
        export_button.pack(pady=5)
        
        return fig, astm_window
    
    def _export_plot(self, fig, window):
        """Export the plot to a file"""
        parent_name = os.path.basename(self.output_directory)
        first_name = self.first_filename
        # drop the last 19 characters from the first filename
        if len(first_name) > 19:
            trimmed_first = first_name[:-19]
        else:
            trimmed_first = first_name
        
        # Add timestamp and interval info if high noise intervals are shown
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.high_noise_intervals:
            interval_info = f"_with_{len(self.high_noise_intervals)}_intervals"
        else:
            interval_info = ""
        
        default_name = f"{parent_name}_ASTM_noise_{trimmed_first}{interval_info}_{timestamp}.png"
        save_path = os.path.join(self.output_directory, default_name)
        fig.savefig(save_path, dpi=EXPORT_DPI, bbox_inches='tight')
        
        # Show success message
        success_label = tk.Label(window, text=f"Exported: {default_name}", 
                               fg="green", font=("Arial", 10, "bold"))
        success_label.pack()
        window.after(3000, success_label.destroy)


class CompletePlotter:
    """Handles the complete dataset plot showing all files"""
    
    def __init__(self, output_directory, stats):
        self.output_directory = output_directory
        self.stats = stats
        
    def create_plot(self):
        """Create the complete dataset plot"""
        import glob
        import re
        
        # Find all files matching the naming convention
        pattern = os.path.join(self.output_directory, "*_*_DataCollection.txt")
        all_files = glob.glob(pattern)
        
        # Sort files by timestamp in filename
        def extract_timestamp(filename):
            basename = os.path.basename(filename)
            match = re.match(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_DataCollection\.txt', basename)
            return match.group(1) if match else basename
        
        all_files.sort(key=extract_timestamp)
        
        if not all_files:
            return None  # No files found
        
        # Load and process all files
        all_t_main, all_i_main = [], []
        all_t_ref, all_i_ref = [], []
        time_offset = 0.0
        first_file_end_time = None
        
        for i, filepath in enumerate(all_files):
            try:
                data = np.loadtxt(filepath, delimiter='\t', skiprows=2)
                times = data[:,0]
                offset_times = times + time_offset
                
                all_t_main.extend(offset_times)
                all_i_main.extend(data[:,2])
                all_t_ref.extend(offset_times)
                all_i_ref.extend(data[:,4])
                
                time_offset = offset_times[-1]
                
                if i == 0:
                    first_file_end_time = offset_times[-1]
                    
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                continue
        
        if not all_t_main:
            return None
        
        # Convert to numpy arrays
        all_t_main = np.array(all_t_main)
        all_i_main = np.array(all_i_main)
        all_t_ref = np.array(all_t_ref)
        all_i_ref = np.array(all_i_ref)
        
        # Create plot window
        complete_window = tk.Toplevel()
        complete_window.title("Complete Dataset Plot")
        complete_window.geometry(COMPLETE_PLOT_WINDOW_SIZE)
        
        # Create figure
        fig = Figure(figsize=(6, 4))
        fig.subplots_adjust(right=0.65)

        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()

        # Convert time from seconds to hours
        t_main_hours = all_t_main / 3600.0
        t_ref_hours = all_t_ref / 3600.0
        
        pts1 = ax1.scatter(t_main_hours, all_i_main, s=5, c=MAIN_CHANNEL_COLOR, label='Main')
        ax1.set_xlabel("Time (hours)")
        ax1.set_ylabel("Main Intensity", color=MAIN_CHANNEL_COLOR, fontsize=10)
        ax1.tick_params(axis='y', colors=MAIN_CHANNEL_COLOR)

        pts2 = ax2.scatter(t_ref_hours, all_i_ref, s=5, c=REF_CHANNEL_COLOR, label='Reference')
        ax2.set_ylabel("Reference Intensity", color=REF_CHANNEL_COLOR, fontsize=10)
        ax2.tick_params(axis='y', colors=REF_CHANNEL_COLOR)

        # Adjust Y-limits
        main_min_val, main_max_val = np.min(all_i_main), np.max(all_i_main)
        main_range = main_max_val - main_min_val
        ax1.set_ylim(main_min_val - 0.2 * main_range, main_max_val)

        ref_min_val, ref_max_val = np.min(all_i_ref), np.max(all_i_ref)
        ref_range = ref_max_val - ref_min_val
        ax2.set_ylim(ref_min_val, ref_max_val + 0.2 * ref_range)

        # Add vertical lines
        if first_file_end_time is not None:
            first_file_end_hours = first_file_end_time / 3600.0
            vline_green = ax1.axvline(x=first_file_end_hours, color=ASTM_START_COLOR, linestyle='--', 
                                    linewidth=2, alpha=0.7, label='ASTM Noise Interval start')
            
            astm_limit_hours = first_file_end_hours + 1.0
            vline_red = ax1.axvline(x=astm_limit_hours, color=ASTM_LIMIT_COLOR, linestyle='--', 
                                  linewidth=2, alpha=0.7, label='ASTM Time Interval limit')
        else:
            vline_red = ax1.axvline(x=1.0, color=ASTM_LIMIT_COLOR, linestyle='--', 
                                  linewidth=2, alpha=0.7, label='ASTM Time Interval limit')
            vline_green = None

        # Legend
        main_label = f"Main\nNoise Mean: {self.stats['main_mean']:.3f}\nNoise Max: {self.stats['main_max']:.3f}"
        ref_label = f"Reference\nNoise Mean: {self.stats['ref_mean']:.3f}\nNoise Max: {self.stats['ref_max']:.3f}"
        
        legend_items = [pts1, pts2]
        legend_labels = [main_label, ref_label]
        
        if vline_green is not None:
            legend_items.append(vline_green)
            legend_labels.append("ASTM Time Interval start")
            
        legend_items.append(vline_red)
        legend_labels.append("ASTM Time Interval limit")
        
        ax1.legend(legend_items, legend_labels,
                   loc='upper left',
                   bbox_to_anchor=(1.2, 1),
                   borderaxespad=0,
                   fontsize='small')
        
        # Title
        total_time_hours = np.max(all_t_main) / 3600.0 if len(all_t_main) > 0 else 0
        ax1.set_title(f"Complete Dataset - {total_time_hours:.1f} hours total time", fontsize=12, pad=10)

        canvas = FigureCanvasTkAgg(fig, master=complete_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
        
        # Add export button
        export_button = tk.Button(complete_window, text="Export Complete Dataset Plot", 
                                 command=lambda: self._export_plot(fig, complete_window, len(all_files), total_time_hours))
        export_button.pack(pady=5)
        
        return fig, len(all_files), total_time_hours
    
    def _export_plot(self, fig, window, file_count, total_hours):
        """Export the complete dataset plot"""
        parent_name = os.path.basename(self.output_directory)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{parent_name}_complete_dataset_{total_hours:.1f}h_{file_count}files_{timestamp}.png"
        save_path = os.path.join(self.output_directory, default_name)
        fig.savefig(save_path, dpi=EXPORT_DPI, bbox_inches='tight')
        
        success_label = tk.Label(window, text=f"Exported: {default_name}", 
                               fg="green", font=("Arial", 10, "bold"))
        success_label.pack()
        window.after(3000, success_label.destroy)


class DetailedIntervalPlotter:
    """Handles detailed plotting of individual high noise intervals"""
    
    def __init__(self, interval_groups, raw_data, output_directory):
        self.interval_groups = interval_groups
        self.raw_t_main, self.raw_i_main, self.raw_t_ref, self.raw_i_ref = raw_data
        self.output_directory = output_directory
    
    def plot_all_intervals(self):
        """Plot detailed view of all high noise intervals - each in separate window"""
        n_intervals = len(self.interval_groups)
        if n_intervals == 0:
            return
        
        # Create separate window for each interval
        for i, group in enumerate(self.interval_groups):
            self._plot_single_interval(i, group)
    
    def _plot_single_interval(self, interval_index, group):
        """Plot a single interval in its own window"""
        # Create individual window for this interval
        detail_window = tk.Toplevel()
        detail_window.title(f"Interval {interval_index+1}: {group['start_time']/60.0:.1f}-{group['end_time']/60.0:.1f} min")
        detail_window.geometry(DETAIL_INTERVAL_WINDOW_SIZE)
        
        # Create individual figure for this interval
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        # Convert to numpy arrays and minutes for better performance
        t_main_array = np.array(self.raw_t_main) if not isinstance(self.raw_t_main, np.ndarray) else self.raw_t_main
        i_main_array = np.array(self.raw_i_main) if not isinstance(self.raw_i_main, np.ndarray) else self.raw_i_main
        t_ref_array = np.array(self.raw_t_ref) if not isinstance(self.raw_t_ref, np.ndarray) else self.raw_t_ref
        i_ref_array = np.array(self.raw_i_ref) if not isinstance(self.raw_i_ref, np.ndarray) else self.raw_i_ref
        
        t_main_min = t_main_array / 60.0
        t_ref_min = t_ref_array / 60.0
        
        # Find data points within the interval
        start_min = group['start_time'] / 60.0
        end_min = group['end_time'] / 60.0
        
        # Plot all data in light colors
        ax.scatter(t_main_min, i_main_array, s=4, c=MAIN_CHANNEL_COLOR, alpha=0.5, label='Main (all)')
        
        # Create second y-axis for reference data
        ax2 = ax.twinx()
        ax2.scatter(t_ref_min, i_ref_array, s=4, c=REF_CHANNEL_COLOR, alpha=0.5, label='Ref (all)')
        
        # Use numpy boolean indexing for better performance
        interval_mask_main = (t_main_min >= start_min) & (t_main_min <= end_min)
        interval_mask_ref = (t_ref_min >= start_min) & (t_ref_min <= end_min)
        
        if np.any(interval_mask_main):
            interval_t_main = t_main_min[interval_mask_main]
            interval_i_main = i_main_array[interval_mask_main]
            ax.scatter(interval_t_main, interval_i_main, s=8, c=MAIN_CHANNEL_COLOR, label='Main (interval)')
            
            # Add convex hull for main channel interval data
            self._add_convex_hull(ax, interval_t_main, interval_i_main, MAIN_CHANNEL_COLOR)
        
        if np.any(interval_mask_ref):
            interval_t_ref = t_ref_min[interval_mask_ref]
            interval_i_ref = i_ref_array[interval_mask_ref]
            ax2.scatter(interval_t_ref, interval_i_ref, s=8, c=REF_CHANNEL_COLOR, label='Ref (interval)')
            
            # Add convex hull for reference channel interval data
            self._add_convex_hull(ax2, interval_t_ref, interval_i_ref, REF_CHANNEL_COLOR)
        
        # Set axis labels and title
        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel("Main Intensity", color=MAIN_CHANNEL_COLOR)
        ax2.set_ylabel("Reference Intensity", color=REF_CHANNEL_COLOR)
        ax.tick_params(axis='y', colors=MAIN_CHANNEL_COLOR)
        ax2.tick_params(axis='y', colors=REF_CHANNEL_COLOR)
        
        # Set title with noise values
        main_noise_str = f"{group['main_noise']:.3f}" if group['main_noise'] is not None else "N/A"
        ref_noise_str = f"{group['ref_noise']:.3f}" if group['ref_noise'] is not None else "N/A"
        ax.set_title(f"Interval {interval_index+1}: {start_min:.1f}-{end_min:.1f} min\nMain: {main_noise_str}, Ref: {ref_noise_str}", 
                    fontsize=10)
        
        # Set reasonable zoom around the interval
        time_buffer = DEFAULT_TIME_BUFFER / 60.0  # Convert to minutes
        ax.set_xlim(max(0, start_min - time_buffer), end_min + time_buffer)
        
        # Adjust Y-axis ranges for better visualization
        if np.any(interval_mask_main):
            self._adjust_y_axis(ax, i_main_array[interval_mask_main], extend_down=0.8, extend_up=0.2)
        
        if np.any(interval_mask_ref):
            self._adjust_y_axis(ax2, i_ref_array[interval_mask_ref], extend_down=0.2, extend_up=0.8)
        
        fig.tight_layout()
        
        # Create canvas and add to window
        canvas = FigureCanvasTkAgg(fig, master=detail_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=10, pady=10)
        
        # Add export button for this individual plot
        export_button = tk.Button(detail_window, text=f"Export Interval {interval_index+1} Plot", 
                                command=lambda: self._export_interval_plot(fig, detail_window, interval_index+1), 
                                bg="lightgreen")
        export_button.pack(pady=5)
    
    def _add_convex_hull(self, axis, time_data, intensity_data, color):
        """Add convex hull visualization to the plot"""
        if len(intensity_data) > 2:
            points = np.column_stack((time_data, intensity_data))
            try:
                from scipy.spatial import ConvexHull
                hull = ConvexHull(points)
                # Plot convex hull boundary
                for simplex in hull.simplices:
                    axis.plot(points[simplex, 0], points[simplex, 1], color=color, alpha=0.7, linewidth=1.5)
            except ImportError:
                # Fallback if scipy not available - just connect min/max points
                min_idx = np.argmin(intensity_data)
                max_idx = np.argmax(intensity_data)
                axis.plot([time_data[min_idx], time_data[max_idx]], 
                         [intensity_data[min_idx], intensity_data[max_idx]], 
                         color=color, alpha=0.7, linewidth=1.5, linestyle='--')
    
    def _adjust_y_axis(self, axis, data, extend_down=0.2, extend_up=0.2):
        """Adjust Y-axis limits with specified extensions"""
        if len(data) > 0:
            min_val = np.min(data)
            max_val = np.max(data)
            data_range = max_val - min_val
            axis.set_ylim(min_val - extend_down * data_range, max_val + extend_up * data_range)
    
    def _export_interval_plot(self, fig, window, interval_num):
        """Export an individual interval plot"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"high_noise_interval_{interval_num}_{timestamp}.png"
        filepath = os.path.join(self.output_directory, filename)
        fig.savefig(filepath, dpi=EXPORT_DPI, bbox_inches='tight')
        
        # Show success message
        success_label = tk.Label(window, text=f"Exported: {filename}", 
                               fg="green", font=("Arial", 10, "bold"))
        success_label.pack()
        window.after(3000, success_label.destroy)
