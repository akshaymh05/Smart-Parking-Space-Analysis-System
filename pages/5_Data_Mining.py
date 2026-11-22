"""
Page 5 - Data Mining
  Tab 1: K-Means clustering of the parking zones
  Tab 2: Decision Tree classification (Low / Medium / High occupancy)
  Tab 3: Outlier detection (IQR or Z-score)
All algorithms use the saved SIMULATED history and refuse to run on too little data.
"""

import streamlit as st

import config
import data_mining
import ui_helpers
import visualization

ui_helpers.page_header(
    "🧠", "Data Mining",
    "K-Means clustering, Decision Tree classification and outlier detection on the simulated parking history.",
)

# Data mining always uses all zones (the zone filter would remove the data the algorithms need).
history = ui_helpers.load_history(apply_zone_filter=False)
st.caption(
    f"Using {len(history)} history records, period: {st.session_state.get('filter_window', 'All history')}. "
    "The zone filter is ignored on this page because the algorithms compare all zones."
)

if history.empty:
    st.warning("No history data yet. Click **Generate simulated history** in the sidebar or let the simulation run.")
    st.stop()

tab_kmeans, tab_tree, tab_outlier = st.tabs(
    ["🔵 K-Means Clustering", "🌳 Decision Tree", "🚨 Outlier Detection"]
)

# =============================================================================
# K-MEANS
# =============================================================================
with tab_kmeans:
    st.subheader("K-Means Clustering of Parking Zones")
    with st.expander("📘 How K-Means works (simple explanation)", expanded=False):
        st.markdown(
            """
**Goal:** put zones that behave similarly into the same group (cluster).

1. Every zone is described by two numbers: its **average occupancy %** and its **peak occupancy %**.
2. We choose **k**, the number of groups we want (2 or 3 here).
3. K-Means puts k "centres" on the chart, assigns every zone to its nearest centre,
   then moves each centre to the middle of its zone group. It repeats until nothing changes.
4. We name the groups from *Low Usage* to *High Usage* by comparing the centres.

**Minimum data:** at least {snap} history snapshots per zone, and more zones than k.
The **silhouette score** (-1 to 1) tells how well separated the groups are; higher is better.
            """.format(snap=config.MIN_SNAPSHOTS_KMEANS)
        )

    k = st.slider("Number of clusters (k)", min_value=2, max_value=3, value=2, key="kmeans_k")
    ready, message = data_mining.check_kmeans_data(history, k)
    if not ready:
        st.warning(message)
    else:
        try:
            outcome = data_mining.run_kmeans(history, k)
            result, centers = outcome["result"], outcome["centers"]

            cards = [("Clusters (k)", k, "Chosen by you", "blue"),
                     ("Inertia", f"{outcome['inertia']:.1f}", "Lower = tighter groups", "blue")]
            if outcome["silhouette"] is not None:
                cards.append(("Silhouette score", f"{outcome['silhouette']:.2f}", "Higher = better separation", "green"))
            ui_helpers.show_metric_cards(cards, per_row=3)

            left, right = st.columns([3, 2])
            with left:
                st.plotly_chart(visualization.kmeans_scatter(result, centers), use_container_width=True)
            with right:
                st.markdown("**Zones and their clusters**")
                ui_helpers.show_table(result[["zone_label", "avg_occupancy", "peak_occupancy", "cluster_label"]].rename(
                    columns={"zone_label": "Zone", "avg_occupancy": "Avg %", "peak_occupancy": "Peak %",
                             "cluster_label": "Cluster"}))
                st.markdown("**Cluster centres**")
                ui_helpers.show_table(centers[["cluster_label", "avg_occupancy", "peak_occupancy"]].rename(
                    columns={"cluster_label": "Cluster", "avg_occupancy": "Avg %", "peak_occupancy": "Peak %"}))
            st.info("With only 4 zones this is a small demonstration of clustering. The result describes simulated data.")
        except ValueError as error:
            st.warning(str(error))

# =============================================================================
# DECISION TREE
# =============================================================================
with tab_tree:
    st.subheader("Decision Tree: predict Low / Medium / High occupancy")
    with st.expander("📘 How the Decision Tree works (simple explanation)", expanded=False):
        st.markdown(
            f"""
**Goal:** predict the occupancy level of a zone from the **hour**, the **weekday** and the **zone**.

* Levels: **Low** (below {config.LOW_MAX}%), **Medium** ({config.LOW_MAX}% to below {config.MEDIUM_MAX}%), **High** ({config.MEDIUM_MAX}% and above).
* The tree asks simple yes/no questions, such as "Is the hour before 8?", and follows the answers down to a prediction.
* The data is split: **75% to train** the tree, **25% to test** it on records it has never seen.
* **Accuracy** is the share of correct predictions. We also show the accuracy of
  *always guessing the most common level* (the baseline) to check the tree really learned something.
* **Max depth** limits how many questions the tree may ask. A very deep tree memorises the data (overfitting).

**Minimum data:** at least {config.MIN_RECORDS_TREE} (hour, zone) records and at least 2 different levels.
            """
        )

    dataset = data_mining.build_tree_dataset(history)
    col_depth, col_test = st.columns(2)
    max_depth = col_depth.slider("Maximum tree depth", 2, 6, 4, key="tree_depth")
    test_percent = col_test.slider("Test data (%)", 20, 40, 25, step=5, key="tree_test")

    try:
        tree = data_mining.train_decision_tree(dataset, max_depth=max_depth, test_size=test_percent / 100)

        ui_helpers.show_metric_cards(
            [
                ("Accuracy", f"{tree['accuracy'] * 100:.1f}%", f"On {tree['test_size']} unseen test records", "green"),
                ("Baseline accuracy", f"{tree['baseline_accuracy'] * 100:.1f}%", "Always guess the commonest level", "blue"),
                ("Training records", tree["train_size"], f"{len(dataset)} records in total", "blue"),
            ],
            per_row=3,
        )
        for warning in tree["warnings"]:
            st.warning(warning)

        left, right = st.columns(2)
        with left:
            st.plotly_chart(visualization.confusion_heatmap(tree["confusion_matrix"]), use_container_width=True)
        with right:
            st.plotly_chart(visualization.importance_bar(tree["importance"]), use_container_width=True)

        st.markdown("**Precision, recall and F1-score for each level**")
        st.dataframe(tree["report"], use_container_width=True)

        with st.expander("Show the learned decision rules"):
            st.code(tree["rules"])

        st.markdown("### Try a prediction")
        col_zone, col_hour, col_day = st.columns(3)
        zone_choice = col_zone.selectbox("Zone", config.ZONES, key="predict_zone")
        hour_choice = col_hour.slider("Hour of day", 0, 23, 10, key="predict_hour")
        day_names = list(config.DAY_ORDER)
        day_choice = col_day.selectbox("Day of week", day_names, key="predict_day")
        level, probabilities = data_mining.predict_level(
            tree["model"], zone_choice, hour_choice, day_names.index(day_choice))
        st.success(f"Predicted occupancy level for Zone {zone_choice} at {hour_choice:02d}:00 on {day_choice}: **{level}**")
        st.caption("Probabilities: " + ", ".join(f"{name} {value * 100:.0f}%" for name, value in probabilities.items()))
    except ValueError as error:
        st.warning(str(error))
        st.caption(f"Records available for the tree right now: {len(dataset)}")

# =============================================================================
# OUTLIER DETECTION
# =============================================================================
with tab_outlier:
    st.subheader("Outlier Detection")
    with st.expander("📘 How outlier detection works (simple explanation)", expanded=False):
        st.markdown(
            f"""
**Goal:** find zone-occupancy records that are *unusual* compared with the rest of the same zone.

* **IQR method:** sort the values, find Q1 (25%) and Q3 (75%). IQR = Q3 - Q1.
  A value is an outlier if it is below `Q1 - s x IQR` or above `Q3 + s x IQR` (s is the sensitivity, usually 1.5).
* **Z-score method:** measure how many standard deviations a value is from the zone's average.
  A value is an outlier if it is more than *s* standard deviations away (usually 2 to 3).
* Smaller *s* means more records are flagged.

**Note:** parking occupancy is limited between 0% and 100% and changes during the day, so
with the default sensitivity few or no outliers may appear. Lower the sensitivity to explore.

**Minimum data:** at least {config.MIN_RECORDS_OUTLIER} records per zone.
            """
        )

    col_method, col_sens = st.columns(2)
    method = col_method.radio("Method", ["IQR", "Z-score"], horizontal=True, key="outlier_method")
    if method == "IQR":
        sensitivity = col_sens.slider("Sensitivity (IQR multiplier)", 0.5, 3.0, 1.5, step=0.1, key="outlier_iqr")
    else:
        sensitivity = col_sens.slider("Sensitivity (Z-score threshold)", 1.0, 4.0, 2.5, step=0.1, key="outlier_z")

    try:
        records, summary = data_mining.detect_outliers(history, method, sensitivity)
        total_outliers = int(records["is_outlier"].sum())
        ui_helpers.show_metric_cards(
            [
                ("Records checked", len(records), "Zone x timestamp", "blue"),
                ("Outliers found", total_outliers, f"{total_outliers / len(records) * 100:.2f}% of records",
                 "red" if total_outliers else "green"),
            ],
            per_row=2,
        )
        st.plotly_chart(visualization.outlier_scatter(records), use_container_width=True)

        st.markdown("**Summary by zone**")
        ui_helpers.show_table(summary.rename(columns={
            "zone_label": "Zone", "records": "Records", "outliers": "Outliers",
            "lower_bound": "Lower bound %", "upper_bound": "Upper bound %", "outlier_percent": "Outlier %"}))

        if total_outliers:
            st.markdown("**Unusual records**")
            flagged = records[records["is_outlier"]][["timestamp", "zone_label", "occupied", "total", "occupancy_pct"]]
            ui_helpers.show_table(flagged.head(500).rename(columns={
                "timestamp": "Time", "zone_label": "Zone", "occupied": "Occupied",
                "total": "Spaces", "occupancy_pct": "Occupancy %"}), height=300)
        else:
            st.success("No outliers found with this sensitivity. Try a smaller value.")
    except ValueError as error:
        st.warning(str(error))
