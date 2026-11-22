# Smart Parking Space Analysis System using Python and Streamlit

A college mini-project for **Data Mining** and **Data Wrangling**.
It simulates a parking lot (40 spaces, 4 zones), stores every change in SQLite,
and analyses the history with data wrangling, analytics and data-mining algorithms
(K-Means, Decision Tree, Outlier Detection) on an interactive Streamlit dashboard.

> **Important:** all parking data is **simulated**. The application is not connected to
> real sensors or real parking facilities, and it never claims to be.

---

## 1. Folder structure

```
Smart_Parking_Space_Analysis/
│
├── app.py                  <- START HERE (navigation + sidebar + page runner)
├── config.py               <- all settings (zones, colours, thresholds, minimum data)
├── database.py             <- SQLite: smart_parking.db, tables, read/write functions
├── parking_simulator.py    <- simulated sensor data + history generator
├── data_cleaning.py        <- DATA WRANGLING functions
├── data_mining.py          <- K-Means, Decision Tree, Outlier detection
├── analytics.py            <- calculations for dashboard / zones / usage / peaks
├── visualization.py        <- Plotly charts + the green/red parking grid
├── ui_helpers.py           <- shared Streamlit helpers (cards, sidebar, auto-refresh)
├── requirements.txt
├── README.md
│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Live_Parking.py
│   ├── 3_Zone_Analysis.py
│   ├── 4_Usage_Analytics.py
│   ├── 5_Data_Mining.py
│   ├── 6_Data_Wrangling.py
│   ├── 7_Reports.py
│   └── 8_About_Project.py
│
├── data/
│   └── sample_parking_data.csv   <- deliberately messy CSV for the wrangling demo
├── reports/                      <- saved report copies appear here
├── assets/
│   └── style.css
├── docs/
│   ├── PROJECT_DOCUMENTATION.md  <- abstract, diagrams, viva questions ...
│   └── PROJECT_DOCUMENTATION.docx
└── .streamlit/config.toml        <- light theme
```

`smart_parking.db` is created automatically the first time you run the project.

---

## 2. Step-by-step guide (Windows + VS Code)

### Step 1 - Install Python
Download **Python 3.11** (3.10 or 3.12 also work) from https://www.python.org/downloads/ .
During installation, **tick "Add python.exe to PATH"**, then click *Install Now*.
> Do **not** use Python 3.13 or newer with this `requirements.txt` - some pinned packages have no installer for it.

Check it worked (open Command Prompt):
```
python --version
```

### Step 2 - Install VS Code
Download from https://code.visualstudio.com/ and install. Open VS Code, press
`Ctrl + Shift + X`, search for **Python** (Microsoft) and click *Install*.

### Step 3 - Create the project folder
Unzip `Smart_Parking_Space_Analysis.zip` (right-click -> *Extract All*), for example to
`C:\Projects\Smart_Parking_Space_Analysis`.
*(If you want to build the files yourself, create this folder and the sub-folders shown above.)*

### Step 4 and 5 - Create / paste the Python files
The zip already contains every file with the full code, so **nothing needs to be typed or pasted**.
In VS Code choose **File -> Open Folder...** and select `Smart_Parking_Space_Analysis`.
*(If you are typing the project by hand: create each file from the folder structure above and paste the matching code into it.)*

### Step 6 - Open the VS Code terminal
Menu **Terminal -> New Terminal**. Make sure the path shown ends with `Smart_Parking_Space_Analysis`.

### Step 7 - Create a virtual environment
```
python -m venv venv
```

### Step 8 - Activate the environment (Windows)
Command Prompt (cmd):
```
venv\Scripts\activate
```
PowerShell:
```
venv\Scripts\Activate.ps1
```
If PowerShell says *"running scripts is disabled"*, run this once and activate again:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
You should now see `(venv)` at the start of the line.
If VS Code asks *"We noticed a new environment"*, click **Yes**.

### Step 9 - Install the dependencies
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 10 - Initialise the SQLite database
```
python database.py
```
Expected output:
```
Database ready : ...\smart_parking.db
Parking spaces : 40
History rows   : 0 (0 snapshots)
```
(The first start of the app then adds a first snapshot and 7 days of simulated history automatically.)

### Step 11 - Run the Streamlit application
```
streamlit run app.py
```
If Streamlit asks for an e-mail address, just press **Enter**.
If `streamlit` is "not recognized", use: `python -m streamlit run app.py`

### Step 12 - Open the application in the browser
Streamlit opens your browser automatically. If not, open **http://localhost:8501**.
Stop the application with `Ctrl + C` in the terminal.

### Step 13 - Test every module
Use this checklist (about 10 minutes):

| # | Page / area | What to do | Expected result |
|---|-------------|-----------|-----------------|
| 1 | **Dashboard** | Open it | 6 metric cards, gauge, donut, zone bars. Numbers change every ~5 s |
| 2 | **Live Parking** | Watch the grid, click **Update now** | 40 spaces: green = available, red = occupied. "Last updated" changes |
| 3 | Live Parking | Click **Pause**, wait 10 s, then **Resume** | Nothing changes while paused; updates continue after resume |
| 4 | Sidebar | Change **Activity level** to High and **Update interval** to 3 seconds | More spaces change, faster updates |
| 5 | Sidebar | Choose **Parking zone = Zone A** | Live Parking shows only Zone A; Zone Analysis shows its detail |
| 6 | **Zone Analysis** | Open it | Most / least occupied zone cards, two bar charts, table |
| 7 | **Usage Analytics** | Open each tab | Trends, peak hours (red bars), heatmap, zone usage, vehicle types |
| 8 | **Data Mining -> K-Means** | Move k between 2 and 3 | Zone table, scatter plot, silhouette score |
| 9 | **Data Mining -> Decision Tree** | Change depth, use "Try a prediction" | Accuracy vs baseline, confusion matrix, prediction |
| 10 | **Data Mining -> Outliers** | Lower the sensitivity to 0.5 | Red outlier points appear |
| 11 | **Data Wrangling** | Keep "Sample CSV", scroll down | Raw data with problems -> step report -> clean table -> filter -> aggregate |
| 12 | **Reports** | Click the 3 download buttons | Three CSV files download |
| 13 | **Restart test** | Stop the app (Ctrl+C), run it again | Previous history is still there |
| 14 | Sidebar -> **Reset simulation** | Tick both boxes, click **Reset now** | History cleared and recreated |

---

## 3. How the simulation works (short)

* Each hour has a *demand* (busy around 9-11 AM, quiet at night) and each zone has a *popularity*
  (A is the most popular, D the least). Both are in `config.py`.
* At every update each space may re-decide: it becomes **Occupied** with a probability based on the
  hour and zone, otherwise **Available**. The **Activity level** controls how many spaces re-decide.
* On the first run, 7 days of **hourly simulated history** are created (`source = simulated_backfill`)
  so the analytics and algorithms have enough data. Live updates are stored as `live_simulation`.
* The simulation advances while a **Dashboard or Live Parking** page is open (they refresh automatically).
* **No duplicate records:** the table has `UNIQUE (timestamp, space_id)`, and the simulator
  refuses to save if the last update was too recent or the simulation is paused.
* To keep the database small only the newest 2000 live snapshots are kept (`MAX_LIVE_SNAPSHOTS`).

## 4. Minimum data rules for the algorithms

| Algorithm | Needs at least | If not enough |
|-----------|----------------|---------------|
| Trend charts | 2 snapshots | Friendly message |
| Peak periods | 3 different hours of the day | Friendly message |
| K-Means | 10 snapshots per zone, more zones than k | Warning, no model |
| Decision Tree | 60 (hour, zone) records and 2+ occupancy levels | Warning, no model |
| Outliers | 30 records per zone | Warning, no result |

You can change these numbers in `config.py`.

## 5. Troubleshooting

| Problem | Fix |
|---------|-----|
| `streamlit` is not recognized | Activate the venv (Step 8) or use `python -m streamlit run app.py` |
| `ModuleNotFoundError` | The venv is not active or Step 9 was skipped. Activate it and run `pip install -r requirements.txt` |
| `pip install` fails with a numpy / scikit-learn error | You are probably on Python 3.13+. Install Python 3.11 and recreate the venv |
| PowerShell blocks `Activate.ps1` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |
| Charts show "No history" | Click **Generate simulated history** in the sidebar, or choose **History period = All history** |
| Want to start completely fresh | Stop the app, delete `smart_parking.db`, run it again (or use *Reset simulation*) |

## 6. Technology

Python - Streamlit - Pandas / NumPy - Plotly - Scikit-learn - SQLite - CSV - VS Code

Full report text, diagrams and 20 viva questions: see `docs/PROJECT_DOCUMENTATION.md` (also as `.docx`).
