"""
ui_helpers.py
-------------
Small Streamlit helpers shared by all pages:
  - load_css()          : applies assets/style.css
  - page_header()       : consistent page title + description
  - show_metric_cards() : coloured metric cards
  - run_live()          : makes a part of a page refresh automatically
  - render_sidebar()    : the Admin Controls (pause, speed, zone filter, reset ...)
  - load_history()      : reads history using the sidebar filters
"""

from datetime import datetime, timedelta

import streamlit as st

import config
import database
import parking_simulator


# ----------------------------------------------------------------------------
# Look and feel
# ----------------------------------------------------------------------------
def load_css():
    """Read assets/style.css and inject it into the page."""
    try:
        css = config.CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except OSError:
        pass   # the app still works without the extra styling


def page_header(icon, title, description):
    """Big title with a short description under it."""
    st.markdown(
        f'<div class="page-header"><h1>{icon} {title}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def metric_card(label, value, caption="", color="blue"):
    """HTML for one metric card. color: blue / green / red / amber."""
    return (
        f'<div class="metric-card {color}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-caption">{caption}</div></div>'
    )


def show_metric_cards(cards, per_row=3):
    """cards = list of (label, value, caption, color) tuples."""
    for start in range(0, len(cards), per_row):
        columns = st.columns(per_row)
        for column, card in zip(columns, cards[start:start + per_row]):
            column.markdown(metric_card(*card), unsafe_allow_html=True)


def show_table(df, height=None, **kwargs):
    """Show a DataFrame full-width without the index column."""
    st.dataframe(df, use_container_width=True, hide_index=True, height=height, **kwargs)


def to_csv_bytes(df):
    """DataFrame -> CSV bytes for st.download_button."""
    return df.to_csv(index=False).encode("utf-8")


def simulation_status_html():
    """Small coloured bar that says if the simulation is running or paused."""
    paused = database.get_setting("paused", "0") == "1"
    interval = database.get_setting("interval_seconds", str(config.DEFAULT_INTERVAL))
    activity = database.get_setting("activity", config.DEFAULT_ACTIVITY)
    last_update = database.get_setting("last_update", "not yet")

    if paused:
        state = '<span class="pill pill-red">⏸ Paused</span>'
    else:
        state = f'<span class="pill pill-green">🟢 Running - every {interval}s</span>'

    return (
        f'<div class="status-bar">{state}'
        f'<span class="pill pill-blue">Activity: {activity}</span>'
        f'<span class="pill pill-blue">Last updated: {last_update}</span>'
        f'<span class="pill pill-gray">Simulated data</span></div>'
    )


# ----------------------------------------------------------------------------
# Automatic refresh
# ----------------------------------------------------------------------------
def run_live(render_function):
    """
    Show `render_function()` in a "fragment" that re-runs every few seconds.
    Before each re-run it asks the simulator for ONE new update. The simulator
    itself refuses to update when paused or when the last update is too recent,
    so re-running the page never creates duplicate history records.
    """
    paused = database.get_setting("paused", "0") == "1"
    interval = int(database.get_setting("interval_seconds", str(config.DEFAULT_INTERVAL)))
    run_every = None if paused else interval

    @st.fragment(run_every=run_every)
    def live_panel():
        parking_simulator.run_update()
        render_function()

    live_panel()


def set_paused(value):
    """Callback for the Pause / Resume buttons."""
    database.set_setting("paused", "1" if value else "0")


# ----------------------------------------------------------------------------
# Sidebar filters used by the analysis pages
# ----------------------------------------------------------------------------
def selected_zone_letter():
    """Return 'A'..'D' if a zone is selected in the sidebar, otherwise None."""
    choice = st.session_state.get("filter_zone", "All Zones")
    if choice == "All Zones":
        return None
    return choice.replace("Zone ", "")


def load_history(apply_zone_filter=True):
    """Read history from the database using the sidebar time window (and zone)."""
    hours = config.TIME_WINDOWS.get(st.session_state.get("filter_window", "All history"))
    start = datetime.now() - timedelta(hours=hours) if hours else None
    zone = selected_zone_letter() if apply_zone_filter else None
    return database.get_history(start=start, zones=[zone] if zone else None)


# ----------------------------------------------------------------------------
# Sidebar (Admin Controls)
# ----------------------------------------------------------------------------
def _save_activity():
    database.set_setting("activity", st.session_state["sb_activity"])


def _save_interval():
    database.set_setting("interval_seconds", st.session_state["sb_interval"])


def _reset_simulation():
    reseed = st.session_state.get("sb_reseed", True)
    parking_simulator.reset_simulation(reseed=reseed)
    st.session_state["sb_confirm_reset"] = False
    st.session_state["sidebar_message"] = "Simulation reset. History was cleared."


def _generate_history():
    inserted = parking_simulator.generate_history()
    if inserted:
        st.session_state["sidebar_message"] = f"Added {inserted} simulated history rows."
    else:
        st.session_state["sidebar_message"] = "This simulated history already exists - nothing new was added."


def render_sidebar():
    """Draw the Admin Controls in the sidebar."""
    sidebar = st.sidebar
    sidebar.markdown("---")
    sidebar.subheader("🛠️ Admin Controls")

    message = st.session_state.pop("sidebar_message", None)
    if message:
        sidebar.success(message)

    # --- Pause / Resume -------------------------------------------------------
    paused = database.get_setting("paused", "0") == "1"
    left, right = sidebar.columns(2)
    left.button("⏸ Pause", key="sb_pause", on_click=set_paused, args=(True,),
                disabled=paused, use_container_width=True)
    right.button("▶ Resume", key="sb_resume", on_click=set_paused, args=(False,),
                 disabled=not paused, use_container_width=True)
    sidebar.caption("Simulation is **paused**." if paused else "Simulation is **running**.")

    # --- Activity level and speed --------------------------------------------
    levels = list(config.ACTIVITY_LEVELS)
    current_activity = database.get_setting("activity", config.DEFAULT_ACTIVITY)
    if current_activity not in levels:
        current_activity = config.DEFAULT_ACTIVITY
    sidebar.selectbox("Activity level", levels, index=levels.index(current_activity),
                      key="sb_activity", on_change=_save_activity,
                      help="How many parking spaces change at every update.")

    try:
        current_interval = int(database.get_setting("interval_seconds", config.DEFAULT_INTERVAL))
    except ValueError:
        current_interval = config.DEFAULT_INTERVAL
    if current_interval not in config.UPDATE_INTERVALS:
        current_interval = config.DEFAULT_INTERVAL
    sidebar.selectbox("Update interval", config.UPDATE_INTERVALS,
                      index=config.UPDATE_INTERVALS.index(current_interval),
                      format_func=lambda seconds: f"{seconds} seconds",
                      key="sb_interval", on_change=_save_interval,
                      help="Time between automatic updates (simulation speed).")

    # --- Filters --------------------------------------------------------------
    sidebar.markdown("**Filters**")
    zone_options = ["All Zones"] + [f"Zone {zone}" for zone in config.ZONES]
    sidebar.selectbox("Parking zone", zone_options, key="filter_zone")
    sidebar.selectbox("History period", list(config.TIME_WINDOWS), key="filter_window")

    # --- Simulated history and reset -----------------------------------------
    sidebar.markdown("**Data**")
    sidebar.button("➕ Generate simulated history", key="sb_generate",
                   on_click=_generate_history, use_container_width=True,
                   help=f"Adds {config.SEED_DAYS} days of hourly SIMULATED records.")

    with sidebar.expander("⚠️ Reset simulation"):
        st.write("Deletes ALL history and sets every space to Available.")
        st.checkbox("Also create new simulated history", value=True, key="sb_reseed")
        confirmed = st.checkbox("I understand, reset everything", key="sb_confirm_reset")
        st.button("🔄 Reset now", key="sb_reset", on_click=_reset_simulation,
                  disabled=not confirmed, use_container_width=True)

    snapshots, rows = database.get_history_counts()
    sidebar.caption(f"Database: {snapshots} snapshots, {rows} history rows")
    sidebar.caption("ℹ️ " + config.SIMULATION_NOTICE)
