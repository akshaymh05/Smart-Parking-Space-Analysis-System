"""
config.py
---------
Central place for every setting used by the project.
If you want to change something (number of zones, colours, thresholds),
change it here and the whole project follows.

NOTE: All parking data in this project is SIMULATED. No real sensors are used.
"""

from pathlib import Path

# ----------------------------------------------------------------------------
# Folders and files
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
ASSETS_DIR = BASE_DIR / "assets"

DB_PATH = BASE_DIR / "smart_parking.db"
SAMPLE_CSV_PATH = DATA_DIR / "sample_parking_data.csv"
CSS_PATH = ASSETS_DIR / "style.css"

# ----------------------------------------------------------------------------
# Application text
# ----------------------------------------------------------------------------
APP_TITLE = "Smart Parking Space Analysis System"
APP_ICON = "🅿️"
SIMULATION_NOTICE = (
    "All parking data in this application is simulated. "
    "It is NOT connected to real sensors or real parking facilities."
)

# ----------------------------------------------------------------------------
# Parking lot layout: 4 zones x 10 spaces = 40 spaces
# ----------------------------------------------------------------------------
ZONES = ["A", "B", "C", "D"]
SPACES_PER_ZONE = 10

STATUS_AVAILABLE = "Available"
STATUS_OCCUPIED = "Occupied"

VEHICLE_TYPES = ["Car", "SUV", "Motorcycle", "Van"]
VEHICLE_WEIGHTS = [0.55, 0.20, 0.15, 0.10]   # how common each vehicle is (sums to 1)
NO_VEHICLE = "None"                          # used when a space is available
UNKNOWN_VEHICLE = "Unknown"                  # used by data cleaning

# ----------------------------------------------------------------------------
# Colours (green = available, red = occupied, blue = information)
# ----------------------------------------------------------------------------
COLOR_AVAILABLE = "#16a34a"
COLOR_OCCUPIED = "#dc2626"
COLOR_INFO = "#2563eb"
COLOR_WARNING = "#f59e0b"
ZONE_COLORS = {"A": "#2563eb", "B": "#7c3aed", "C": "#0891b2", "D": "#ea580c"}

# ----------------------------------------------------------------------------
# Simulation settings
# ----------------------------------------------------------------------------
# Chance (per update) that a space "re-decides" if it is occupied or free.
ACTIVITY_LEVELS = {"Low": 0.05, "Normal": 0.12, "High": 0.25}
DEFAULT_ACTIVITY = "Normal"

UPDATE_INTERVALS = [3, 5, 10, 15, 30]        # seconds between automatic updates
DEFAULT_INTERVAL = 5

# How busy the lot is at each hour of the day (0 = empty, 1 = very busy).
HOURLY_DEMAND = [
    0.10, 0.08, 0.06, 0.06, 0.08, 0.15,   # 00:00 - 05:59
    0.30, 0.55, 0.80, 0.92, 0.90, 0.85,   # 06:00 - 11:59
    0.80, 0.82, 0.78, 0.72, 0.75, 0.70,   # 12:00 - 17:59
    0.55, 0.40, 0.30, 0.22, 0.15, 0.12,   # 18:00 - 23:59
]
# Some zones are more popular (A is closest to the entrance, D is farthest).
ZONE_POPULARITY = {"A": 1.15, "B": 1.00, "C": 0.85, "D": 0.65}
WEEKEND_FACTOR = 0.80          # weekends are quieter
MIN_OCCUPANCY_PROB = 0.03
MAX_OCCUPANCY_PROB = 0.95

# Simulated history created for the first run (so charts have data to show)
AUTO_SEED_ON_FIRST_RUN = True
SEED_DAYS = 7
SEED_CHANGE_RATE = 0.60        # how much the lot changes between two hourly snapshots
RANDOM_SEED = 42

# To stop the database growing forever, only the newest live snapshots are kept.
# One snapshot = 40 rows (one per parking space).
MAX_LIVE_SNAPSHOTS = 2000

# ----------------------------------------------------------------------------
# Occupancy levels (used by the Decision Tree and by availability messages)
# ----------------------------------------------------------------------------
LOW_MAX = 40       # below 40%  -> Low
MEDIUM_MAX = 70    # 40% to <70% -> Medium, 70% and above -> High
BUSY_MAX = 90      # used for the availability message only
LEVELS = ["Low", "Medium", "High"]

# ----------------------------------------------------------------------------
# Minimum data needed before we run the data-mining algorithms
# ----------------------------------------------------------------------------
MIN_SNAPSHOTS_ANALYTICS = 2    # history charts need at least 2 time points
MIN_SNAPSHOTS_KMEANS = 10      # K-Means zone profile needs 10+ snapshots
MIN_RECORDS_TREE = 60          # Decision Tree needs 60+ (hour, zone) records
MIN_RECORDS_OUTLIER = 30       # Outlier detection needs 30+ records per zone

# ----------------------------------------------------------------------------
# Sidebar history filter (hours back from now, None = everything)
# ----------------------------------------------------------------------------
TIME_WINDOWS = {
    "All history": None,
    "Last 1 hour": 1,
    "Last 24 hours": 24,
    "Last 7 days": 168,
}

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
