"""
Page 7 - Reports
Download CSV reports and see summary statistics.
The sidebar filters (zone, history period) are applied to the history report.
"""

from datetime import datetime

import streamlit as st

import analytics
import config
import database
import ui_helpers

ui_helpers.page_header(
    "📄", "Reports",
    "Download the current status, the parking history and the zone analysis as CSV files.",
)

status_df = database.get_current_status()
history = ui_helpers.load_history()
zone_df = analytics.zone_summary(status_df)

# ---- Zone analysis report = current zone numbers + historical usage ---------------
zone_report = zone_df.drop(columns=["zone_label"]).copy()
usage = analytics.zone_usage(ui_helpers.load_history(apply_zone_filter=False))
if not usage.empty:
    zone_report = zone_report.merge(
        usage[["zone", "avg_occupancy", "peak_occupancy", "lowest_occupancy"]], on="zone", how="left"
    ).rename(columns={
        "avg_occupancy": "history_avg_occupancy_pct",
        "peak_occupancy": "history_peak_occupancy_pct",
        "lowest_occupancy": "history_lowest_occupancy_pct",
    })
zone_report = zone_report.rename(columns={"occupancy_pct": "current_occupancy_pct"})

# ---- Filter parking records --------------------------------------------------------
st.subheader("Filter the history records")
st.caption("The sidebar filters (Parking zone and History period) are applied as well.")
f1, f2 = st.columns(2)
status_filter = f1.multiselect("Status", [config.STATUS_AVAILABLE, config.STATUS_OCCUPIED], key="report_status")
vehicle_filter = f2.multiselect("Vehicle type", config.VEHICLE_TYPES + [config.NO_VEHICLE], key="report_vehicle")

report_history = history.copy()
if status_filter:
    report_history = report_history[report_history["status"].isin(status_filter)]
if vehicle_filter:
    report_history = report_history[report_history["vehicle_type"].isin(vehicle_filter)]

# ---- Downloads ---------------------------------------------------------------------
st.subheader("Downloads")
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Current parking status**")
    st.caption(f"{len(status_df)} rows")
    st.download_button("⬇️ Download current status", ui_helpers.to_csv_bytes(status_df),
                       file_name=f"current_status_{stamp}.csv", mime="text/csv", key="dl_status")
with col2:
    st.markdown("**Historical parking records**")
    st.caption(f"{len(report_history)} rows (after filters)")
    st.download_button("⬇️ Download history", ui_helpers.to_csv_bytes(report_history),
                       file_name=f"parking_history_{stamp}.csv", mime="text/csv", key="dl_history",
                       disabled=report_history.empty)
with col3:
    st.markdown("**Zone analysis**")
    st.caption(f"{len(zone_report)} zones")
    st.download_button("⬇️ Download zone analysis", ui_helpers.to_csv_bytes(zone_report),
                       file_name=f"zone_analysis_{stamp}.csv", mime="text/csv", key="dl_zone")

if st.button("💾 Also save copies in the project's reports/ folder", key="save_reports"):
    try:
        config.REPORTS_DIR.mkdir(exist_ok=True)
        status_df.to_csv(config.REPORTS_DIR / f"current_status_{stamp}.csv", index=False)
        zone_report.to_csv(config.REPORTS_DIR / f"zone_analysis_{stamp}.csv", index=False)
        if not report_history.empty:
            report_history.to_csv(config.REPORTS_DIR / f"parking_history_{stamp}.csv", index=False)
        st.success(f"Saved in: {config.REPORTS_DIR}")
    except OSError as error:
        st.error(f"Could not save the files: {error}")

# ---- Previews and statistics -------------------------------------------------------
st.subheader("Preview")
tab_status, tab_history, tab_zone = st.tabs(["Current status", "History records", "Zone analysis"])
with tab_status:
    ui_helpers.show_table(status_df, height=300)
with tab_history:
    if report_history.empty:
        st.info("No history records match the filters.")
    else:
        st.caption(f"First 300 of {len(report_history)} rows")
        ui_helpers.show_table(report_history.head(300), height=300)
with tab_zone:
    ui_helpers.show_table(zone_report)

st.subheader("Summary statistics")
if report_history.empty:
    st.info("Summary statistics need history records.")
else:
    left, right = st.columns([2, 3])
    with left:
        ui_helpers.show_table(analytics.summary_statistics(report_history))
    with right:
        snapshots = analytics.snapshot_occupancy(report_history)
        st.markdown("**Distribution of occupancy per snapshot**")
        described = snapshots[["occupied", "available", "occupancy_pct"]].describe().round(2)
        st.dataframe(described, use_container_width=True)
