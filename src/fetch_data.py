"""Step 1 — Download raw indicators from the World Bank API.

Pulls every indicator in config.INDICATORS for every country in
config.COUNTRIES and saves one tidy long-format CSV:

    data/raw/wdi_raw.csv   columns: iso3, country, year, indicator_code, value

The raw file is never edited by hand; all cleaning happens in clean.py.

Usage:
    python -m src.fetch_data
"""
from __future__ import annotations

import time

import pandas as pd
import requests

from . import config

API = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"


def fetch_indicator(code: str, retries: int = 3) -> pd.DataFrame:
    """Fetch one indicator for all study countries, following pagination."""
    url = API.format(countries=";".join(config.COUNTRIES), indicator=code)
    params = {
        "format": "json",
        "date": f"{config.START_YEAR}:{config.END_YEAR}",
        "per_page": 1000,
        "page": 1,
    }
    rows: list[dict] = []
    while True:
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                break
            except (requests.RequestException, ValueError) as err:
                if attempt == retries - 1:
                    raise RuntimeError(f"Failed to fetch {code}: {err}") from err
                time.sleep(2 ** attempt)

        if len(payload) < 2 or payload[1] is None:
            # The API returns [{"message": ...}] for an unknown indicator.
            raise RuntimeError(f"No data returned for {code}: {payload[0]}")

        meta, records = payload
        for r in records:
            rows.append(
                {
                    "iso3": r["countryiso3code"],
                    "country": config.COUNTRIES.get(r["countryiso3code"], r["country"]["value"]),
                    "year": int(r["date"]),
                    "indicator_code": code,
                    "value": r["value"],
                }
            )
        if params["page"] >= int(meta["pages"]):
            break
        params["page"] += 1

    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    frames = []
    for code, name in config.INDICATORS.items():
        df = fetch_indicator(code)
        n_obs = df["value"].notna().sum()
        print(f"  {code:<20} {name:<22} {n_obs:>4} non-missing values")
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    out = config.DATA_RAW / "wdi_raw.csv"
    raw.to_csv(out, index=False)
    print(f"Saved {len(raw):,} rows -> {out.relative_to(config.ROOT)}")
    return raw


if __name__ == "__main__":
    main()
