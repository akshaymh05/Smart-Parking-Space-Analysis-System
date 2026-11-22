"""
parking_simulator.py
--------------------
Creates SIMULATED parking-sensor data. There are no real sensors.

How the simulation works (simple version)
  1. Every hour of the day has a "demand" (busy at 9-11 AM, quiet at night).
  2. Every zone has a popularity (Zone A is popular, Zone D is quiet).
  3. At each update, every parking space has a small chance to "re-decide":
        it becomes Occupied with probability = demand x zone popularity,
        otherwise it becomes Available.
  4. Spaces that do not re-decide keep their old status, so changes look gradual.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config
import database

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Core simulation maths
# ----------------------------------------------------------------------------
def target_probability(zone, hour, weekday):
    """Chance (0-1) that a space in `zone` is occupied at this hour/weekday."""
    demand = config.HOURLY_DEMAND[hour]
    probability = demand * config.ZONE_POPULARITY.get(zone, 1.0)
    if weekday >= 5:                      # Saturday = 5, Sunday = 6
        probability *= config.WEEKEND_FACTOR
    return float(min(max(probability, config.MIN_OCCUPANCY_PROB), config.MAX_OCCUPANCY_PROB))


def pick_vehicle(rng):
    """Choose a random vehicle type using the weights from config.py."""
    return str(rng.choice(config.VEHICLE_TYPES, p=config.VEHICLE_WEIGHTS))


def empty_state():
    """A DataFrame with all 40 spaces Available."""
    rows = [
        {
            "space_id": space_id,
            "zone": zone,
            "status": config.STATUS_AVAILABLE,
            "vehicle_type": config.NO_VEHICLE,
        }
        for space_id, zone in database.build_space_list()
    ]
    return pd.DataFrame(rows)


def simulate_step(current_df, when, change_rate, rng):
    """
    Produce the NEXT state of the parking lot.
      current_df  : DataFrame with space_id, zone, status, vehicle_type
      when        : datetime that decides the demand (hour + weekday)
      change_rate : chance (0-1) that one space re-decides at this step
      rng         : numpy random generator
    """
    new_df = current_df[["space_id", "zone", "status", "vehicle_type"]].copy().reset_index(drop=True)
    statuses = new_df["status"].tolist()
    vehicles = new_df["vehicle_type"].tolist()
    zones = new_df["zone"].tolist()

    for i in range(len(new_df)):
        if rng.random() >= change_rate:
            continue                                   # this space keeps its status

        probability = target_probability(zones[i], when.hour, when.weekday())
        if rng.random() < probability:
            if statuses[i] != config.STATUS_OCCUPIED:  # a new vehicle arrives
                statuses[i] = config.STATUS_OCCUPIED
                vehicles[i] = pick_vehicle(rng)
        else:                                          # the space becomes free
            statuses[i] = config.STATUS_AVAILABLE
            vehicles[i] = config.NO_VEHICLE

    new_df["status"] = statuses
    new_df["vehicle_type"] = vehicles
    return new_df


# ----------------------------------------------------------------------------
# Live updates
# ----------------------------------------------------------------------------
def run_update(force=False):
    """
    Move the live simulation one step forward and save it in the database.

    force=False : used by the automatic timer. Does nothing when the simulation
                  is paused or when the last update was too recent. This is what
                  stops duplicate records when Streamlit re-runs the page.
    force=True  : used by the "Update now" button (works even when paused).

    Returns True if a new snapshot was saved.
    """
    try:
        now = datetime.now()

        if not force:
            if database.get_setting("paused", "0") == "1":
                return False
            interval = int(database.get_setting("interval_seconds", config.DEFAULT_INTERVAL))
            last_update = database.get_setting("last_update")
            if last_update:
                last_time = datetime.strptime(last_update, database.TIME_FORMAT)
                if (now - last_time).total_seconds() < interval * 0.8:
                    return False

        activity = database.get_setting("activity", config.DEFAULT_ACTIVITY)
        change_rate = config.ACTIVITY_LEVELS.get(activity, config.ACTIVITY_LEVELS[config.DEFAULT_ACTIVITY])

        current = database.get_current_status()
        rng = np.random.default_rng()
        new_state = simulate_step(current, now, change_rate, rng)

        saved_rows = database.save_snapshot(
            new_state, timestamp=now.strftime(database.TIME_FORMAT), source="live_simulation"
        )
        if saved_rows > 0:
            database.prune_live_history()
        return saved_rows > 0

    except Exception as error:   # keep the app alive even if the database is busy
        logger.warning("Simulation update failed: %s", error)
        return False


# ----------------------------------------------------------------------------
# Simulated history (backfill)
# ----------------------------------------------------------------------------
def generate_history(days=None):
    """
    Create `days` days of hourly SIMULATED history ending at the last full hour.
    These rows are marked source = 'simulated_backfill' so they are never
    confused with live updates. Running it twice does not create duplicates.
    Returns the number of rows inserted.
    """
    days = days or config.SEED_DAYS
    rng = np.random.default_rng(config.RANDOM_SEED)

    end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=days)

    state = empty_state()
    for _ in range(6):                                   # warm-up steps (not saved)
        state = simulate_step(state, start_time, config.SEED_CHANGE_RATE, rng)

    frames = []
    current_time = start_time
    while current_time < end_time:
        state = simulate_step(state, current_time, config.SEED_CHANGE_RATE, rng)
        snapshot = state.copy()
        snapshot["timestamp"] = current_time
        frames.append(snapshot)
        current_time += timedelta(hours=1)

    history_df = pd.concat(frames, ignore_index=True)
    return database.insert_history_rows(history_df, source="simulated_backfill")


# ----------------------------------------------------------------------------
# Start-up and reset
# ----------------------------------------------------------------------------
def ensure_initialized(auto_seed=None):
    """
    Make sure the database, the 40 spaces and a first snapshot exist.
    On the very first run it also creates the simulated history.
    Safe to call many times.
    """
    if auto_seed is None:
        auto_seed = config.AUTO_SEED_ON_FIRST_RUN

    database.init_database()
    snapshots, _ = database.get_history_counts()
    if snapshots > 0:
        return

    if auto_seed:
        generate_history()

    rng = np.random.default_rng()
    first_state = simulate_step(empty_state(), datetime.now(), 1.0, rng)
    database.save_snapshot(first_state, source="live_simulation")


def reset_simulation(reseed=True):
    """Admin action: wipe history, set every space Available, and start again."""
    database.init_database()
    database.reset_all()
    ensure_initialized(auto_seed=reseed)
