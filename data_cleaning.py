"""
data_cleaning.py
----------------
DATA WRANGLING module. Every function here does ONE clear job:

  1. standardize_column_names : "Space ID" -> "space_id"
  2. convert_data_types       : text -> datetime, trim spaces, fix capital letters
  3. clean_text_values        : "occupied " / "FREE" -> "Occupied" / "Available"
  4. handle_missing_values    : fill or remove empty cells
  5. validate_space_ids       : remove rows with impossible IDs such as "Z99"
  6. remove_duplicates        : same timestamp + same space -> keep one row
  7. create_features          : hour, weekday, weekend flag, time period ...
  8. filter_data              : choose zones / status / dates / time periods
  9. aggregate_occupancy      : group data and compute occupancy %

clean_pipeline() runs steps 1-7 in order and returns a small report.
"""

import re

import numpy as np
import pandas as pd

import config

REQUIRED_COLUMNS = ["timestamp", "space_id", "zone", "status", "vehicle_type"]

# Different spellings that all mean the same thing
STATUS_MAP = {
    "occupied": config.STATUS_OCCUPIED, "occ": config.STATUS_OCCUPIED,
    "busy": config.STATUS_OCCUPIED, "full": config.STATUS_OCCUPIED,
    "taken": config.STATUS_OCCUPIED, "1": config.STATUS_OCCUPIED,
    "true": config.STATUS_OCCUPIED,
    "available": config.STATUS_AVAILABLE, "avail": config.STATUS_AVAILABLE,
    "free": config.STATUS_AVAILABLE, "empty": config.STATUS_AVAILABLE,
    "vacant": config.STATUS_AVAILABLE, "0": config.STATUS_AVAILABLE,
    "false": config.STATUS_AVAILABLE,
}

# Space IDs look like A01 ... D10
SPACE_ID_PATTERN = re.compile(
    "^[" + "".join(config.ZONES) + "](0[1-9]|[1-9][0-9])$"
)


# ----------------------------------------------------------------------------
# Loading a CSV
# ----------------------------------------------------------------------------
def load_csv(file_or_path):
    """
    Read a CSV file. The text "None" is kept as text because in this project
    "None" means "no vehicle", not "missing".
    """
    return pd.read_csv(
        file_or_path,
        keep_default_na=False,
        na_values=["", "NA", "N/A", "NaN", "nan", "null", "NULL"],
    )


# ----------------------------------------------------------------------------
# Quality report (before cleaning)
# ----------------------------------------------------------------------------
def data_quality_report(df):
    """Missing values and data types for every column."""
    report = pd.DataFrame(
        {
            "column": df.columns,
            "data_type": [str(t) for t in df.dtypes],
            "missing_values": df.isna().sum().values,
        }
    )
    total = max(len(df), 1)
    report["missing_percent"] = (report["missing_values"] / total * 100).round(2)
    return report


def count_duplicates(df):
    """How many rows repeat the same (timestamp, space_id) pair."""
    df = standardize_column_names(df)
    if "timestamp" not in df.columns or "space_id" not in df.columns:
        return int(df.duplicated().sum())
    return int(df.duplicated(subset=["timestamp", "space_id"], keep="first").sum())


# ----------------------------------------------------------------------------
# Cleaning steps
# ----------------------------------------------------------------------------
def standardize_column_names(df):
    """Lower-case column names, trim spaces, and use underscores."""
    df = df.copy()
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    return df


def check_required_columns(df):
    """Raise a clear error if an important column is missing."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "These required columns are missing: " + ", ".join(missing)
            + ". Expected columns: " + ", ".join(REQUIRED_COLUMNS)
        )


def convert_data_types(df):
    """Convert timestamp to datetime and the other columns to clean text."""
    df = df.copy()

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", format="mixed")
    except (TypeError, ValueError):
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    for column in ["space_id", "zone", "status", "vehicle_type"]:
        df[column] = df[column].astype("string").str.strip()
    return df


def normalize_status(series):
    """Turn spellings such as 'free' or 'OCCUPIED ' into Available / Occupied."""
    return series.astype("string").str.strip().str.lower().map(STATUS_MAP)


def clean_text_values(df):
    """Fix capital letters and spellings in the text columns."""
    df = df.copy()
    df["space_id"] = df["space_id"].str.upper()

    zone = df["zone"].str.upper().str.replace("ZONE", "", regex=False).str.strip()
    df["zone"] = zone

    df["status"] = normalize_status(df["status"])
    df["vehicle_type"] = df["vehicle_type"].str.title()
    return df


def handle_missing_values(df, status_strategy="fill_mode"):
    """
    Deal with empty cells.
      timestamp / space_id missing -> row removed (we cannot place it in time/space)
      zone missing or invalid      -> taken from the first letter of space_id
      status missing               -> "fill_mode": most common status, or "drop": remove row
      vehicle_type missing         -> "None" if Available, "Unknown" if Occupied
    Returns (cleaned_df, details_text)
    """
    df = df.copy()
    notes = []

    before = len(df)
    df = df.dropna(subset=["timestamp", "space_id"])
    removed = before - len(df)
    if removed:
        notes.append(f"{removed} rows removed (missing/invalid timestamp or space_id)")

    # Zone: derive from the space_id letter
    zone_from_id = df["space_id"].str[0]
    bad_zone = df["zone"].isna() | ~df["zone"].isin(config.ZONES)
    if bad_zone.sum():
        df.loc[bad_zone, "zone"] = zone_from_id[bad_zone]
        notes.append(f"{int(bad_zone.sum())} zones filled from space_id")

    # Status
    missing_status = int(df["status"].isna().sum())
    if missing_status:
        if status_strategy == "drop":
            df = df.dropna(subset=["status"])
            notes.append(f"{missing_status} rows removed (missing status)")
        else:
            modes = df["status"].mode()
            fill_value = modes.iloc[0] if len(modes) else config.STATUS_AVAILABLE
            df["status"] = df["status"].fillna(fill_value)
            notes.append(f"{missing_status} missing status values filled with '{fill_value}' (mode)")

    # Vehicle type depends on the status
    vehicle_missing = df["vehicle_type"].isna()
    occupied = df["status"] == config.STATUS_OCCUPIED
    fill_unknown = vehicle_missing & occupied
    fill_none = vehicle_missing & ~occupied
    if vehicle_missing.sum():
        df.loc[fill_unknown, "vehicle_type"] = config.UNKNOWN_VEHICLE
        df.loc[fill_none, "vehicle_type"] = config.NO_VEHICLE
        notes.append(f"{int(vehicle_missing.sum())} missing vehicle types filled")

    # Consistency: an Available space cannot hold a vehicle
    wrong_available = (df["status"] == config.STATUS_AVAILABLE) & (df["vehicle_type"] != config.NO_VEHICLE)
    wrong_occupied = (df["status"] == config.STATUS_OCCUPIED) & (df["vehicle_type"] == config.NO_VEHICLE)
    if wrong_available.sum() or wrong_occupied.sum():
        df.loc[wrong_available, "vehicle_type"] = config.NO_VEHICLE
        df.loc[wrong_occupied, "vehicle_type"] = config.UNKNOWN_VEHICLE
        notes.append(f"{int(wrong_available.sum() + wrong_occupied.sum())} status/vehicle conflicts fixed")

    return df, "; ".join(notes) if notes else "No missing values found"


def validate_space_ids(df):
    """Keep only valid IDs (A01-D10). The zone is always taken from the ID."""
    df = df.copy()
    valid = df["space_id"].apply(lambda value: bool(SPACE_ID_PATTERN.match(str(value))))
    # also check the number is not above the allowed spaces per zone
    numbers = pd.to_numeric(df["space_id"].str[1:], errors="coerce")
    valid = valid & (numbers >= 1) & (numbers <= config.SPACES_PER_ZONE)
    removed = int((~valid).sum())
    df = df[valid].copy()
    df["zone"] = df["space_id"].str[0]
    return df, removed


def remove_duplicates(df):
    """Keep one row for each (timestamp, space_id) pair."""
    before = len(df)
    df = df.drop_duplicates(subset=["timestamp", "space_id"], keep="last")
    return df, before - len(df)


def create_features(df):
    """Add new helpful columns (feature creation)."""
    df = df.copy()
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["timestamp"].dt.hour
    df["day_name"] = df["timestamp"].dt.day_name()
    df["day_of_week"] = df["timestamp"].dt.dayofweek          # Monday = 0
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_occupied"] = (df["status"] == config.STATUS_OCCUPIED).astype(int)

    hour = df["hour"]
    df["time_period"] = np.select(
        [hour.between(6, 11), hour.between(12, 16), hour.between(17, 21)],
        ["Morning", "Afternoon", "Evening"],
        default="Night",
    )
    return df


# ----------------------------------------------------------------------------
# The full pipeline
# ----------------------------------------------------------------------------
def clean_pipeline(raw_df, status_strategy="fill_mode", drop_duplicates=True, drop_invalid_ids=True):
    """
    Run the whole cleaning process.
    Returns (clean_df, steps_df) where steps_df explains what each step did.
    Raises ValueError if the file does not have the required columns.
    """
    steps = []

    def log(step, before, after, details):
        steps.append({"step": step, "rows_before": before, "rows_after": after, "details": details})

    df = standardize_column_names(raw_df)
    log("1. Standardize column names", len(raw_df), len(df), "Columns: " + ", ".join(df.columns))

    check_required_columns(df)
    df = df[[c for c in df.columns if c in REQUIRED_COLUMNS or c == "source"]].copy()

    n = len(df)
    df = convert_data_types(df)
    bad_dates = int(df["timestamp"].isna().sum())
    log("2. Convert data types", n, len(df), f"timestamp -> datetime ({bad_dates} unreadable dates became empty); other columns -> text")

    n = len(df)
    df = clean_text_values(df)
    unknown_status = int(df["status"].isna().sum())
    log("3. Clean text values", n, len(df), f"Upper/lower case fixed, status spellings unified ({unknown_status} unreadable statuses left empty)")

    n = len(df)
    df, details = handle_missing_values(df, status_strategy)
    log("4. Handle missing values", n, len(df), details)

    n = len(df)
    if drop_invalid_ids:
        df, removed = validate_space_ids(df)
        log("5. Validate space IDs", n, len(df), f"{removed} rows with invalid space IDs removed")
    else:
        log("5. Validate space IDs", n, len(df), "Skipped")

    n = len(df)
    if drop_duplicates:
        df, removed = remove_duplicates(df)
        log("6. Remove duplicates", n, len(df), f"{removed} duplicate rows removed")
    else:
        log("6. Remove duplicates", n, len(df), "Skipped")

    n = len(df)
    df = create_features(df)
    log("7. Create features", n, len(df), "Added: date, hour, day_name, day_of_week, is_weekend, is_occupied, time_period")

    df = df.sort_values(["timestamp", "space_id"]).reset_index(drop=True)
    for column in ["space_id", "zone", "status", "vehicle_type"]:
        df[column] = df[column].astype("object")

    return df, pd.DataFrame(steps)


# ----------------------------------------------------------------------------
# Filtering and aggregation
# ----------------------------------------------------------------------------
def filter_data(df, zones=None, statuses=None, start_date=None, end_date=None, time_periods=None):
    """Filter a cleaned DataFrame. Empty/None filters are ignored."""
    result = df.copy()
    if zones:
        result = result[result["zone"].isin(zones)]
    if statuses:
        result = result[result["status"].isin(statuses)]
    if time_periods:
        result = result[result["time_period"].isin(time_periods)]
    if start_date is not None:
        result = result[result["timestamp"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        result = result[result["timestamp"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)]
    return result


def aggregate_occupancy(df, group_by):
    """
    Group the data and compute occupancy %.
    group_by can be a column name or a list, e.g. "zone" or ["zone", "time_period"].
    """
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby(group_by, as_index=False).agg(
        total_records=("is_occupied", "size"),
        occupied_records=("is_occupied", "sum"),
    )
    grouped["occupancy_pct"] = (grouped["occupied_records"] / grouped["total_records"] * 100).round(1)
    return grouped
