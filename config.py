"""ASTM Noise Analysis Tool - Configuration and Constants
"""

__version__ = "3.1.0"

# Application metadata
APP_NAME = "ASTM Noise Analysis Tool"
APP_VERSION = __version__
APP_DESCRIPTION = "A Python tool for analyzing noise in lamp data according to ASTM standards"

# Default analysis parameters
DEFAULT_SUBSET_SIZE = 30  # seconds
DEFAULT_NOISE_THRESHOLD = 1200
DEFAULT_TIME_BUFFER = 10  # seconds padding around intervals
DEFAULT_MAX_INTERVALS = 120

# Window geometry
MAIN_WINDOW_SIZE = "650x500"
ASTM_PLOT_WINDOW_SIZE = "900x600"
COMPLETE_PLOT_WINDOW_SIZE = "900x600"
INTERVAL_WINDOW_SIZE = "900x700"
DETAIL_INTERVAL_WINDOW_SIZE = "600x700"

# File patterns
DATA_FILE_PATTERN = "*_*_DataCollection.txt"
EXPORT_DPI = 300

# Colors for plots
MAIN_CHANNEL_COLOR = 'blue'
REF_CHANNEL_COLOR = 'orange'
ASTM_LIMIT_COLOR = 'red'
ASTM_START_COLOR = 'green'
HIGH_NOISE_HIGHLIGHT_COLOR = 'red'
