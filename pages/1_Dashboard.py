"""
Page 1 - Dashboard
Shows the main numbers of the parking lot in metric cards and three charts.
The panel refreshes automatically (every few seconds) while the simulation runs.
"""

import streamlit as st

import analytics
import database
import ui_helpers
import visualization

ui_helpers.page_header(
    "📊", "Dashboard",
    "Live overview of the simulated parking lot: spaces, occupancy and availability.",
)


def render_dashboard():
    status_df = database.get_current_status()
    summary = analytics.current_summary(status_df)

    st.markdown(ui_helpers.simulation_status_html(), unsafe_allow_html=True)

    cards = [
        ("Total Parking Spaces", summary["total_spaces"], "4 zones x 10 spaces", "blue"),
        ("Occupied Spaces", summary["occupied"], "Currently in use", "red"),
        ("Available Spaces", summary["available"], "Free right now", "green"),
        ("Occupancy", f"{summary['occupancy_pct']}%", "Occupied / total", "blue"),
        ("Parking Zones", summary["zone_count"], "Zone A, B, C, D", "blue"),
        ("Availability Status", summary["availability_message"], "Based on occupancy %",
         "green" if summary["occupancy_pct"] < 40 else "blue" if summary["occupancy_pct"] < 70
         else "amber" if summary["occupancy_pct"] < 90 else "red"),
    ]
    ui_helpers.show_metric_cards(cards, per_row=3)

    zone_df = analytics.zone_summary(status_df)
    left, middle, right = st.columns(3)
    with left:
        st.plotly_chart(visualization.occupancy_gauge(summary["occupancy_pct"]), use_container_width=True)
    with middle:
        st.plotly_chart(visualization.status_donut(summary["occupied"], summary["available"]),
                        use_container_width=True)
    with right:
        st.plotly_chart(visualization.zone_stacked_bar(zone_df), use_container_width=True)


ui_helpers.run_live(render_dashboard)

st.caption("Tip: open **Live Parking** to see every space, or use the sidebar to pause the simulation.")
