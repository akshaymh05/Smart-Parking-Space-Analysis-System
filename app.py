"""
app.py  -  START HERE
---------------------
Run the project with:    streamlit run app.py

This file is the "main" file. It
  1. sets the page settings,
  2. makes sure the database and the simulated data exist,
  3. builds the sidebar navigation with the 8 pages,
  4. draws the Admin Controls in the sidebar,
  5. runs the page the user selected (files inside the pages/ folder).
"""

import streamlit as st

import config
import parking_simulator
import ui_helpers

# This must be the first Streamlit command and may only appear in this file.
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def start_up():
    """Create the database and the first simulated data (runs only once per server start)."""
    parking_simulator.ensure_initialized()
    return True


ui_helpers.load_css()

try:
    start_up()
except Exception as error:   # show a friendly message instead of a crash
    st.error(f"Could not prepare the database: {error}")
    st.stop()

# Sidebar navigation (the page files are in the pages/ folder)
pages = [
    st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("pages/2_Live_Parking.py", title="Live Parking", icon="🚗"),
    st.Page("pages/3_Zone_Analysis.py", title="Zone Analysis", icon="🗺️"),
    st.Page("pages/4_Usage_Analytics.py", title="Usage Analytics", icon="📈"),
    st.Page("pages/5_Data_Mining.py", title="Data Mining", icon="🧠"),
    st.Page("pages/6_Data_Wrangling.py", title="Data Wrangling", icon="🧹"),
    st.Page("pages/7_Reports.py", title="Reports", icon="📄"),
    st.Page("pages/8_About_Project.py", title="About Project", icon="ℹ️"),
]
selected_page = st.navigation(pages)

ui_helpers.render_sidebar()
selected_page.run()
