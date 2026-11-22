"""
visualization.py
----------------
All Plotly charts and the HTML parking grid live here.
Each function receives a DataFrame and RETURNS a figure; the pages show it
with st.plotly_chart(). Colours: green = available, red = occupied, blue = info.
"""

import plotly.express as px
import plotly.graph_objects as go

import analytics
import config

CLUSTER_COLORS = {
    "Low Usage": config.COLOR_AVAILABLE,
    "Medium Usage": config.COLOR_INFO,
    "High Usage": config.COLOR_OCCUPIED,
}


def _style(fig, title=None, height=380):
    """Apply the same clean look to every chart."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=60 if title else 30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=13),
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.01))
    return fig


# ----------------------------------------------------------------------------
# Dashboard / zone charts
# ----------------------------------------------------------------------------
def occupancy_gauge(percentage):
    """Round gauge that shows the current occupancy percentage."""
    _, color = analytics.availability_status(percentage)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=percentage,
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, config.LOW_MAX], "color": "#dcfce7"},
                    {"range": [config.LOW_MAX, config.MEDIUM_MAX], "color": "#dbeafe"},
                    {"range": [config.MEDIUM_MAX, 100], "color": "#fee2e2"},
                ],
            },
        )
    )
    return _style(fig, "Current Occupancy", height=300)


def status_donut(occupied, available):
    """Donut chart: occupied (red) versus available (green)."""
    fig = go.Figure(
        go.Pie(
            labels=[config.STATUS_OCCUPIED, config.STATUS_AVAILABLE],
            values=[occupied, available],
            hole=0.55,
            marker=dict(colors=[config.COLOR_OCCUPIED, config.COLOR_AVAILABLE]),
            sort=False,
        )
    )
    return _style(fig, "Occupied vs Available", height=300)


def zone_stacked_bar(zone_df):
    """Bars with occupied and available spaces for every zone."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=zone_df["zone_label"], y=zone_df["occupied"], name="Occupied",
                         marker_color=config.COLOR_OCCUPIED))
    fig.add_trace(go.Bar(x=zone_df["zone_label"], y=zone_df["available"], name="Available",
                         marker_color=config.COLOR_AVAILABLE))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Parking spaces")
    return _style(fig, "Spaces by Zone", height=320)


def zone_percentage_bar(zone_df):
    """Bar chart of occupancy % per zone (colour depends on how full it is)."""
    colors = [analytics.availability_status(value)[1] for value in zone_df["occupancy_pct"]]
    fig = go.Figure(
        go.Bar(
            x=zone_df["zone_label"],
            y=zone_df["occupancy_pct"],
            marker_color=colors,
            text=[f"{value:.0f}%" for value in zone_df["occupancy_pct"]],
            textposition="outside",
        )
    )
    fig.update_yaxes(title="Occupancy (%)", range=[0, 115])
    return _style(fig, "Occupancy % by Zone", height=320)


# ----------------------------------------------------------------------------
# Usage analytics charts
# ----------------------------------------------------------------------------
def trend_line(df, y_column, title, color, y_title):
    """Single line over time (used for occupancy %)."""
    fig = px.line(df, x="timestamp", y=y_column, markers=len(df) <= 60)
    fig.update_traces(line_color=color)
    fig.update_xaxes(title="Time")
    fig.update_yaxes(title=y_title)
    return _style(fig, title)


def availability_area(df, y_column, title):
    """Filled area chart (used for available spaces)."""
    fig = px.area(df, x="timestamp", y=y_column)
    fig.update_traces(line_color=config.COLOR_AVAILABLE)
    fig.update_xaxes(title="Time")
    fig.update_yaxes(title="Available spaces")
    return _style(fig, title)


def zone_trend_lines(df):
    """One line per zone over time."""
    color_map = {analytics.zone_label(z): c for z, c in config.ZONE_COLORS.items()}
    fig = px.line(df, x="timestamp", y="occupancy_pct", color="zone_label",
                  color_discrete_map=color_map)
    fig.update_xaxes(title="Time")
    fig.update_yaxes(title="Occupancy (%)", range=[0, 105])
    return _style(fig, "Zone-wise Occupancy Trend", height=400)


def hourly_bar(pattern_df, peak_hours):
    """Average occupancy for each hour of the day; peak hours are red."""
    colors = [config.COLOR_OCCUPIED if hour in peak_hours else config.COLOR_INFO for hour in pattern_df["hour"]]
    fig = go.Figure(go.Bar(x=pattern_df["hour_label"], y=pattern_df["avg_occupancy"], marker_color=colors))
    fig.update_xaxes(title="Hour of day")
    fig.update_yaxes(title="Average occupancy (%)", range=[0, 105])
    return _style(fig, "Average Occupancy by Hour (red = peak hours)")


def weekday_heatmap(matrix_df):
    """Heatmap: weekday (rows) x hour (columns)."""
    fig = go.Figure(
        go.Heatmap(
            z=matrix_df.values,
            x=[f"{int(h):02d}:00" for h in matrix_df.columns],
            y=list(matrix_df.index),
            colorscale=[[0, "#dcfce7"], [0.5, "#fef08a"], [1, "#dc2626"]],
            zmin=0, zmax=100,
            colorbar=dict(title="Occupancy %"),
        )
    )
    return _style(fig, "Occupancy Heatmap (weekday x hour)", height=400)


def zone_usage_bar(usage_df):
    """Average occupancy of every zone."""
    colors = [config.ZONE_COLORS.get(z, config.COLOR_INFO) for z in usage_df["zone"]]
    fig = go.Figure(
        go.Bar(
            x=usage_df["zone_label"],
            y=usage_df["avg_occupancy"],
            marker_color=colors,
            text=[f"{value:.1f}%" for value in usage_df["avg_occupancy"]],
            textposition="outside",
        )
    )
    fig.update_yaxes(title="Average occupancy (%)", range=[0, 115])
    return _style(fig, "Average Usage by Zone", height=340)


def vehicle_donut(counts_df):
    """Share of vehicle types among occupied spaces."""
    fig = go.Figure(go.Pie(labels=counts_df["vehicle_type"], values=counts_df["count"], hole=0.5))
    return _style(fig, "Vehicle Types", height=340)


# ----------------------------------------------------------------------------
# Data-mining charts
# ----------------------------------------------------------------------------
def kmeans_scatter(result_df, centers_df):
    """Zones plotted by average and peak occupancy, coloured by cluster."""
    fig = px.scatter(
        result_df, x="avg_occupancy", y="peak_occupancy",
        color="cluster_label", text="zone_label",
        color_discrete_map=CLUSTER_COLORS,
    )
    fig.update_traces(marker=dict(size=20), textposition="top center")
    fig.add_trace(
        go.Scatter(
            x=centers_df["avg_occupancy"], y=centers_df["peak_occupancy"],
            mode="markers", name="Cluster centre",
            marker=dict(symbol="x", size=14, color="black"),
        )
    )
    fig.update_xaxes(title="Average occupancy (%)")
    fig.update_yaxes(title="Peak occupancy (%)")
    return _style(fig, "K-Means Clusters of Parking Zones", height=420)


def importance_bar(importance_series):
    """Which input matters most to the Decision Tree."""
    ordered = importance_series.sort_values()
    fig = go.Figure(go.Bar(x=ordered.values, y=list(ordered.index), orientation="h",
                           marker_color=config.COLOR_INFO))
    fig.update_xaxes(title="Importance")
    return _style(fig, "Feature Importance", height=280)


def confusion_heatmap(matrix_df):
    """Confusion matrix of the Decision Tree."""
    fig = px.imshow(matrix_df, text_auto=True, color_continuous_scale="Blues", aspect="auto")
    return _style(fig, "Confusion Matrix (test data)", height=340)


def outlier_scatter(records_df):
    """Zone occupancy over time; outliers are red."""
    fig = px.scatter(
        records_df, x="timestamp", y="occupancy_pct", color="label",
        facet_col="zone_label", facet_col_wrap=2,
        color_discrete_map={"Normal": "#93c5fd", "Outlier": config.COLOR_OCCUPIED},
    )
    fig.update_yaxes(range=[-5, 105])
    return _style(fig, "Outlier Detection by Zone", height=620)


def simple_bar(df, x_column, y_column, title, color=None):
    """Generic bar chart used by the Data Wrangling page."""
    fig = px.bar(df, x=x_column, y=y_column, color=color)
    return _style(fig, title, height=340)


# ----------------------------------------------------------------------------
# Parking grid (HTML + CSS, styled in assets/style.css)
# ----------------------------------------------------------------------------
def parking_grid_html(status_df, zones=None):
    """
    Build the coloured parking grid: green = available, red = occupied.
    The HTML is built without line breaks so Streamlit's markdown does not break it.
    """
    zones = zones or config.ZONES
    parts = ['<div class="zones-wrapper">']

    for zone in zones:
        zone_spaces = status_df[status_df["zone"] == zone]
        occupied = int((zone_spaces["status"] == config.STATUS_OCCUPIED).sum())
        total = len(zone_spaces)
        parts.append(
            f'<div class="zone-card"><div class="zone-title">Zone {zone}'
            f'<span class="zone-count">{total - occupied} free / {total}</span></div>'
            f'<div class="space-grid">'
        )
        for row in zone_spaces.itertuples(index=False):
            is_occupied = row.status == config.STATUS_OCCUPIED
            css_class = "occupied" if is_occupied else "available"
            vehicle = row.vehicle_type if is_occupied else "Free"
            parts.append(
                f'<div class="space {css_class}" title="{row.space_id}: {row.status}">'
                f'<div class="space-id">{row.space_id}</div>'
                f'<div class="space-vehicle">{vehicle}</div></div>'
            )
        parts.append("</div></div>")

    parts.append("</div>")
    return "".join(parts)
