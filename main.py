
import argparse
import importlib
import runpy
import sys

from config import OUTPUT_DIR


def run_module(module_name, function_name=None):
    """
    Run a module only once.
    If function_name is provided, import the module
    and execute that function.
    Otherwise, run the module as a script.
    """

    print("\n" + "=" * 65)
    print(f"RUNNING: {module_name}")
    print("=" * 65)

    try:
        if function_name:
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
            function()
        else:
            runpy.run_module(module_name, run_name="__main__")

        print(f"\nSUCCESS: {module_name}")

    except Exception as error:
        print(f"\nERROR in {module_name}: {error}")
        raise


def run_analysis():
    """Run analysis using collected and cleaned data."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nNASA EARTH SYSTEM TREND DETECTIVE")
    print("Starting data science analysis pipeline...")

    run_module("src.statistics_analysis")
    run_module("src.manual_validation")
    run_module("src.forecasting")

    run_module(
        "src.opposite_trends",
        function_name="find_opposite_trends"
    )

    run_module("src.clustering")

    print("\n" + "=" * 65)
    print("ALL ANALYSIS TASKS COMPLETED SUCCESSFULLY!")
    print("=" * 65)

    print("\nMain output folder:")
    print(OUTPUT_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="NASA Earth System Trend Detective"
    )

    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run NASA POWER data collection"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Run data cleaning"
    )

    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Run all analysis stages"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run collection, cleaning and analysis"
    )

    args = parser.parse_args()

    try:
        if args.all:
            run_module("src.data_collection")
            run_module("src.data_cleaning")
            run_analysis()

        elif args.collect:
            run_module("src.data_collection")

        elif args.clean:
            run_module("src.data_cleaning")

        elif args.analysis:
            run_analysis()

        else:
            parser.print_help()

    except Exception:
        print("\nPipeline stopped because an error occurred.")
        sys.exit(1)


if __name__ == "__main__":
    main()
