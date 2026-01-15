"""
Utility functions for the ASTM Noise Analysis Tool
"""

import os
import datetime
from config import APP_VERSION

def get_timestamp():
    """Generate a timestamp string for file exports"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def get_parent_folder_name(filepath):
    """Extract parent folder name from a file path"""
    return os.path.basename(os.path.dirname(filepath)) if filepath else "ASTM"

def create_export_filename(base_name, extension=".png", include_timestamp=True):
    """Create a standardized export filename"""
    timestamp = f"_{get_timestamp()}" if include_timestamp else ""
    return f"{base_name}{timestamp}{extension}"

def validate_data_file(filepath):
    """Check if a file is a valid data file"""
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    if not filepath.endswith('.txt'):
        return False, "File must be a .txt file"
    
    try:
        # Try to read first few lines to validate format
        with open(filepath, 'r') as f:
            lines = f.readlines()
            if len(lines) < 3:
                return False, "File too short (needs at least header + data)"
            # Additional validation could be added here
        return True, "Valid data file"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def get_version_info():
    """Get version information for display"""
    return {
        'version': APP_VERSION,
        'build_date': '2025-07-15',
        'python_requirement': '3.8+'
    }
