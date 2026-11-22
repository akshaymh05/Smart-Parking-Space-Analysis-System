"""
Page 6 - Data Wrangling
Shows the full cleaning process step by step:
  load -> inspect -> clean (missing values, duplicates, types) -> filter -> aggregate -> download

The sample CSV is deliberately messy so every cleaning step has something to fix.
"""

import pandas as pd
import streamlit as st

import analytics
import config
import data_cleaning
import database
import ui_helpers
import visualization

ui_helpers.page_header(
    "🧹", "Data Wrangling",
    "Missing values, duplicates, data types, cleaning, filtering, aggregation and feature creation.",
)

# ---- 1. Choose the data source ---------------------------------------------------
st.subheader("1. Choose the data")
source = st.radio(
    "Data source",
    ["Sample CSV (deliberately messy demo data)", "Database history (already clean)", "Upload my own CSV"],
    key="wrangle_source",
)

raw_df = None
try:
    if source.startswith("Sample"):
        raw_df = data_cleaning.load_csv(config.SAMPLE_CSV_PATH)
    elif source.startswith("Database"):
        raw_df = database.get_history()
    else:
        uploaded = st.file_uploader("Upload a CSV with columns: timestamp, space_id, zone, status, vehicle_type",
                                    type=["csv"], key="wrangle_upload")
        if uploaded is not None:
            raw_df = data_cleaning.load_csv(uploaded)
except FileNotFoundError:
    st.error("The sample file data/sample_parking_data.csv was not found.")
except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
    st.error(f"This file could not be read as a CSV: {error}")

if raw_df is None:
    st.info("Select or upload data to continue.")
    st.stop()
if raw_df.empty:
    st.warning("The selected data source has no rows.")
    st.stop()

# ---- 2. Inspect the raw data -------------------------------------------------------
st.subheader("2. Raw data (before cleaning)")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Rows", len(raw_df))
col_b.metric("Columns", raw_df.shape[1])
col_c.metric("Duplicate (timestamp, space) rows", data_cleaning.count_duplicates(raw_df))

left, right = st.columns([3, 2])
with left:
    st.markdown("**First 50 rows**")
    ui_helpers.show_table(raw_df.head(50), height=280)
with right:
    st.markdown("**Data quality report**")
    ui_helpers.show_table(data_cleaning.data_quality_report(raw_df), height=280)

# ---- 3. Clean ----------------------------------------------------------------------
st.subheader("3. Clean the data")
opt1, opt2, opt3 = st.columns(3)
status_choice = opt1.radio("Missing status values", ["Fill with most common status", "Remove those rows"],
                           key="wrangle_status")
remove_dupes = opt2.checkbox("Remove duplicate records", value=True, key="wrangle_dupes")
drop_invalid = opt3.checkbox("Remove invalid space IDs (not A01-D10)", value=True, key="wrangle_ids")

try:
    clean_df, steps_df = data_cleaning.clean_pipeline(
        raw_df,
        status_strategy="drop" if status_choice.startswith("Remove") else "fill_mode",
        drop_duplicates=remove_dupes,
        drop_invalid_ids=drop_invalid,
    )
except ValueError as error:
    st.error(str(error))
    st.stop()

if clean_df.empty:
    st.warning("No rows are left after cleaning. Check the data or the options above.")
    ui_helpers.show_table(steps_df)
    st.stop()

ui_helpers.show_metric_cards(
    [
        ("Rows before", len(raw_df), "Raw data", "blue"),
        ("Rows after", len(clean_df), "Cleaned data", "green"),
        ("Rows removed", len(raw_df) - len(clean_df), "Invalid or duplicate", "amber"),
    ],
    per_row=3,
)
st.markdown("**What every step did**")
ui_helpers.show_table(steps_df)

st.markdown("**Cleaned data (new feature columns at the right)**")
st.caption(f"Showing the first 500 of {len(clean_df)} rows. Missing values left: {int(clean_df.isna().sum().sum())}")
ui_helpers.show_table(clean_df.head(500), height=320)

# ---- 4. Filter ---------------------------------------------------------------------
st.subheader("4. Filter the cleaned data")
f1, f2, f3 = st.columns(3)
zone_filter = f1.multiselect("Zones", config.ZONES, key="wrangle_zones")
status_filter = f2.multiselect("Status", [config.STATUS_AVAILABLE, config.STATUS_OCCUPIED], key="wrangle_statuses")
period_filter = f3.multiselect("Time period", ["Morning", "Afternoon", "Evening", "Night"], key="wrangle_periods")

min_date = clean_df["timestamp"].min().date()
max_date = clean_df["timestamp"].max().date()
date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date,
                           max_value=max_date, key="wrangle_dates")
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = data_cleaning.filter_data(
    clean_df, zones=zone_filter, statuses=status_filter, time_periods=period_filter,
    start_date=start_date, end_date=end_date,
)
st.write(f"**{len(filtered)}** of {len(clean_df)} rows match the filters.")
ui_helpers.show_table(filtered.head(300), height=260)

# ---- 5. Aggregate ------------------------------------------------------------------
st.subheader("5. Aggregate (group) the data")
group_options = {
    "Zone": "zone",
    "Hour of day": "hour",
    "Date": "date",
    "Day of week": "day_name",
    "Time period": "time_period",
    "Zone and time period": ["zone", "time_period"],
}
group_choice = st.selectbox("Group by", list(group_options), key="wrangle_group")
aggregated = data_cleaning.aggregate_occupancy(filtered, group_options[group_choice])

if aggregated.empty:
    st.info("Nothing to aggregate with the current filters.")
else:
    ui_helpers.show_table(aggregated)
    x_column = group_options[group_choice] if isinstance(group_options[group_choice], str) else "zone"
    color_column = None if isinstance(group_options[group_choice], str) else "time_period"
    st.plotly_chart(
        visualization.simple_bar(aggregated, x_column, "occupancy_pct", f"Occupancy % by {group_choice}", color_column),
        use_container_width=True,
    )

# ---- 6. Download -------------------------------------------------------------------
st.subheader("6. Download")
st.download_button(
    "⬇️ Download cleaned data (CSV)",
    data=ui_helpers.to_csv_bytes(clean_df),
    file_name="cleaned_parking_data.csv",
    mime="text/csv",
    key="wrangle_download",
)
