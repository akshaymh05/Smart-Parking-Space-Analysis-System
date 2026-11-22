"""
Page 3 - Zone Analysis
Compares the four parking zones using the CURRENT status.
"""

import streamlit as st

import analytics
import database
import ui_helpers
import visualization

ui_helpers.page_header(
    "🗺️", "Zone Analysis",
    "Occupied spaces, available spaces and occupancy percentage for every parking zone.",
)

if st.button("🔄 Refresh", key="zone_refresh"):
    st.rerun()

status_df = database.get_current_status()
zone_df = analytics.zone_summary(status_df)
most, most_pct, least, least_pct = analytics.most_and_least_occupied(zone_df)

ui_helpers.show_metric_cards(
    [
        ("Most Occupied Zone", most, f"{most_pct}% occupied", "red"),
        ("Least Occupied Zone", least, f"{least_pct}% occupied", "green"),
        ("Zones Analysed", len(zone_df), "Current snapshot", "blue"),
    ],
    per_row=3,
)

left, right = st.columns(2)
with left:
    st.plotly_chart(visualization.zone_stacked_bar(zone_df), use_container_width=True)
with right:
    st.plotly_chart(visualization.zone_percentage_bar(zone_df), use_container_width=True)

st.subheader("Zone-wise table")
table = zone_df.drop(columns=["zone"]).rename(
    columns={
        "zone_label": "Zone",
        "total_spaces": "Total spaces",
        "occupied": "Occupied",
        "available": "Available",
        "occupancy_pct": "Occupancy %",
    }
)
ui_helpers.show_table(
    table,
    column_config={
        "Occupancy %": st.column_config.ProgressColumn(
            "Occupancy %", min_value=0, max_value=100, format="%.1f%%"
        )
    },
)

# ---- Detail of the zone chosen in the sidebar ---------------------------------
st.subheader("Zone detail")
selected_zone = ui_helpers.selected_zone_letter()
if selected_zone is None:
    st.info("Choose a zone in the sidebar (**Parking zone**) to see its individual spaces and vehicle types.")
else:
    zone_spaces = status_df[status_df["zone"] == selected_zone]
    detail_left, detail_right = st.columns([2, 1])
    with detail_left:
        ui_helpers.show_table(zone_spaces)
    with detail_right:
        vehicles = analytics.vehicle_counts(zone_spaces)
        if vehicles.empty:
            st.write(f"Zone {selected_zone} has no parked vehicles right now.")
        else:
            st.plotly_chart(visualization.vehicle_donut(vehicles), use_container_width=True)
