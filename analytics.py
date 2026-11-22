"""
analytics.py
------------
Calculations used by the dashboard and the analysis pages.
Everything here takes a pandas DataFrame and returns numbers or DataFrames
(no Streamlit code and no charts, so it is easy to test).

Two kinds of input
  status_df  : current state of the spaces (space_id, zone, status, vehicle_type)
  history_df : timestamped history (timestamp, space_id, zone, status, vehicle_type)
"""

import pandas as pd

import config


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def zone_label(zone):
    """'A' -> 'Zone A'."""
    return f"Zone {zone}"


def availability_status(occupancy_pct):
    """Return (message, colour) that describes how full the parking lot is."""
    if occupancy_pct < config.LOW_MAX:
        return "Plenty of Space", config.COLOR_AVAILABLE
    if occupancy_pct < config.MEDIUM_MAX:
        return "Moderately Busy", config.COLOR_INFO
    if occupancy_pct < config.BUSY_MAX:
        return "Filling Up", config.COLOR_WARNING
    if occupancy_pct < 100:
        return "Almost Full", config.COLOR_OCCUPIED
    return "Full", config.COLOR_OCCUPIED


def _with_flag(df):
    """Copy of df with an is_occupied column (1 = Occupied, 0 = Available)."""
    result = df.copy()
    result["is_occupied"] = (result["status"] == config.STATUS_OCCUPIED).astype(int)
    return result


# ----------------------------------------------------------------------------
# Current state
# ----------------------------------------------------------------------------
def current_summary(status_df):
    """Numbers shown on the dashboard cards."""
    total = len(status_df)
    occupied = int((status_df["status"] == config.STATUS_OCCUPIED).sum())
    available = total - occupied
    percentage = round(occupied / total * 100, 1) if total else 0.0
    message, color = availability_status(percentage)
    return {
        "total_spaces": total,
        "occupied": occupied,
        "available": available,
        "occupancy_pct": percentage,
        "zone_count": int(status_df["zone"].nunique()) if total else 0,
        "availability_message": message,
        "availability_color": color,
    }


def zone_summary(status_df):
    """One row per zone: total, occupied, available, occupancy %."""
    df = _with_flag(status_df)
    grouped = df.groupby("zone").agg(
        total_spaces=("space_id", "count"),
        occupied=("is_occupied", "sum"),
    ).reset_index()
    grouped["available"] = grouped["total_spaces"] - grouped["occupied"]
    grouped["occupancy_pct"] = (grouped["occupied"] / grouped["total_spaces"] * 100).round(1)
    grouped["zone_label"] = grouped["zone"].map(zone_label)
    return grouped[["zone", "zone_label", "total_spaces", "occupied", "available", "occupancy_pct"]]


def most_and_least_occupied(zone_df):
    """Return (most_names, most_pct, least_names, least_pct). Ties are joined with commas."""
    if zone_df.empty:
        return "-", 0.0, "-", 0.0
    highest = zone_df["occupancy_pct"].max()
    lowest = zone_df["occupancy_pct"].min()
    most = ", ".join(zone_df.loc[zone_df["occupancy_pct"] == highest, "zone_label"])
    least = ", ".join(zone_df.loc[zone_df["occupancy_pct"] == lowest, "zone_label"])
    return most, float(highest), least, float(lowest)


def vehicle_counts(df):
    """Count occupied spaces by vehicle type (works for current or history data)."""
    occupied = df[df["status"] == config.STATUS_OCCUPIED]
    counts = occupied.groupby("vehicle_type").size().reset_index(name="count")
    return counts.sort_values("count", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------
# History: occupancy per time point
# ----------------------------------------------------------------------------
SNAPSHOT_COLUMNS = ["timestamp", "occupied", "total", "available", "occupancy_pct"]


def snapshot_occupancy(history_df):
    """Total occupancy for every timestamp (all spaces in history_df together)."""
    if history_df.empty:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    df = _with_flag(history_df)
    grouped = df.groupby("timestamp").agg(
        occupied=("is_occupied", "sum"),
        total=("is_occupied", "size"),
    ).reset_index()
    grouped["available"] = grouped["total"] - grouped["occupied"]
    grouped["occupancy_pct"] = (grouped["occupied"] / grouped["total"] * 100).round(2)
    return grouped


def zone_snapshot_occupancy(history_df):
    """Occupancy for every (timestamp, zone) pair."""
    columns = ["timestamp", "zone", "occupied", "total", "available", "occupancy_pct", "zone_label"]
    if history_df.empty:
        return pd.DataFrame(columns=columns)
    df = _with_flag(history_df)
    grouped = df.groupby(["timestamp", "zone"]).agg(
        occupied=("is_occupied", "sum"),
        total=("is_occupied", "size"),
    ).reset_index()
    grouped["available"] = grouped["total"] - grouped["occupied"]
    grouped["occupancy_pct"] = (grouped["occupied"] / grouped["total"] * 100).round(2)
    grouped["zone_label"] = grouped["zone"].map(zone_label)
    return grouped


def choose_frequency(timestamps, option="Auto"):
    """Translate the 'time grouping' choice into a pandas frequency (None = raw)."""
    if option.startswith("Raw"):
        return None
    if option == "Hourly":
        return "h"
    if option == "Daily":
        return "D"
    span = timestamps.max() - timestamps.min()          # Auto
    if span <= pd.Timedelta(hours=6):
        return None
    if span <= pd.Timedelta(days=14):
        return "h"
    return "D"


def resample_occupancy(df, option="Auto", by_zone=False):
    """
    Average the occupancy over larger time blocks (hourly / daily) so that
    charts stay readable when there are thousands of snapshots.
    """
    if df.empty:
        return df
    frequency = choose_frequency(df["timestamp"], option)
    if frequency is None:
        return df.copy()

    result = df.copy()
    result["timestamp"] = result["timestamp"].dt.floor(frequency)
    keys = ["timestamp", "zone"] if by_zone else ["timestamp"]
    result = result.groupby(keys, as_index=False).agg(
        occupied=("occupied", "mean"),
        available=("available", "mean"),
        occupancy_pct=("occupancy_pct", "mean"),
    )
    for column in ["occupied", "available", "occupancy_pct"]:
        result[column] = result[column].round(2)
    if by_zone:
        result["zone_label"] = result["zone"].map(zone_label)
    return result


# ----------------------------------------------------------------------------
# History: usage patterns and peak periods
# ----------------------------------------------------------------------------
def _hourly_blocks(history_df):
    """Average occupancy for every clock hour that exists in the history."""
    snapshots = snapshot_occupancy(history_df)
    if snapshots.empty:
        return pd.DataFrame(columns=["hour_bucket", "occupancy_pct"])
    snapshots["hour_bucket"] = snapshots["timestamp"].dt.floor("h")
    return snapshots.groupby("hour_bucket", as_index=False)["occupancy_pct"].mean()


def hourly_pattern(history_df):
    """Average occupancy for each hour of the day (0-23)."""
    blocks = _hourly_blocks(history_df)
    if blocks.empty:
        return pd.DataFrame(columns=["hour", "avg_occupancy", "hours_observed", "hour_label"])
    blocks["hour"] = blocks["hour_bucket"].dt.hour
    pattern = blocks.groupby("hour", as_index=False).agg(
        avg_occupancy=("occupancy_pct", "mean"),
        hours_observed=("occupancy_pct", "size"),
    )
    pattern["avg_occupancy"] = pattern["avg_occupancy"].round(1)
    pattern["hour_label"] = pattern["hour"].map(lambda h: f"{h:02d}:00")
    return pattern


def peak_periods(pattern_df, top_n=5):
    """The `top_n` busiest hours of the day."""
    if pattern_df.empty:
        return pd.DataFrame(columns=["rank", "time_window", "avg_occupancy", "level"])
    top = pattern_df.sort_values("avg_occupancy", ascending=False).head(top_n).copy()
    top["time_window"] = top["hour"].map(lambda h: f"{h:02d}:00 - {(h + 1) % 24:02d}:00")
    top["level"] = top["avg_occupancy"].map(lambda value: availability_status(value)[0])
    top.insert(0, "rank", range(1, len(top) + 1))
    return top[["rank", "time_window", "avg_occupancy", "level"]].reset_index(drop=True)


def weekday_hour_matrix(history_df):
    """Table: rows = day name, columns = hour, values = average occupancy %."""
    blocks = _hourly_blocks(history_df)
    if blocks.empty:
        return pd.DataFrame()
    blocks["day_name"] = blocks["hour_bucket"].dt.day_name()
    blocks["hour"] = blocks["hour_bucket"].dt.hour
    matrix = blocks.pivot_table(index="day_name", columns="hour", values="occupancy_pct", aggfunc="mean")
    days_present = [day for day in config.DAY_ORDER if day in matrix.index]
    return matrix.reindex(days_present).round(1)


def zone_usage(history_df):
    """Average, highest and lowest occupancy of each zone over the whole history."""
    zone_data = zone_snapshot_occupancy(history_df)
    if zone_data.empty:
        return pd.DataFrame(columns=["zone", "zone_label", "avg_occupancy", "peak_occupancy", "lowest_occupancy"])
    usage = zone_data.groupby("zone", as_index=False).agg(
        avg_occupancy=("occupancy_pct", "mean"),
        peak_occupancy=("occupancy_pct", "max"),
        lowest_occupancy=("occupancy_pct", "min"),
    )
    usage["zone_label"] = usage["zone"].map(zone_label)
    usage = usage.round(1)
    return usage[["zone", "zone_label", "avg_occupancy", "peak_occupancy", "lowest_occupancy"]]


def summary_statistics(history_df):
    """A small 'metric / value' table with the main numbers of the history."""
    if history_df.empty:
        return pd.DataFrame({"metric": ["History records"], "value": ["0"]})

    snapshots = snapshot_occupancy(history_df)
    pattern = hourly_pattern(history_df)
    usage = zone_usage(history_df)

    rows = [
        ("Number of snapshots", f"{len(snapshots)}"),
        ("Number of history records", f"{len(history_df)}"),
        ("First record", str(snapshots["timestamp"].min())),
        ("Last record", str(snapshots["timestamp"].max())),
        ("Average occupancy (%)", f"{snapshots['occupancy_pct'].mean():.1f}"),
        ("Highest occupancy (%)", f"{snapshots['occupancy_pct'].max():.1f}"),
        ("Lowest occupancy (%)", f"{snapshots['occupancy_pct'].min():.1f}"),
    ]
    if not pattern.empty:
        busiest = pattern.loc[pattern["avg_occupancy"].idxmax()]
        quietest = pattern.loc[pattern["avg_occupancy"].idxmin()]
        rows.append(("Busiest hour of day", f"{busiest['hour_label']} ({busiest['avg_occupancy']}%)"))
        rows.append(("Quietest hour of day", f"{quietest['hour_label']} ({quietest['avg_occupancy']}%)"))
    if not usage.empty:
        top = usage.loc[usage["avg_occupancy"].idxmax()]
        low = usage.loc[usage["avg_occupancy"].idxmin()]
        rows.append(("Most used zone", f"{top['zone_label']} ({top['avg_occupancy']}%)"))
        rows.append(("Least used zone", f"{low['zone_label']} ({low['avg_occupancy']}%)"))
    return pd.DataFrame(rows, columns=["metric", "value"])
