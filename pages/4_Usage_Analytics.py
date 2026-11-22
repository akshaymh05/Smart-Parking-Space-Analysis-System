"""
Page 4 - Usage Analytics
Uses the saved, timestamped history to show trends, usage patterns and peak periods.
The sidebar filters (Parking zone, History period) are applied here.
"""

import streamlit as st

import analytics
import config
import ui_helpers
import visualization

ui_helpers.page_header(
    "📈", "Usage Analytics",
    "Occupancy trends, usage patterns, peak periods and zone-wise usage from the recorded history.",
)

history = ui_helpers.load_history()
snapshots = analytics.snapshot_occupancy(history)

if history.empty:
    st.warning(
        "No history records match the current sidebar filters. "
        "Try **History period = All history**, or click **Generate simulated history** in the sidebar."
    )
    st.stop()

if len(snapshots) < config.MIN_SNAPSHOTS_ANALYTICS:
    st.info(
        f"Only {len(snapshots)} snapshot(s) found. Trend charts need at least "
        f"{config.MIN_SNAPSHOTS_ANALYTICS}. Let the simulation run, or generate simulated history in the sidebar."
    )
    st.stop()

zone_text = ui_helpers.selected_zone_letter()
st.caption(
    f"Showing {'Zone ' + zone_text if zone_text else 'all zones'} | "
    f"period: {st.session_state.get('filter_window', 'All history')} | "
    f"{len(snapshots)} snapshots | {snapshots['timestamp'].min()} to {snapshots['timestamp'].max()}"
)

ui_helpers.show_metric_cards(
    [
        ("Average Occupancy", f"{snapshots['occupancy_pct'].mean():.1f}%", "Over the selected history", "blue"),
        ("Highest Occupancy", f"{snapshots['occupancy_pct'].max():.1f}%", "Busiest moment", "red"),
        ("Lowest Occupancy", f"{snapshots['occupancy_pct'].min():.1f}%", "Quietest moment", "green"),
    ],
    per_row=3,
)

grouping = st.selectbox(
    "Time grouping for the trend charts",
    ["Auto", "Raw (every update)", "Hourly", "Daily"],
    key="usage_grouping",
    help="Hourly / Daily averages make long histories easier to read.",
)

tab_trends, tab_peaks, tab_zones, tab_vehicles = st.tabs(
    ["📉 Occupancy trends", "⏰ Peak periods", "🗺️ Zone-wise usage", "🚙 Vehicle types"]
)

# ---- Trends --------------------------------------------------------------------
with tab_trends:
    trend = analytics.resample_occupancy(snapshots, grouping)
    st.plotly_chart(
        visualization.trend_line(trend, "occupancy_pct", "Occupancy Trend", config.COLOR_INFO, "Occupancy (%)"),
        use_container_width=True,
    )
    st.plotly_chart(
        visualization.availability_area(trend, "available", "Availability Trend (free spaces)"),
        use_container_width=True,
    )

# ---- Peak periods --------------------------------------------------------------
with tab_peaks:
    pattern = analytics.hourly_pattern(history)
    peaks = analytics.peak_periods(pattern, top_n=5)
    if len(pattern) < 3:
        st.info("Peak-period analysis needs data from at least 3 different hours of the day.")
    else:
        peak_hours = set(pattern.sort_values("avg_occupancy", ascending=False).head(5)["hour"])
        st.plotly_chart(visualization.hourly_bar(pattern, peak_hours), use_container_width=True)

        left, right = st.columns([1, 2])
        with left:
            st.subheader("Top 5 peak hours")
            ui_helpers.show_table(peaks.rename(columns={
                "rank": "Rank", "time_window": "Time window",
                "avg_occupancy": "Avg occupancy %", "level": "Level"}))
        with right:
            matrix = analytics.weekday_hour_matrix(history)
            if not matrix.empty:
                st.plotly_chart(visualization.weekday_heatmap(matrix), use_container_width=True)

# ---- Zone usage ----------------------------------------------------------------
with tab_zones:
    usage = analytics.zone_usage(history)
    st.plotly_chart(visualization.zone_usage_bar(usage), use_container_width=True)
    ui_helpers.show_table(usage.drop(columns=["zone"]).rename(columns={
        "zone_label": "Zone", "avg_occupancy": "Average %",
        "peak_occupancy": "Peak %", "lowest_occupancy": "Lowest %"}))

    zone_trend = analytics.resample_occupancy(analytics.zone_snapshot_occupancy(history), grouping, by_zone=True)
    st.plotly_chart(visualization.zone_trend_lines(zone_trend), use_container_width=True)

# ---- Vehicle types -------------------------------------------------------------
with tab_vehicles:
    vehicles = analytics.vehicle_counts(history)
    if vehicles.empty:
        st.info("No occupied records in the selected history.")
    else:
        left, right = st.columns(2)
        with left:
            st.plotly_chart(visualization.vehicle_donut(vehicles), use_container_width=True)
        with right:
            ui_helpers.show_table(vehicles.rename(columns={"vehicle_type": "Vehicle type", "count": "Records"}))
