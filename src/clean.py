"""Step 2 — Clean the raw World Bank data into an analysis-ready panel.

Input : data/raw/wdi_raw.csv          (long format, straight from the API)
Output: data/processed/panel_clean.csv  one row per country-year, one column per
                                        indicator, plus *_imputed flag columns
        reports/missing_report.csv      % missing per country x indicator (before filling)
        reports/cleaning_log.md         every cleaning decision, with counts

Cleaning rules (each one is logged with how many cells it touched):
  1. Keep only study countries and years; drop exact duplicate rows.
  2. Coerce values to numbers; impossible values become missing
     (negatives anywhere; >100 for indicators that are true percentages).
  3. Reshape long -> wide (country-year panel).
  4. Fill gaps by linear interpolation *within a country only*, only between two
     observed values (no extrapolation), and only for gaps of at most
     config.MAX_INTERP_GAP years. Every filled cell is flagged.
  5. Add derived columns (log GDP per capita).

Usage:
    python -m src.clean
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# Indicators that cannot exceed 100. Gross enrollment, completion rate and mobile
# subscriptions legitimately can (over-age students, multiple SIMs), so they are
# only checked for negatives.
TRUE_PERCENTAGES = {"internet_users_pct", "urban_pct", "edu_spend_gdp_pct"}


class CleaningLog:
    """Collects human-readable notes about each cleaning step."""

    def __init__(self) -> None:
        self.lines: list[str] = ["# Cleaning log", ""]

    def add(self, step: str, detail: str) -> None:
        self.lines.append(f"- **{step}:** {detail}")
        print(f"  [{step}] {detail}")

    def write(self, path) -> None:
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def interpolate_with_gap_limit(s: pd.Series, max_gap: int) -> tuple[pd.Series, pd.Series]:
    """Linear interpolation inside a single country's time series.

    Only fills runs of missing years that (a) sit between two observed values and
    (b) are no longer than ``max_gap``. Returns the filled series and a boolean
    mask marking which cells were filled.
    """
    filled = s.interpolate(method="linear", limit_area="inside")
    was_missing = s.isna()

    # Measure the length of each consecutive run of missing values.
    run_id = (was_missing != was_missing.shift()).cumsum()
    run_len = was_missing.groupby(run_id).transform("sum")
    too_long = was_missing & (run_len > max_gap)

    filled[too_long] = np.nan
    imputed = was_missing & filled.notna()
    return filled, imputed


def main() -> pd.DataFrame:
    log = CleaningLog()
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.REPORTS.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(config.DATA_RAW / "wdi_raw.csv")
    log.add("Load", f"{len(raw):,} raw rows, {raw['iso3'].nunique()} countries, "
                    f"{raw['indicator_code'].nunique()} indicators")

    # 1. Scope and duplicates
    n0 = len(raw)
    raw = raw[raw["iso3"].isin(config.COUNTRIES)]
    raw = raw[raw["year"].between(config.START_YEAR, config.END_YEAR)]
    raw = raw[raw["indicator_code"].isin(config.INDICATORS)]
    log.add("Scope", f"dropped {n0 - len(raw)} rows outside study countries/years/indicators")

    n0 = len(raw)
    raw = raw.drop_duplicates(subset=["iso3", "year", "indicator_code"], keep="first")
    log.add("Duplicates", f"dropped {n0 - len(raw)} duplicate country-year-indicator rows")

    raw["indicator"] = raw["indicator_code"].map(config.INDICATORS)
    raw["country"] = raw["iso3"].map(config.COUNTRIES)  # one consistent name per code

    # 2. Numeric coercion and validity checks
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    neg = raw["value"] < 0
    over = raw["indicator"].isin(TRUE_PERCENTAGES) & (raw["value"] > 100)
    raw.loc[neg | over, "value"] = np.nan
    log.add("Validity", f"set {int(neg.sum())} negative and {int(over.sum())} >100% values to missing")

    # 3. Long -> wide panel on a complete country x year grid
    wide = raw.pivot_table(index=["iso3", "country", "year"], columns="indicator",
                           values="value", aggfunc="first").reset_index()
    grid = pd.MultiIndex.from_product(
        [list(config.COUNTRIES), range(config.START_YEAR, config.END_YEAR + 1)],
        names=["iso3", "year"],
    ).to_frame(index=False)
    grid["country"] = grid["iso3"].map(config.COUNTRIES)
    panel = grid.merge(wide, on=["iso3", "country", "year"], how="left")
    indicator_cols = [c for c in config.INDICATORS.values() if c in panel.columns]
    missing_cols = sorted(set(config.INDICATORS.values()) - set(indicator_cols))
    for col in missing_cols:  # an indicator with zero data still gets a column
        panel[col] = np.nan
    indicator_cols = list(config.INDICATORS.values())
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)
    log.add("Reshape", f"panel of {len(panel)} country-years x {len(indicator_cols)} indicators")

    # Missingness report BEFORE any filling — this is the honest picture of the data.
    missing = (panel.groupby("country")[indicator_cols]
               .apply(lambda g: g.isna().mean() * 100).round(1))
    missing.to_csv(config.REPORTS / "missing_report.csv")
    total_missing = panel[indicator_cols].isna().sum().sum()
    log.add("Missing (before)", f"{int(total_missing)} of {panel[indicator_cols].size} cells "
                                f"({total_missing / panel[indicator_cols].size:.1%}) missing")

    # 4. Within-country interpolation with a gap limit
    filled_count = 0
    for col in indicator_cols:
        flags = pd.Series(False, index=panel.index)
        for _, idx in panel.groupby("iso3").groups.items():
            filled, imputed = interpolate_with_gap_limit(panel.loc[idx, col], config.MAX_INTERP_GAP)
            panel.loc[idx, col] = filled
            flags.loc[idx] = imputed
        panel[f"{col}_imputed"] = flags
        filled_count += int(flags.sum())
    still_missing = panel[indicator_cols].isna().sum().sum()
    log.add("Interpolation", f"filled {filled_count} cells (gaps <= {config.MAX_INTERP_GAP} years, "
                             f"within-country, no extrapolation); {int(still_missing)} cells left missing")

    # 5. Derived columns
    panel["log_gdp_pc"] = np.log(panel["gdp_pc_ppp"])
    log.add("Derived", "added log_gdp_pc = ln(GDP per capita, PPP)")

    out = config.DATA_PROCESSED / "panel_clean.csv"
    panel.to_csv(out, index=False)
    log.add("Saved", f"{out.relative_to(config.ROOT)}")
    log.write(config.REPORTS / "cleaning_log.md")
    return panel


if __name__ == "__main__":
    main()
