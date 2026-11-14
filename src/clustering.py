
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from config import OUTPUT_DIR


# ==========================================
# SETTINGS
# ==========================================

INPUT_FILE = OUTPUT_DIR / "all_cities_trend_results.csv"

CLUSTER_OUTPUT = OUTPUT_DIR / "city_clusters.csv"
METRICS_OUTPUT = OUTPUT_DIR / "clustering_metrics.csv"
CENTERS_OUTPUT = OUTPUT_DIR / "cluster_centers.csv"
PLOT_OUTPUT = OUTPUT_DIR / "clustering_evaluation.png"

FEATURES = [
    "precipitation",
    "soil_moisture"
]

PERCENTAGE_COLUMN = "pct_per_decade"

MIN_K = 2
MAX_K = 10
RANDOM_STATE = 42


# ==========================================
# LOAD AND PREPARE DATA
# ==========================================

def prepare_clustering_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Trend results not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "city",
        "variable",
        PERCENTAGE_COLUMN
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    df[PERCENTAGE_COLUMN] = pd.to_numeric(
        df[PERCENTAGE_COLUMN],
        errors="coerce"
    )

    # Convert long-format data into one row per city
    pivot_df = df.pivot(
        index="city",
        columns="variable",
        values=PERCENTAGE_COLUMN
    ).reset_index()

    pivot_df.columns.name = None

    missing_features = [
        feature for feature in FEATURES
        if feature not in pivot_df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing feature variables: {missing_features}"
        )

    # Keep cities with both percentage values available
    pivot_df = pivot_df.dropna(
        subset=FEATURES
    ).copy()

    pivot_df = pivot_df.replace(
        [np.inf, -np.inf],
        np.nan
    ).dropna(subset=FEATURES)

    if len(pivot_df) < 3:
        raise ValueError(
            "At least 3 cities with complete data are required."
        )

    return pivot_df


# ==========================================
# ELBOW AND SILHOUETTE EVALUATION
# ==========================================

def evaluate_cluster_numbers(X_scaled):

    number_of_cities = len(X_scaled)

    max_k = min(
        MAX_K,
        number_of_cities - 1
    )

    metrics = []

    for k in range(MIN_K, max_k + 1):

        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=20
        )

        labels = model.fit_predict(X_scaled)

        # Avoid invalid silhouette calculation
        if len(np.unique(labels)) < 2:
            continue

        score = silhouette_score(
            X_scaled,
            labels
        )

        metrics.append({
            "k": k,
            "inertia": model.inertia_,
            "silhouette_score": score
        })

        print(
            f"K={k} | "
            f"Inertia={model.inertia_:.4f} | "
            f"Silhouette={score:.4f}"
        )

    metrics_df = pd.DataFrame(metrics)

    if metrics_df.empty:
        raise RuntimeError(
            "Could not calculate clustering evaluation metrics."
        )

    return metrics_df


# ==========================================
# PLOT EVALUATION
# ==========================================

def save_evaluation_plot(metrics_df):

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12, 5)
    )

    axes[0].plot(
        metrics_df["k"],
        metrics_df["inertia"],
        marker="o"
    )

    axes[0].set_title("Elbow Method")
    axes[0].set_xlabel("Number of Clusters (K)")
    axes[0].set_ylabel("Inertia")
    axes[0].grid(True)

    axes[1].plot(
        metrics_df["k"],
        metrics_df["silhouette_score"],
        marker="o"
    )

    axes[1].set_title("Silhouette Score")
    axes[1].set_xlabel("Number of Clusters (K)")
    axes[1].set_ylabel("Silhouette Score")
    axes[1].grid(True)

    plt.tight_layout()

    plt.savefig(
        PLOT_OUTPUT,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("\nEvaluation plot saved:")
    print(PLOT_OUTPUT)


# ==========================================
# FINAL K-MEANS CLUSTERING
# ==========================================

def perform_clustering(pivot_df, metrics_df):

    # Highest silhouette score selects final K
    best_row = metrics_df.loc[
        metrics_df["silhouette_score"].idxmax()
    ]

    best_k = int(best_row["k"])

    print("\n======================================")
    print("BEST CLUSTER COUNT")
    print("======================================")

    print("Selected K:", best_k)
    print(
        "Best silhouette score:",
        round(best_row["silhouette_score"], 4)
    )

    # Standardize percentage features
    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        pivot_df[FEATURES]
    )

    # Final K-means model
    final_model = KMeans(
        n_clusters=best_k,
        random_state=RANDOM_STATE,
        n_init=20
    )

    pivot_df = pivot_df.copy()

    pivot_df["cluster"] = final_model.fit_predict(
        X_scaled
    )

    pivot_df["cluster"] = (
        pivot_df["cluster"] + 1
    )

    # Cluster centers in original percentage units
    original_centers = scaler.inverse_transform(
        final_model.cluster_centers_
    )

    centers_df = pd.DataFrame(
        original_centers,
        columns=[
            "precipitation_pct_per_decade",
            "soil_moisture_pct_per_decade"
        ]
    )

    centers_df.insert(
        0,
        "cluster",
        range(1, best_k + 1)
    )

    return pivot_df, centers_df, best_k


# ==========================================
# SAVE RESULTS
# ==========================================

def save_results(
    clustered_df,
    centers_df,
    metrics_df
):

    clustered_df = clustered_df.rename(
        columns={
            "precipitation":
                "precipitation_pct_per_decade",
            "soil_moisture":
                "soil_moisture_pct_per_decade"
        }
    )

    clustered_df.to_csv(
        CLUSTER_OUTPUT,
        index=False
    )

    centers_df.to_csv(
        CENTERS_OUTPUT,
        index=False
    )

    metrics_df.to_csv(
        METRICS_OUTPUT,
        index=False
    )

    print("\n======================================")
    print("SAVED CLUSTERING FILES")
    print("======================================")

    print(CLUSTER_OUTPUT)
    print(CENTERS_OUTPUT)
    print(METRICS_OUTPUT)


# ==========================================
# MAIN FUNCTION
# ==========================================

def run_clustering():

    print("\n======================================")
    print("CITY CLUSTERING ANALYSIS")
    print("======================================")

    pivot_df = prepare_clustering_data()

    print(
        "\nCities available for clustering:",
        len(pivot_df)
    )

    print("\nEvaluating different K values...")

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        pivot_df[FEATURES]
    )

    metrics_df = evaluate_cluster_numbers(
        X_scaled
    )

    metrics_df.to_csv(
        METRICS_OUTPUT,
        index=False
    )

    save_evaluation_plot(metrics_df)

    clustered_df, centers_df, best_k = perform_clustering(
        pivot_df,
        metrics_df
    )

    save_results(
        clustered_df,
        centers_df,
        metrics_df
    )

    print("\n======================================")
    print("CLUSTERING SUMMARY")
    print("======================================")

    print("Total cities:", len(clustered_df))
    print("Selected clusters:", best_k)

    print("\nCities in each cluster:")

    print(
        clustered_df.groupby("cluster")["city"].apply(
            lambda cities: ", ".join(cities)
        ).to_string()
    )

    print("\nCluster centers:")

    print(centers_df.to_string(index=False))

    print("\nClustering completed successfully!")

    return clustered_df


if __name__ == "__main__":

    try:
        run_clustering()

    except Exception as error:
        print("\nCLUSTERING ERROR:", error)
