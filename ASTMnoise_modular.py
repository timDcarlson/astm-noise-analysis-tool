"""
ASTM Noise Analysis Tool - Main Application Entry Point

A refactored version of the ASTM noise analysis tool with modular architecture.
This main script provides the entry point and command-line interface.

Version: 3.1.1
Author: Tim Carlson
"""

import tkinter as tk
import argparse
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_VERSION, APP_NAME
from gui_components import NoiseAnalysisGUI
from data_processor import NoiseDataProcessor


def create_gui():
    """Create and run the main GUI for ASTM Noise Analysis"""
    root = tk.Tk()
    app = NoiseAnalysisGUI(root)
    root.mainloop()


def run_command_line(args):
    """Run analysis from command line without GUI"""
    from tkinter import filedialog
    import tkinter as tk
    
    # Create a temporary root for file dialog
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Get file from user
    first_filepath = filedialog.askopenfilename(
        title="Select first data file",
        filetypes=[("Text files", "*.txt")]
    )
    
    if not first_filepath:
        print("No file selected. Exiting.")
        return
    
    try:
        # Initialize data processor
        processor = NoiseDataProcessor()
        
        # Find and process files
        files_to_process, selected_timestamp = processor.find_chronological_files(first_filepath)
        
        print(f"Starting with selected file: {os.path.basename(first_filepath)}")
        print(f"Selected file timestamp: {selected_timestamp}")
        print(f"Total files to process: {len(files_to_process)}")
        
        # Process files
        processor.process_files(files_to_process)
        
        # Get statistics
        stats = processor.get_statistics()
        
        # Print results
        print("\n" + "="*50)
        print("ANALYSIS RESULTS")
        print("="*50)
        print(f"Main Channel:")
        print(f"  Mean Noise: {stats['main_mean']:.3f}")
        print(f"  Max Noise:  {stats['main_max']:.3f}")
        print(f"  Intervals:  {stats['main_count']}")
        print(f"\nReference Channel:")
        print(f"  Mean Noise: {stats['ref_mean']:.3f}")
        print(f"  Max Noise:  {stats['ref_max']:.3f}")
        print(f"  Intervals:  {stats['ref_count']}")
        
        # Export CSV
        output_directory = os.path.dirname(first_filepath)
        success, message = processor.export_csv(output_directory, stats)
        if success:
            print(f"\n✓ {message}")
        else:
            print(f"\n✗ Export failed: {message}")
        
        # Handle high noise intervals if requested
        if args.show_high_noise_intervals or args.noise_threshold:
            threshold = args.noise_threshold if args.noise_threshold else None
            n_intervals = args.n_intervals if args.n_intervals else 0
            
            if threshold is None and n_intervals == 0:
                n_intervals = 5  # Default to top 5
            
            sorted_groups = processor.get_high_noise_intervals(
                n_intervals=n_intervals, 
                noise_threshold=threshold
            )
            
            if sorted_groups:
                print(f"\n" + "="*50)
                if threshold:
                    print(f"HIGH NOISE INTERVALS ABOVE {threshold}")
                else:
                    print(f"TOP {len(sorted_groups)} HIGH NOISE INTERVALS")
                print("="*50)
                
                for i, group in enumerate(sorted_groups, 1):
                    start_min = group['start_time'] / 60.0
                    end_min = group['end_time'] / 60.0
                    print(f"{i:2d}. Time: {start_min:.1f} - {end_min:.1f} min ({group['filename']})")
                    
                    if group['main_noise'] is not None:
                        print(f"    Main Channel: {group['main_noise']:.3f}")
                    if group['ref_noise'] is not None:
                        print(f"    Reference Channel: {group['ref_noise']:.3f}")
                    print()
            else:
                print(f"\nNo high noise intervals found.")
        
        print("\nAnalysis complete!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    finally:
        root.destroy()
    
    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=f'{APP_NAME} v{APP_VERSION}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ASTMnoise_modular.py                     # Launch GUI
  python ASTMnoise_modular.py --cli               # Command line mode
  python ASTMnoise_modular.py --cli --intervals   # CLI with high noise intervals
        """
    )
    
    parser.add_argument('--version', action='version', version=f'{APP_NAME} v{APP_VERSION}')
    parser.add_argument('--cli', action='store_true', 
                       help='Run in command-line mode (no GUI)')
    parser.add_argument('--show-complete-dataset', action='store_true',
                       help='Show complete dataset plot (GUI mode only)')
    parser.add_argument('--show-high-noise-intervals', '--intervals', action='store_true',
                       help='Show high noise intervals analysis')
    parser.add_argument('--n-intervals', type=int, default=0,
                       help='Number of highest noise intervals to show')
    parser.add_argument('--noise-threshold', type=float, 
                       help='Threshold value - show all intervals above this noise level')
    
    args = parser.parse_args()
    
    print(f"{APP_NAME} v{APP_VERSION}")
    print("="*50)
    
    if args.cli:
        # Command line mode
        print("Running in command-line mode...")
        return run_command_line(args)
    else:
        # GUI mode
        print("Launching GUI...")
        create_gui()
        return 0


if __name__ == "__main__":
    sys.exit(main())
