"""
data_mining.py
--------------
Three beginner-friendly data-mining algorithms (scikit-learn):

  1. K-Means clustering        -> groups the ZONES by how busy they are
  2. Decision Tree classifier  -> predicts occupancy level Low / Medium / High
  3. Outlier detection (IQR or Z-score) -> finds unusual occupancy records

Important: the algorithms are NOT run on tiny data. Every function checks the
minimum data requirements from config.py and raises a ValueError with a clear
message if there is not enough data.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

import analytics
import config

TREE_FEATURES = ["hour", "day_of_week", "zone_code"]
ZONE_CODES = {zone: index for index, zone in enumerate(config.ZONES)}


def occupancy_level(percentage):
    """Convert an occupancy percentage into Low / Medium / High."""
    if percentage < config.LOW_MAX:
        return "Low"
    if percentage < config.MEDIUM_MAX:
        return "Medium"
    return "High"


# ============================================================================
# 1. K-MEANS CLUSTERING
# ============================================================================
def zone_features(history_df):
    """One row per zone: average occupancy % and peak occupancy % over the history."""
    zone_data = analytics.zone_snapshot_occupancy(history_df)
    if zone_data.empty:
        return pd.DataFrame(columns=["zone", "zone_label", "avg_occupancy", "peak_occupancy", "snapshots"])
    features = zone_data.groupby("zone", as_index=False).agg(
        avg_occupancy=("occupancy_pct", "mean"),
        peak_occupancy=("occupancy_pct", "max"),
        snapshots=("timestamp", "nunique"),
    )
    features["avg_occupancy"] = features["avg_occupancy"].round(2)
    features["zone_label"] = features["zone"].map(analytics.zone_label)
    return features[["zone", "zone_label", "avg_occupancy", "peak_occupancy", "snapshots"]]


def check_kmeans_data(history_df, k):
    """Return (is_ready, message)."""
    features = zone_features(history_df)
    if features.empty:
        return False, "There is no history data yet."
    snapshots = int(features["snapshots"].min())
    if snapshots < config.MIN_SNAPSHOTS_KMEANS:
        return False, (
            f"K-Means needs at least {config.MIN_SNAPSHOTS_KMEANS} history snapshots per zone "
            f"to get a reliable zone profile, but only {snapshots} exist."
        )
    if len(features) <= k:
        return False, f"K-Means with k={k} needs more than {k} zones, but only {len(features)} exist."
    unique_points = features[["avg_occupancy", "peak_occupancy"]].drop_duplicates().shape[0]
    if unique_points < k:
        return False, f"The zones are too similar: only {unique_points} distinct profiles exist for k={k}."
    return True, "Enough data for K-Means."


def run_kmeans(history_df, k=2):
    """
    Group the zones into `k` clusters using average and peak occupancy.
    Returns a dictionary with the zone table, cluster centres, inertia and silhouette score.
    """
    ready, message = check_kmeans_data(history_df, k)
    if not ready:
        raise ValueError(message)

    features = zone_features(history_df)
    X = features[["avg_occupancy", "peak_occupancy"]].to_numpy(dtype=float)

    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)

    # Name the clusters from the lowest to the highest average occupancy
    names = {2: ["Low Usage", "High Usage"], 3: ["Low Usage", "Medium Usage", "High Usage"]}
    cluster_names = names.get(k, [f"Cluster {i + 1}" for i in range(k)])
    order = np.argsort(model.cluster_centers_[:, 0])
    name_for_cluster = {int(cluster_id): cluster_names[position] for position, cluster_id in enumerate(order)}

    result = features.copy()
    result["cluster"] = labels
    result["cluster_label"] = result["cluster"].map(name_for_cluster)

    centers = pd.DataFrame(model.cluster_centers_, columns=["avg_occupancy", "peak_occupancy"]).round(2)
    centers["cluster"] = range(k)
    centers["cluster_label"] = centers["cluster"].map(name_for_cluster)

    silhouette = None
    if len(set(labels)) >= 2 and len(features) > len(set(labels)):
        silhouette = float(silhouette_score(X, labels))

    return {
        "result": result.sort_values("avg_occupancy", ascending=False).reset_index(drop=True),
        "centers": centers.sort_values("avg_occupancy").reset_index(drop=True),
        "inertia": float(model.inertia_),
        "silhouette": silhouette,
        "k": k,
    }


# ============================================================================
# 2. DECISION TREE CLASSIFICATION
# ============================================================================
def build_tree_dataset(history_df):
    """
    One row per (clock hour, zone). The target is the occupancy level of that
    zone in that hour. The inputs are only hour, weekday and zone, so the tree
    must LEARN the pattern instead of reading the answer.
    """
    zone_data = analytics.zone_snapshot_occupancy(history_df)
    if zone_data.empty:
        return pd.DataFrame(columns=TREE_FEATURES + ["occupancy_pct", "occupancy_level"])

    zone_data["hour_bucket"] = zone_data["timestamp"].dt.floor("h")
    hourly = zone_data.groupby(["hour_bucket", "zone"], as_index=False)["occupancy_pct"].mean()
    hourly["hour"] = hourly["hour_bucket"].dt.hour
    hourly["day_of_week"] = hourly["hour_bucket"].dt.dayofweek
    hourly["zone_code"] = hourly["zone"].map(ZONE_CODES)
    hourly["occupancy_pct"] = hourly["occupancy_pct"].round(2)
    hourly["occupancy_level"] = hourly["occupancy_pct"].map(occupancy_level)
    return hourly


def train_decision_tree(dataset, max_depth=4, test_size=0.25):
    """
    Train and evaluate a Decision Tree. Raises ValueError if the data is not suitable.
    Returns a dictionary with the model, accuracy, confusion matrix and more.
    """
    if len(dataset) < config.MIN_RECORDS_TREE:
        raise ValueError(
            f"The Decision Tree needs at least {config.MIN_RECORDS_TREE} (hour, zone) records "
            f"but only {len(dataset)} exist. Generate simulated history in the sidebar or let the simulation run longer."
        )

    class_counts = dataset["occupancy_level"].value_counts()
    if len(class_counts) < 2:
        raise ValueError(
            "All records belong to one occupancy level "
            f"('{class_counts.index[0]}'). A classifier needs at least 2 different levels to learn from."
        )

    X = dataset[TREE_FEATURES]
    y = dataset["occupancy_level"]

    stratify = y if class_counts.min() >= 2 else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=stratify
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    model = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    levels = [level for level in config.LEVELS if level in set(model.classes_)]
    accuracy = float(accuracy_score(y_test, predictions))
    baseline = float((y_test == y_train.mode().iloc[0]).mean())   # always guess the commonest level

    matrix = pd.DataFrame(
        confusion_matrix(y_test, predictions, labels=levels),
        index=[f"Actual {level}" for level in levels],
        columns=[f"Predicted {level}" for level in levels],
    )
    report = pd.DataFrame(
        classification_report(y_test, predictions, labels=levels, output_dict=True, zero_division=0)
    ).T
    report = report.loc[levels, ["precision", "recall", "f1-score", "support"]].round(2)

    importance = pd.Series(model.feature_importances_, index=TREE_FEATURES).sort_values(ascending=False)

    warnings = []
    if len(X_test) < 20:
        warnings.append("The test set is very small, so the accuracy is not very reliable.")
    if accuracy <= baseline:
        warnings.append("The model is not better than always guessing the most common level.")
    if class_counts.min() < 5:
        warnings.append("One occupancy level has fewer than 5 records, so it is hard to learn.")

    return {
        "model": model,
        "accuracy": accuracy,
        "baseline_accuracy": baseline,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "confusion_matrix": matrix,
        "report": report,
        "importance": importance,
        "rules": export_text(model, feature_names=TREE_FEATURES),
        "class_counts": class_counts,
        "warnings": warnings,
    }


def predict_level(model, zone, hour, day_of_week):
    """Predict the occupancy level for one zone / hour / weekday. Returns (level, probabilities)."""
    row = pd.DataFrame([[hour, day_of_week, ZONE_CODES[zone]]], columns=TREE_FEATURES)
    level = str(model.predict(row)[0])
    probabilities = {
        str(name): round(float(value), 3)
        for name, value in zip(model.classes_, model.predict_proba(row)[0])
    }
    return level, probabilities


# ============================================================================
# 3. OUTLIER DETECTION
# ============================================================================
def detect_outliers(history_df, method="IQR", sensitivity=1.5):
    """
    Find unusual zone-occupancy records (one record = one zone at one timestamp).
      method "IQR"     : outside  Q1 - s*IQR  ...  Q3 + s*IQR   (s = sensitivity, usually 1.5)
      method "Z-score" : more than s standard deviations away from the zone's mean
    The bounds are calculated separately for every zone.
    Returns (records_df, summary_df).
    """
    zone_data = analytics.zone_snapshot_occupancy(history_df)
    if zone_data.empty:
        raise ValueError("There is no history data yet.")

    counts = zone_data.groupby("zone").size()
    if counts.min() < config.MIN_RECORDS_OUTLIER:
        raise ValueError(
            f"Outlier detection needs at least {config.MIN_RECORDS_OUTLIER} records per zone, "
            f"but the smallest zone has only {int(counts.min())}."
        )

    parts = []
    for zone, group in zone_data.groupby("zone"):
        group = group.copy()
        values = group["occupancy_pct"]

        if method == "Z-score":
            mean, std = values.mean(), values.std()
            lower, upper = mean - sensitivity * std, mean + sensitivity * std
            has_spread = std > 0
        else:
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - sensitivity * iqr, q3 + sensitivity * iqr
            has_spread = iqr > 0

        group["lower_bound"] = round(float(lower), 2)
        group["upper_bound"] = round(float(upper), 2)
        if has_spread:
            group["is_outlier"] = (values < lower) | (values > upper)
        else:
            group["is_outlier"] = False       # all values identical -> nothing is unusual
        parts.append(group)

    records = pd.concat(parts, ignore_index=True)
    records["label"] = np.where(records["is_outlier"], "Outlier", "Normal")

    summary = records.groupby("zone_label", as_index=False).agg(
        records=("is_outlier", "size"),
        outliers=("is_outlier", "sum"),
        lower_bound=("lower_bound", "first"),
        upper_bound=("upper_bound", "first"),
    )
    summary["outlier_percent"] = (summary["outliers"] / summary["records"] * 100).round(2)
    return records, summary
