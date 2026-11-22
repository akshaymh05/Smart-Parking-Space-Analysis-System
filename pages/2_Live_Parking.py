"""
Page 2 - Live Parking
Shows all 40 parking spaces. Green = available, red = occupied.
The grid updates automatically (default every 5 seconds). You can also press
"Update now", pause the simulation, or change the speed in the sidebar.
"""

import pandas as pd
import streamlit as st

import config
import database
import parking_simulator
import ui_helpers
import visualization

ui_helpers.page_header(
    "🚗", "Live Parking",
    "Simulated parking-sensor view. Green = available, red = occupied.",
)

# ---- Controls (these buttons are outside the auto-refreshing part) -----------
paused = database.get_setting("paused", "0") == "1"
col_update, col_pause, col_resume, col_info = st.columns([1, 1, 1, 3])

if col_update.button("🔄 Update now", key="live_update", use_container_width=True):
    if parking_simulator.run_update(force=True):
        st.toast("Parking status updated")
    else:
        st.toast("Please wait one second and try again")

col_pause.button("⏸ Pause", key="live_pause", on_click=ui_helpers.set_paused, args=(True,),
                 disabled=paused, use_container_width=True)
col_resume.button("▶ Resume", key="live_resume", on_click=ui_helpers.set_paused, args=(False,),
                  disabled=not paused, use_container_width=True)
col_info.caption("Change the activity level and update interval in the sidebar (Admin Controls).")


def recent_changes():
    """Compare the two newest snapshots and list the spaces that changed."""
    latest = database.get_latest_snapshots(2)
    stamps = sorted(latest["timestamp"].unique())
    if len(stamps) < 2:
        return pd.DataFrame()
    before = latest[latest["timestamp"] == stamps[-2]].set_index("space_id")
    after = latest[latest["timestamp"] == stamps[-1]].set_index("space_id")
    changed = after[after["status"] != before["status"]].copy()
    changed["previous_status"] = before.loc[changed.index, "status"]
    changed = changed.reset_index()[["space_id", "zone", "previous_status", "status", "vehicle_type"]]
    return changed.rename(columns={"status": "new_status"})


def render_live():
    status_df = database.get_current_status()
    selected_zone = ui_helpers.selected_zone_letter()
    zones_to_show = [selected_zone] if selected_zone else config.ZONES

    st.markdown(ui_helpers.simulation_status_html(), unsafe_allow_html=True)

    st.markdown(
        '<span class="legend-item"><span class="legend-dot dot-green"></span>Available</span>'
        '<span class="legend-item"><span class="legend-dot dot-red"></span>Occupied</span>',
        unsafe_allow_html=True,
    )
    st.markdown(visualization.parking_grid_html(status_df, zones_to_show), unsafe_allow_html=True)

    occupied = int((status_df["status"] == config.STATUS_OCCUPIED).sum())
    st.caption(
        f"Whole lot: {occupied} occupied, {len(status_df) - occupied} available. "
        f"Zone filter: {'All Zones' if not selected_zone else 'Zone ' + selected_zone} (change it in the sidebar)."
    )

    with st.expander("Spaces that changed in the last update"):
        changes = recent_changes()
        if changes.empty:
            st.write("No changes yet, or only one snapshot exists.")
        else:
            ui_helpers.show_table(changes)

    with st.expander("Show data table"):
        table = status_df if not selected_zone else status_df[status_df["zone"] == selected_zone]
        ui_helpers.show_table(table)


ui_helpers.run_live(render_live)
