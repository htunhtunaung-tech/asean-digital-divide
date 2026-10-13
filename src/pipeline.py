"""Run the whole project end to end.

    python -m src.pipeline              # download fresh data, then everything else
    python -m src.pipeline --skip-fetch # reuse data/raw/wdi_raw.csv
"""
import argparse
import time

from . import clean, eda, fetch_data, model, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-fetch", action="store_true",
                        help="reuse the existing raw CSV instead of calling the World Bank API")
    args = parser.parse_args()

    steps = [("Clean", clean.main), ("Explore", eda.main),
             ("Model", model.main), ("Report", report.main)]
    if not args.skip_fetch:
        steps.insert(0, ("Fetch", fetch_data.main))

    t0 = time.time()
    for i, (name, fn) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {name}")
        fn()
    print(f"\nDone in {time.time() - t0:.1f}s. Launch the dashboard with: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
