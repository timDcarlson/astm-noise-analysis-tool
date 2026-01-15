"""
ASTM Noise Analysis - GUI Components Module

This module handles all the GUI-related functionality including windows, plots, and user interactions.
Separated from data processing for better maintainability.
"""

import tkinter as tk
from tkinter import messagebox
import numpy as np
import os
import datetime
import glob
import re
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import *


class IntervalDisplayWindow:
    """Handles the high noise intervals display window"""
    
    def __init__(self, sorted_groups, noise_threshold, raw_data, output_directory):
        self.sorted_groups = sorted_groups
        self.noise_threshold = noise_threshold
        self.raw_t_main, self.raw_i_main, self.raw_t_ref, self.raw_i_ref = raw_data
        self.output_directory = output_directory
        self.interval_window = None
        
    def create_window(self):
        """Create and display the intervals window"""
        # Generate interval text
        if self.noise_threshold is not None:
            interval_text = f"\nHigh Noise Intervals Above {self.noise_threshold} (0-3600s only, {len(self.sorted_groups)} found):\n"
            window_title = f"High Noise Intervals (Above {self.noise_threshold})"
        else:
            interval_text = f"\nTop {len(self.sorted_groups)} High Noise Intervals (0-3600s only):\n"
            window_title = "High Noise Intervals"
            
        interval_text += "=" * 70 + "\n"
        for i, group in enumerate(self.sorted_groups, 1):
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
        
        # Create window
        self.interval_window = tk.Toplevel()
        self.interval_window.title(window_title)
        self.interval_window.geometry(INTERVAL_WINDOW_SIZE)
        
        # Create main frame
        main_frame = tk.Frame(self.interval_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text display
        self._create_text_display(main_frame, interval_text)
        
        # Create file selection section
        self._create_file_selection(main_frame)
        
        # Create buttons
        self._create_buttons(main_frame, interval_text)
    
    def _create_text_display(self, parent, interval_text):
        """Create the text display area"""
        text_frame = tk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        text_widget = tk.Text(text_frame, font=("Courier", 10), wrap=tk.WORD)
        text_widget.insert(tk.END, interval_text)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_file_selection(self, parent):
        """Create the file selection section"""
        file_selection_frame = tk.Frame(parent)
        file_selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_label = tk.Label(file_selection_frame, text="Compute Noise Values for Additional Files:", 
                             font=("Arial", 10, "bold"))
        file_label.pack(anchor=tk.W)
        
        # Create scrollable frame for file checkboxes
        file_scroll_frame = tk.Frame(file_selection_frame, height=120)
        file_scroll_frame.pack(fill=tk.X, pady=(5, 0))
        file_scroll_frame.pack_propagate(False)
        
        canvas = tk.Canvas(file_scroll_frame, height=120)
        scrollbar_files = tk.Scrollbar(file_scroll_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_files.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_files.pack(side="right", fill="y")
        
        # Mouse wheel support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Create file checkboxes
        self.file_checkboxes = self._create_file_checkboxes(scrollable_frame, _on_mousewheel)
    
    def _create_file_checkboxes(self, parent, mousewheel_handler):
        """Create checkboxes for file selection"""
        def extract_timestamp_local(filename):
            basename = os.path.basename(filename)
            match = re.match(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', basename)
            if match:
                return match.group(1)
            match = re.search(r'(\d{4}-\d{2}-\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2})', basename)
            if match:
                return match.group(1)
            return basename
        
        all_files_pattern = os.path.join(self.output_directory, "*_*_DataCollection.txt")
        all_available_files = glob.glob(all_files_pattern)
        all_available_files.sort(key=extract_timestamp_local)
        
        file_checkboxes = {}
        for filepath in all_available_files:
            filename = os.path.basename(filepath)
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(parent, text=filename, variable=var, 
                                     font=("Arial", 9), anchor="w")
            checkbox.pack(fill="x", padx=5, pady=1)
            checkbox.bind("<MouseWheel>", mousewheel_handler)
            file_checkboxes[filepath] = var
        
        return file_checkboxes
    
    def _create_buttons(self, parent, interval_text):
        """Create the action buttons"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Plot intervals button
        plot_button = tk.Button(button_frame, text="Plot 30-Second Intervals", 
                               command=self._plot_30_second_intervals, bg="lightblue", 
                               font=("Arial", 10, "bold"), pady=8)
        plot_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Compute noise button
        compute_button = tk.Button(button_frame, text="Compute Noise for Selected Files", 
                                 command=self._compute_selected_file_noise, bg="lightyellow",
                                 font=("Arial", 10, "bold"), pady=8)
        compute_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export button
        export_button = tk.Button(button_frame, text="Export Interval List", 
                                 command=lambda: self._export_interval_list(interval_text), bg="lightgreen",
                                 font=("Arial", 10, "bold"), pady=8)
        export_button.pack(side=tk.LEFT)
    
    def _plot_30_second_intervals(self):
        """Create individual plots for each high noise interval"""
        from gui_plots import DetailedIntervalPlotter
        plotter = DetailedIntervalPlotter(self.sorted_groups, 
                                        (self.raw_t_main, self.raw_i_main, self.raw_t_ref, self.raw_i_ref),
                                        self.output_directory)
        plotter.plot_all_intervals()
    
    def _compute_selected_file_noise(self):
        """Compute noise for selected files"""
        selected_files = [filepath for filepath, var in self.file_checkboxes.items() if var.get()]
        if not selected_files:
            messagebox.showwarning("No Files Selected", "Please select at least one file to compute noise values.")
            return
        
        # Create a new window to show the results
        results_window = tk.Toplevel(self.interval_window)
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
        
        # Use data processor to analyze each file
        from data_processor import NoiseDataProcessor
        processor = NoiseDataProcessor()
        
        for filepath in selected_files:
            filename = os.path.basename(filepath)
            results_output += f"File: {filename}\n"
            results_output += "-" * 50 + "\n"
            
            try:
                # Process single file
                processor.process_files([filepath])
                stats = processor.get_statistics()
                
                # Add results to output
                results_output += f"Main Channel ({stats['main_count']} intervals):\n"
                results_output += f"  Mean:   {stats['main_mean']:.3f}\n"
                results_output += f"  Max:    {stats['main_max']:.3f}\n\n"
                
                results_output += f"Reference Channel ({stats['ref_count']} intervals):\n"
                results_output += f"  Mean:   {stats['ref_mean']:.3f}\n"
                results_output += f"  Max:    {stats['ref_max']:.3f}\n\n"
                
                # Reset processor for next file
                processor = NoiseDataProcessor()
                
            except Exception as e:
                results_output += f"Error processing file: {e}\n\n"
            
            results_output += "\n"
        
        # Display results
        results_text.insert(tk.END, results_output)
        results_text.config(state=tk.DISABLED)
        
        # Add export button for results
        def export_file_noise_results():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"selected_files_noise_analysis_{timestamp}.txt"
            filepath = os.path.join(self.output_directory, filename)
            
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
    
    def _export_interval_list(self, interval_text):
        """Export the interval list to a text file"""
        if not self.output_directory:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.noise_threshold is not None:
            filename = f"high_noise_intervals_above_{self.noise_threshold}_{timestamp}.txt"
        else:
            filename = f"high_noise_intervals_top_{len(self.sorted_groups)}_{timestamp}.txt"
        filepath = os.path.join(self.output_directory, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(interval_text)
            
            success_label = tk.Label(self.interval_window, text=f"Exported: {filename}", 
                                   fg="green", font=("Arial", 9, "bold"))
            success_label.pack(pady=5)
            self.interval_window.after(3000, success_label.destroy)
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting interval list: {e}")


class NoiseAnalysisGUI:
    """Main GUI class for the ASTM Noise Analysis Tool"""
    
    def __init__(self, root):
        self.root = root
        self.setup_main_window()
        self.create_widgets()
    
    def setup_main_window(self):
        """Configure the main window"""
        from config import APP_NAME, APP_VERSION
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(MAIN_WINDOW_SIZE)
        self.root.resizable(True, True)
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="ASTM Noise Analysis Configuration", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Options frame
        self._create_options_frame(main_frame)
        
        # Instructions frame
        self._create_instructions_frame(main_frame)
        
        # Status and buttons
        self._create_status_and_buttons(main_frame)
    
    def _create_options_frame(self, parent):
        """Create the analysis options frame"""
        options_frame = tk.LabelFrame(parent, text="Analysis Options", 
                                     font=("Arial", 12, "bold"), padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Complete dataset option
        self.show_complete_var = tk.BooleanVar()
        complete_check = tk.Checkbutton(options_frame, 
                                       text="Show Complete Dataset Plot", 
                                       variable=self.show_complete_var,
                                       font=("Arial", 10))
        complete_check.pack(anchor=tk.W, pady=2)
        
        # High noise intervals option
        self.show_intervals_var = tk.BooleanVar()
        intervals_check = tk.Checkbutton(options_frame, 
                                        text="Show High Noise Intervals", 
                                        variable=self.show_intervals_var,
                                        font=("Arial", 10))
        intervals_check.pack(anchor=tk.W, pady=2)
        
        # Threshold configuration
        threshold_frame = tk.Frame(options_frame)
        threshold_frame.pack(fill=tk.X, pady=(10, 0))
        
        threshold_label = tk.Label(threshold_frame, text="Noise threshold:", 
                                  font=("Arial", 10))
        threshold_label.pack(side=tk.LEFT)
        
        self.threshold_var = tk.StringVar(value=str(DEFAULT_NOISE_THRESHOLD))
        threshold_entry = tk.Entry(threshold_frame, textvariable=self.threshold_var, width=8)
        threshold_entry.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_instructions_frame(self, parent):
        """Create the instructions frame"""
        instructions_frame = tk.LabelFrame(parent, text="Instructions", 
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
    
    def _create_status_and_buttons(self, parent):
        """Create status display and action buttons"""
        # Status frame
        status_frame = tk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_label = tk.Label(status_frame, text="Ready to start analysis", 
                                   font=("Arial", 10), fg="blue")
        self.status_label.pack()
        
        # Buttons frame
        buttons_frame = tk.Frame(parent)
        buttons_frame.pack(fill=tk.X)
        
        # Start analysis button
        start_button = tk.Button(buttons_frame, text="Start Analysis", 
                               command=self.start_analysis, 
                               font=("Arial", 12, "bold"), 
                               bg="lightgreen", pady=10)
        start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Help button
        help_button = tk.Button(buttons_frame, text="Help", 
                              command=self.show_help,
                              font=("Arial", 12), pady=10)
        help_button.pack(side=tk.LEFT)
    
    def start_analysis(self):
        """Start the noise analysis process"""
        from tkinter import filedialog
        from data_processor import NoiseDataProcessor
        from gui_plots import ScatterPlotter, CompletePlotter
        
        # Get first file from user
        first_filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not first_filepath:
            return
        
        self.status_label.config(text="Processing files...", fg="orange")
        self.root.update()
        
        try:
            # Initialize data processor
            processor = NoiseDataProcessor()
            
            # Find and process files
            files_to_process, selected_timestamp = processor.find_chronological_files(first_filepath)
            
            print(f"Starting with selected file: {os.path.basename(first_filepath)}")
            print(f"Selected file timestamp: {selected_timestamp}")
            print(f"Total files to process: {len(files_to_process)}")
            
            processor.process_files(files_to_process)
            
            # Get statistics
            stats = processor.get_statistics()
            
            # Export CSV
            output_directory = os.path.dirname(first_filepath)
            success, message = processor.export_csv(output_directory, stats)
            if not success:
                messagebox.showerror("Export Error", message)
            
            # Create plots
            self._create_plots(processor, stats, output_directory, os.path.basename(files_to_process[0]))
            
            # Handle high noise intervals if requested
            if self.show_intervals_var.get():
                self._show_high_noise_intervals(processor, output_directory)
            
            self.status_label.config(text="Analysis complete!", fg="green")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", fg="red")
            messagebox.showerror("Analysis Error", f"An error occurred during analysis: {str(e)}")
    
    def _create_plots(self, processor, stats, output_directory, first_filename):
        """Create the analysis plots"""
        from gui_plots import ScatterPlotter, CompletePlotter
        
        # Create main ASTM plot
        scatter_plotter = ScatterPlotter(
            (processor.raw_t_main, processor.raw_i_main, processor.raw_t_ref, processor.raw_i_ref),
            stats, output_directory, first_filename
        )
        scatter_plotter.create_plot()
        
        # Create complete dataset plot if requested
        if self.show_complete_var.get():
            complete_plotter = CompletePlotter(output_directory, stats)
            complete_plotter.create_plot()
    
    def _show_high_noise_intervals(self, processor, output_directory):
        """Show high noise intervals analysis"""
        try:
            threshold = float(self.threshold_var.get()) if self.threshold_var.get() else None
        except ValueError:
            threshold = DEFAULT_NOISE_THRESHOLD
        
        sorted_groups = processor.get_high_noise_intervals(noise_threshold=threshold)
        
        if sorted_groups:
            interval_window = IntervalDisplayWindow(
                sorted_groups, threshold,
                (processor.raw_t_main, processor.raw_i_main, processor.raw_t_ref, processor.raw_i_ref),
                output_directory
            )
            interval_window.create_window()
        else:
            messagebox.showinfo("No Intervals", f"No intervals found above threshold {threshold}")
    
    def show_help(self):
        """Show help information"""
        help_text = """ASTM Noise Analysis Tool Help

This tool analyzes lamp stability data according to ASTM standards.

Basic Usage:
1. Click 'Start Analysis'
2. Select your first data file
3. The tool will automatically find and process subsequent files
4. View results in the generated plots

Options:
- Complete Dataset: Shows all files in the folder over time
- High Noise Intervals: Identifies periods of high noise
- Noise Threshold: Set minimum noise level for interval detection

For detailed help, see the HELP.md file included with this tool."""
        
        messagebox.showinfo("Help - ASTM Noise Analysis Tool", help_text)
