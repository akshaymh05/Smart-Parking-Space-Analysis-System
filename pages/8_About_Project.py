"""
Page 8 - About Project
Explains the project, the technologies, the modules and the database.
"""

import pandas as pd
import streamlit as st

import config
import ui_helpers

ui_helpers.page_header(
    "ℹ️", "About Project",
    "Smart Parking Space Analysis System using Python and Streamlit - a Data Mining and Data Wrangling mini-project.",
)

st.warning(config.SIMULATION_NOTICE)

st.subheader("What does this project do?")
st.write(
    "It simulates a parking lot with 40 spaces in 4 zones (A, B, C, D), records every change in a "
    "SQLite database, and then analyses the recorded history with data wrangling, analytics and "
    "data-mining algorithms. The results are shown on an interactive dashboard."
)

st.subheader("How the data is created")
st.markdown(
    """
* Every hour of the day has a *demand* value (busy around 9-11 AM, quiet at night) and every zone has a *popularity* (Zone A highest, Zone D lowest).
* At each update, every space may re-decide: it becomes **Occupied** with a probability based on the hour and zone, otherwise **Available**.
* On the first run the app also creates 7 days of **hourly simulated history** (marked `simulated_backfill`) so the charts have data immediately.
* Live updates are stored as `live_simulation` and only the newest 2000 live snapshots are kept.
    """
)

st.subheader("Technology stack")
st.dataframe(
    pd.DataFrame(
        {
            "Purpose": ["Language", "Web interface", "Data processing", "Charts", "Machine learning", "Database", "Data storage", "Editor"],
            "Technology": ["Python", "Streamlit", "Pandas, NumPy", "Plotly", "Scikit-learn", "SQLite (smart_parking.db)", "CSV files", "VS Code"],
        }
    ),
    use_container_width=True, hide_index=True,
)

st.subheader("Modules")
st.dataframe(
    pd.DataFrame(
        {
            "Page": ["Dashboard", "Live Parking", "Zone Analysis", "Usage Analytics",
                     "Data Mining", "Data Wrangling", "Reports", "Admin Controls (sidebar)"],
            "What it does": [
                "Metric cards, gauge and charts for the whole lot",
                "40 coloured spaces, automatic updates, manual update, pause / resume",
                "Occupied, available and occupancy % per zone, most / least occupied zone",
                "Trends, usage patterns, peak hours and zone-wise usage from history",
                "K-Means, Decision Tree and outlier detection with data checks",
                "Missing values, duplicates, types, cleaning, filtering, aggregation, features",
                "CSV downloads and summary statistics",
                "Pause, speed, activity, zone filter, history period, reset",
            ],
        }
    ),
    use_container_width=True, hide_index=True,
)

st.subheader("Database design (SQLite)")
left, right = st.columns(2)
with left:
    st.markdown("**parking_spaces** - current state")
    st.dataframe(
        pd.DataFrame({"Column": ["space_id (PK)", "zone", "status", "vehicle_type", "last_updated"],
                      "Type": ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT"]}),
        use_container_width=True, hide_index=True,
    )
with right:
    st.markdown("**parking_history** - one row per space per snapshot")
    st.dataframe(
        pd.DataFrame({"Column": ["record_id (PK)", "timestamp", "space_id", "zone", "status", "vehicle_type", "source"],
                      "Type": ["INTEGER", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT"]}),
        use_container_width=True, hide_index=True,
    )
st.caption("A UNIQUE (timestamp, space_id) rule prevents duplicate history records. A third table, app_settings, stores pause / speed / activity.")

st.subheader("Algorithms in one line each")
st.markdown(
    """
* **K-Means:** groups zones with similar average and peak occupancy.
* **Decision Tree:** learns to predict Low / Medium / High occupancy from hour, weekday and zone.
* **Outlier detection:** flags occupancy values far outside the normal range of a zone (IQR or Z-score).
    """
)

st.subheader("Limitations")
st.markdown(
    """
* The data is simulated, so the discovered patterns come from the simulation rules, not from real drivers.
* Simulation only advances while the app is open in a browser page that refreshes automatically.
* With only 4 zones, K-Means is a demonstration of the technique rather than a strong statistical result.
    """
)
