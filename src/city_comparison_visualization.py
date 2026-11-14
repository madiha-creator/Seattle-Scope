
from pathlib import Path
import argparse

import matplotlib.pyplot as plt

from src.city_comparison import compare_two_cities


def create_comparison_graphs(city1, city2):

    print("\n" + "=" * 60)
    print("TWO-CITY COMPARISON VISUALIZATION")
    print("=" * 60)

    # Get data from existing comparison module
    results = compare_two_cities(city1, city2)

    city1 = results["city1"]
    city2 = results["city2"]

    # Correct dictionary keys
    monthly_df = results["monthly"]
    annual_df = results["annual"]
    forecast_df = results["forecasts"]

    # Create output folder
    graph_dir = Path("outputs/city_comparisons/graphs")
    graph_dir.mkdir(parents=True, exist_ok=True)

    def save_graph(filename):
        plt.tight_layout()
        plt.savefig(
            graph_dir / filename,
            dpi=300,
            bbox_inches="tight"
        )
        plt.close()
        print(f"Saved: {filename}")

    # GRAPH 1: Monthly Precipitation
    plt.figure(figsize=(13, 6))

    plt.plot(
        monthly_df["date"],
        monthly_df[f"{city1}_precipitation"],
        label=city1
    )

    plt.plot(
        monthly_df["date"],
        monthly_df[f"{city2}_precipitation"],
        label=city2
    )

    plt.title(f"Monthly Precipitation: {city1} vs {city2}")
    plt.xlabel("Year")
    plt.ylabel("Precipitation (mm/day)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_monthly_precipitation.png")

    # GRAPH 2: Monthly Soil Moisture
    plt.figure(figsize=(13, 6))

    plt.plot(
        monthly_df["date"],
        monthly_df[f"{city1}_soil_moisture"],
        label=city1
    )

    plt.plot(
        monthly_df["date"],
        monthly_df[f"{city2}_soil_moisture"],
        label=city2
    )

    plt.title(f"Monthly Soil Moisture: {city1} vs {city2}")
    plt.xlabel("Year")
    plt.ylabel("Root-Zone Soil Moisture (0–1)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_monthly_soil_moisture.png")

    # GRAPH 3: Annual Precipitation
    plt.figure(figsize=(12, 6))

    plt.plot(
        annual_df["year"],
        annual_df[f"{city1}_precipitation"],
        marker="o",
        label=city1
    )

    plt.plot(
        annual_df["year"],
        annual_df[f"{city2}_precipitation"],
        marker="o",
        label=city2
    )

    plt.title(f"Annual Precipitation: {city1} vs {city2}")
    plt.xlabel("Year")
    plt.ylabel("Average Precipitation (mm/day)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_annual_precipitation.png")

    # GRAPH 4: Annual Soil Moisture
    plt.figure(figsize=(12, 6))

    plt.plot(
        annual_df["year"],
        annual_df[f"{city1}_soil_moisture"],
        marker="o",
        label=city1
    )

    plt.plot(
        annual_df["year"],
        annual_df[f"{city2}_soil_moisture"],
        marker="o",
        label=city2
    )

    plt.title(f"Annual Soil Moisture: {city1} vs {city2}")
    plt.xlabel("Year")
    plt.ylabel("Average Soil Moisture (0–1)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_annual_soil_moisture.png")

    # GRAPH 5: Future Precipitation Projection
    plt.figure(figsize=(12, 6))

    plt.plot(
        forecast_df["date"],
        forecast_df[f"{city1}_precipitation"],
        label=city1
    )

    plt.plot(
        forecast_df["date"],
        forecast_df[f"{city2}_precipitation"],
        label=city2
    )

    plt.title(
        f"Precipitation Projection (2026–2035): {city1} vs {city2}"
    )
    plt.xlabel("Year")
    plt.ylabel("Projected Precipitation (mm/day)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_future_precipitation.png")

    # GRAPH 6: Future Soil Moisture Projection
    plt.figure(figsize=(12, 6))

    plt.plot(
        forecast_df["date"],
        forecast_df[f"{city1}_soil_moisture"],
        label=city1
    )

    plt.plot(
        forecast_df["date"],
        forecast_df[f"{city2}_soil_moisture"],
        label=city2
    )

    plt.title(
        f"Soil Moisture Projection (2026–2035): {city1} vs {city2}"
    )
    plt.xlabel("Year")
    plt.ylabel("Projected Soil Moisture (0–1)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    save_graph(f"{city1}_vs_{city2}_future_soil_moisture.png")

    print("\n" + "=" * 60)
    print("ALL COMPARISON GRAPHS CREATED SUCCESSFULLY!")
    print("=" * 60)

    print(f"Graph folder: {graph_dir.resolve()}")
    print("\nNote: Future projections are indicative estimates,")
    print("not operational weather forecasts.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Visualize comparison between two cities"
    )

    parser.add_argument(
        "--city1",
        default="Islamabad",
        help="First city name"
    )

    parser.add_argument(
        "--city2",
        default="London",
        help="Second city name"
    )

    args = parser.parse_args()

    create_comparison_graphs(args.city1, args.city2)
