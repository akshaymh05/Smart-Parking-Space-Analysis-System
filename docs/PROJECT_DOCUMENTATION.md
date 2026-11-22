---
title: "Smart Parking Space Analysis System using Python and Streamlit"
subtitle: "Mini-Project Documentation - Data Mining and Data Wrangling"
---

# Part A - Project Report

## 1. Project Abstract

Finding a free parking space wastes time and fuel. This project presents a **Smart Parking Space Analysis System** that simulates a parking lot of 40 spaces divided into four zones (A, B, C, D). Because no physical sensors are used, a **simulator** produces parking-sensor style data: each space is either *Available* or *Occupied*, and the probability of being occupied depends on the hour of the day, the weekday and the popularity of the zone. Every update is stored with a timestamp in a **SQLite** database, so a history of the simulation builds up and survives restarts.

The recorded history is processed with **data wrangling** (missing-value handling, duplicate removal, type conversion, cleaning, filtering, aggregation, feature creation) and analysed with **data mining** algorithms: **K-Means clustering** groups zones by occupancy, a **Decision Tree** classifies occupancy as Low, Medium or High, and **outlier detection** (IQR or Z-score) finds unusual records. Results are shown on an interactive **Streamlit** dashboard with **Plotly** charts, and reports can be downloaded as CSV files.

**Note:** all data in the project is simulated. The system is not connected to real sensors or real parking facilities.

## 2. Introduction

Urban parking demand is high and drivers often circle a car park looking for space. Smart-parking systems monitor occupancy, show availability and help managers find busy periods. This mini-project demonstrates the *analysis* side of such a system using beginner-friendly tools: Python for logic, Pandas for data handling, Scikit-learn for data mining, SQLite for storage and Streamlit for the web interface.

## 3. Problem Statement

Parking managers and users need to know which zones are free, when the lot is busiest and whether unusual patterns exist. Raw occupancy records are numerous and often messy (missing values, duplicates, inconsistent spellings). The problem is to build a system that **records parking occupancy over time, cleans the data, analyses usage patterns with data-mining techniques and presents the results clearly**, without needing real hardware.

## 4. Objectives

1. Simulate the occupancy of 40 parking spaces in four zones.
2. Monitor available and occupied spaces and show them live (green / red).
3. Store timestamped history in SQLite so data persists after restart.
4. Analyse zone-wise occupancy, trends, usage patterns and peak periods.
5. Apply data wrangling to produce clean, analysable data.
6. Apply K-Means, Decision Tree and outlier detection with proper data checks.
7. Provide admin controls (pause, speed, activity, filters, reset).
8. Provide downloadable CSV reports.

## 5. Existing System

* Manual parking management: attendants count vehicles; no history is kept.
* Basic counters at the entrance that show only the total free spaces, with no zone detail and no analysis.
* Hardware sensor systems are expensive to install and usually need specialist software.

**Drawbacks:** no usage analysis, no peak-period detection, no data cleaning, high cost, little insight for planning.

## 6. Proposed System

A software-only system that simulates sensor data, stores a history, cleans and analyses it, and displays everything in a web dashboard.

**Advantages over the existing system:** zone-level monitoring, historical trends and peak hours, data-mining insights, reports, no hardware cost, easy to demonstrate and extend to real sensors later.

## 7. Hardware Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| Processor | Dual-core 1.8 GHz | Quad-core |
| RAM | 4 GB | 8 GB |
| Free disk space | 500 MB | 1 GB |
| Display | 1366 x 768 | 1920 x 1080 |
| Other | Keyboard, mouse | - |

No sensors or special hardware are required.

## 8. Software Requirements

| Item | Details |
|------|---------|
| Operating system | Windows 10 / 11 (also works on Linux and macOS) |
| Language | Python 3.10 - 3.12 (3.11 recommended) |
| Editor | Visual Studio Code with the Python extension |
| Libraries | streamlit 1.40.2, pandas 2.2.3, numpy 1.26.4, plotly 5.24.1, scikit-learn 1.5.2 |
| Database | SQLite (built into Python) |
| Browser | Chrome, Edge or Firefox |

## 9. System Architecture

```
+--------------------------------------------------------------------+
|                    PRESENTATION LAYER (Streamlit)                  |
|  app.py  ->  pages/1..8  (Dashboard, Live, Zones, Usage, Mining,   |
|                           Wrangling, Reports, About)               |
|  ui_helpers.py (cards, sidebar admin controls, auto-refresh)       |
+----------------------------------+---------------------------------+
                                   |
+----------------------------------v---------------------------------+
|                     PROCESSING LAYER (Python)                      |
|  analytics.py        data_cleaning.py        data_mining.py        |
|  (KPIs, trends,      (wrangling pipeline)    (K-Means, Tree,       |
|   peaks)                                      Outliers)            |
|  visualization.py (Plotly charts, parking grid)                    |
+----------------------------------+---------------------------------+
                                   |
+----------------------------------v---------------------------------+
|                         DATA LAYER                                 |
|  parking_simulator.py  ->  database.py  ->  smart_parking.db       |
|  (simulated sensors)       (SQLite)         parking_spaces         |
|                                             parking_history        |
|                                             app_settings           |
|  data/sample_parking_data.csv  (CSV input)   reports/ (CSV output) |
+--------------------------------------------------------------------+
```

## 10. Data Flow Diagram

**Level 0 (context diagram)**

```
 +---------+   controls, filters, uploads    +---------------------------+
 |  User / | ------------------------------> |  Smart Parking Space      |
 |  Admin  | <------------------------------ |  Analysis System          |
 +---------+   dashboards, charts, CSV       +---------------------------+
```

**Level 1**

```
 (Parking Simulator)
        |  1. simulated status of 40 spaces
        v
 [P1 Update & Store] ----> D1: parking_spaces (current)
        |             ----> D2: parking_history (timestamped)
        v
 [P2 Data Wrangling] <---- D2 / sample CSV / uploaded CSV
        |  clean data
        v
 [P3 Analytics]  -----> KPIs, zone summary, trends, peak hours
 [P4 Data Mining] ----> clusters, predictions, outliers
        |
        v
 [P5 Visualisation & Reports] ----> User (dashboard, CSV downloads)

 User admin controls ----> D3: app_settings (pause, speed, activity)
```

## 11. Use Case Diagram

```
                    +----------------------------------------------+
                    |   Smart Parking Space Analysis System        |
                    |                                              |
                    |  (View dashboard)                            |
                    |  (Watch live parking)                        |
   +--------+       |  (Analyse zones)                             |
   |  User  |------>|  (View usage analytics / peak hours)         |
   +--------+       |  (Run K-Means / Decision Tree / Outliers)    |
                    |  (Wrangle & clean data)                      |
                    |  (Download CSV reports)                      |
                    |                                              |
   +--------+       |  (Pause / resume simulation)                 |
   | Admin  |------>|  (Change speed & activity level)             |
   +--------+       |  (Filter zone / period / records)            |
                    |  (Generate simulated history)                |
                    |  (Reset simulation)                          |
                    +----------------------------------------------+
```
(The Admin is also a User; the admin controls are in the sidebar.)

## 12. Module Descriptions

| Module | Page / file | Description |
|--------|-------------|-------------|
| 1 Dashboard | `1_Dashboard.py` | Metric cards: total, occupied, available, occupancy %, zones, availability status; gauge, donut and zone chart; auto-refresh |
| 2 Live Parking | `2_Live_Parking.py` | 40 spaces in a green/red grid; automatic update every 5 s; Update-now button; pause / resume; last-updated time; recent changes |
| 3 Zone Analysis | `3_Zone_Analysis.py` | Occupied, available and occupancy % per zone; most / least occupied zone; bar charts and tables |
| 4 Usage Analytics | `4_Usage_Analytics.py` | Occupancy and availability trends, hourly pattern, peak hours, weekday x hour heatmap, zone usage, vehicle types |
| 5 Data Mining | `5_Data_Mining.py` | K-Means, Decision Tree, outlier detection, with explanations and minimum-data checks |
| 6 Data Wrangling | `6_Data_Wrangling.py` | Missing values, duplicates, type conversion, cleaning, filtering, aggregation, feature creation; shows the cleaned table |
| 7 Reports | `7_Reports.py` | CSV downloads (current status, history, zone analysis) and summary statistics |
| 8 Admin Controls | sidebar (`ui_helpers.py`) | Reset, speed (interval), activity level, zone filter, period filter, pause / resume |
| About | `8_About_Project.py` | Project description, technologies, database design |

## 13. Algorithm Explanations

### 13.1 K-Means Clustering (zones)
* **Input:** one row per zone with two features: *average occupancy %* and *peak occupancy %* computed from the history.
* **Steps:** choose k (2 or 3) -> place k centres -> assign each zone to the nearest centre -> move each centre to the mean of its zones -> repeat until stable.
* **Output:** each zone gets a cluster, named *Low / Medium / High Usage* by comparing cluster centres. The **silhouette score** (-1 to 1) measures how well separated the clusters are.
* **Data check:** at least 10 snapshots per zone and more zones than k.

### 13.2 Decision Tree (Low / Medium / High)
* **Records:** one per (clock hour, zone) with the average occupancy of that hour.
* **Target:** Low (< 40 %), Medium (40 % to < 70 %), High (>= 70 %).
* **Inputs:** hour, day of week, zone code (the occupancy itself is *not* an input, so the tree must learn the pattern).
* **Validation:** 75 / 25 train-test split (stratified when possible); accuracy, confusion matrix, precision / recall / F1, feature importance and a **baseline** (always guess the commonest level). A warning appears if the tree does not beat the baseline.
* **Data check:** at least 60 records and at least 2 levels.

### 13.3 Outlier Detection
* **IQR:** Q1 and Q3 are the 25th and 75th percentiles, IQR = Q3 - Q1. A value is an outlier if it is below Q1 - s x IQR or above Q3 + s x IQR (s = 1.5 by default).
* **Z-score:** outlier if it is more than s standard deviations from the zone average.
* Bounds are calculated separately for each zone. **Data check:** at least 30 records per zone.

## 14. Database Design

Database file: `smart_parking.db` (SQLite)

**parking_spaces** (current state)

| Column | Type | Notes |
|--------|------|-------|
| space_id | TEXT | Primary key, e.g. A01 |
| zone | TEXT | A, B, C or D |
| status | TEXT | Available / Occupied |
| vehicle_type | TEXT | Car, SUV, Motorcycle, Van or None |
| last_updated | TEXT | Timestamp |

**parking_history** (time series)

| Column | Type | Notes |
|--------|------|-------|
| record_id | INTEGER | Primary key, auto-increment |
| timestamp | TEXT | Snapshot time |
| space_id | TEXT | Parking space |
| zone | TEXT | Zone |
| status | TEXT | Available / Occupied |
| vehicle_type | TEXT | Vehicle or None |
| source | TEXT | `live_simulation` or `simulated_backfill` |
| | | `UNIQUE (timestamp, space_id)` prevents duplicates |

**app_settings** (key / value): `paused`, `activity`, `interval_seconds`, `last_update`.

```
parking_spaces (1) ----- (many) parking_history      linked by space_id
```

## 15. Advantages

* No hardware needed; easy to run and demonstrate.
* Complete pipeline: data generation -> storage -> wrangling -> analytics -> data mining -> reports.
* Data persists in SQLite; no duplicate records on page re-runs.
* Algorithms refuse to run on too little data and explain their results.
* Clean, interactive, colour-coded dashboard.

## 16. Limitations

* The data is simulated, so findings reflect the simulation rules, not real driver behaviour.
* The simulation advances only while the Dashboard or Live Parking page is open in a browser.
* K-Means on four zones is a demonstration; the sample is tiny.
* Outliers are rare because occupancy is bounded between 0 % and 100 % and the simulation is regular.
* Single-user, local application; no login or security.

## 17. Future Enhancements

* Connect to real IoT / ultrasonic / camera sensors through MQTT or REST.
* Forecast future occupancy with time-series models.
* Mobile app and navigation to the nearest free space.
* Pricing, reservations and payment.
* Number-plate recognition and entry / exit logs.
* Multi-user login, cloud database, e-mail / SMS alerts.

## 18. Conclusion

The project shows how data wrangling and data mining can turn parking-occupancy records into useful knowledge. A simulator provides the data, SQLite stores the history, Pandas cleans it, Scikit-learn mines it, and Streamlit with Plotly presents it. The system is complete, modular and easy to extend, and it can be connected to real sensors in the future.

---

# Part B - Project Presentation Preparation

## B1. How the project works
1. `app.py` starts, creates the database and 40 spaces, and (first run only) creates 7 days of simulated history.
2. The user opens a page from the sidebar. Dashboard and Live Parking refresh every 5 seconds.
3. Before each refresh the simulator makes one *update*: every space may change status. The new state is written to `parking_spaces` and added to `parking_history` with a timestamp.
4. Analytics, wrangling and mining pages read the history from SQLite, process it with Pandas / Scikit-learn and draw Plotly charts.
5. Reports are downloaded as CSV files.

## B2. How data is collected and simulated
There are no sensors. For every space the chance of being *Occupied* is `hour demand x zone popularity x weekend factor` (see `config.py`). Morning (9-11 AM) demand is high and night demand is low; Zone A is most popular and Zone D least. A space only re-decides with a small probability each update, so the lot changes gradually, like real traffic. Each snapshot (40 rows) is saved with its timestamp.

## B3. How data wrangling is performed
The pipeline in `data_cleaning.py` runs in order: standardise column names -> convert types (text to datetime) -> clean text values (`"free"` -> `Available`) -> handle missing values (zone from space ID, status by mode or removal, vehicle type by status) -> validate space IDs (remove `Z99`) -> remove duplicates (same timestamp + space) -> create features (hour, weekday, weekend flag, time period, occupied flag). Filtering and aggregation (group by zone, hour, date ...) follow. The sample CSV contains deliberate errors, so each step visibly fixes something.

## B3b. How data mining is performed
The history is turned into tables suited to each algorithm (zone profiles for K-Means, hourly zone records for the Decision Tree, zone-time records for outliers). The page first checks the minimum amount of data, then trains / runs the algorithm and shows the result with validation numbers.

## B4. How K-Means works in this project
Each zone is a point described by *average occupancy %* and *peak occupancy %*. K-Means picks k centres, assigns every zone to the closest centre, recalculates the centres, and repeats until the groups stop changing. The cluster with the lowest centre is called *Low Usage* and the highest *High Usage*. The silhouette score tells how clear the grouping is.

## B5. How the dashboard displays parking information
Six metric cards (total, occupied, available, occupancy %, zones, availability message), a gauge for the occupancy percentage, a donut chart for occupied versus available, and a stacked bar per zone. **Green = available, red = occupied, blue = information.** The Live Parking page shows each space as a coloured box with its ID and vehicle type.

## B6. Twenty viva questions with simple answers

1. **What is the aim of your project?** To simulate a parking lot, store its history, and analyse it with data wrangling and data mining, shown on a Streamlit dashboard.
2. **Is the data real?** No. It is simulated; the system is not connected to real sensors or a real parking facility.
3. **Why did you simulate the data?** Real sensors are expensive and not available for a college project; simulation lets us test the analysis safely.
4. **How is the simulated data created?** Each space becomes occupied with a probability that depends on the hour, the weekday and the zone popularity.
5. **Why Streamlit?** It builds web dashboards with only Python, so there is no need for HTML, CSS or JavaScript.
6. **Why SQLite?** It is a built-in, file-based database that needs no installation and keeps data after restart.
7. **Which tables did you create?** `parking_spaces` (current status), `parking_history` (timestamped records) and `app_settings`.
8. **How do you avoid duplicate records?** `parking_history` has a UNIQUE rule on (timestamp, space_id), and the simulator will not save if paused or if the last update was too recent.
9. **What is data wrangling?** Converting raw, messy data into clean, structured data that can be analysed.
10. **Which wrangling steps did you implement?** Missing values, duplicate removal, type conversion, text cleaning, ID validation, filtering, aggregation and feature creation.
11. **How do you handle missing values?** Rows without timestamp or space ID are removed; zone is taken from the space ID; status is filled with the most common value (or the row is removed); vehicle type is "None" if available, "Unknown" if occupied.
12. **What is feature creation? Give examples.** Making new columns from existing ones, e.g. hour, day name, weekend flag, time period and `is_occupied`.
13. **What is K-Means?** An unsupervised algorithm that groups similar data points into k clusters around centres.
14. **What data does K-Means use here and why?** Each zone's average and peak occupancy, so zones with similar usage fall into the same cluster.
15. **What is the silhouette score?** A number from -1 to 1 showing how well each point fits its own cluster; higher is better.
16. **What is a Decision Tree and what does yours predict?** A model that asks yes/no questions to reach a decision; ours predicts Low, Medium or High occupancy from hour, weekday and zone.
17. **How do you know the Decision Tree is good?** We test it on 25 % unseen data and compare accuracy with a baseline that always guesses the commonest level.
18. **What is an outlier and how do you detect it?** A value far from the others. We use the IQR rule (outside Q1 - 1.5 x IQR to Q3 + 1.5 x IQR) or a Z-score threshold, for each zone separately.
19. **Why do the algorithms refuse to run sometimes?** Training on too little data gives meaningless results, so each algorithm checks a minimum amount of data first.
20. **What are the limitations and future work?** Data is simulated and K-Means has only four zones; in future we can add real sensors, forecasting, reservations and a mobile app.

---

*All data in this project is simulated.*
