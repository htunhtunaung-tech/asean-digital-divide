"""SYNTHETIC test data — for automated tests only, never for analysis.

Generates a raw CSV in exactly the shape fetch_data.py produces, with deliberate
problems (gaps, a long gap, a negative value, a duplicate row) so every cleaning
rule gets exercised. The numbers are made up and must not appear in any report.
"""
import numpy as np
import pandas as pd

from src import config


def make_raw(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    years = np.arange(config.START_YEAR, config.END_YEAR + 1)
    rows = []
    for i, (iso, name) in enumerate(config.COUNTRIES.items()):
        mid = 2008 + i * 1.2                 # year a country passes ~50% internet use
        internet = 95 / (1 + np.exp(-(years - mid) / 3))
        gdp = 3000 * (1 + i * 0.6) * np.cumprod(1 + rng.normal(0.04, 0.03, len(years)))
        urban = 20 + 4 * i + np.cumsum(rng.normal(0.4, 0.3, len(years)))
        enroll = 45 + 0.25 * internet + 3 * np.log(gdp / 3000) + rng.normal(0, 2, len(years))
        series = {
            "IT.NET.USER.ZS": internet,
            "IT.CEL.SETS.P2": internet * 1.3,
            "NY.GDP.PCAP.PP.KD": gdp,
            "SP.URB.TOTL.IN.ZS": urban,
            "SE.SEC.ENRR": enroll,
            "SE.PRM.CMPT.ZS": 70 + 0.2 * internet,
            "SE.XPD.TOTL.GD.ZS": 2.5 + 0.1 * i + rng.normal(0, 0.2, len(years)),
        }
        for code, vals in series.items():
            vals = vals.astype(float).copy()
            # education data is patchy in reality: drop ~35% of years at random
            if code.startswith("SE."):
                vals[rng.random(len(vals)) < 0.35] = np.nan
            for y, v in zip(years, vals):
                rows.append({"iso3": iso, "country": name, "year": int(y),
                             "indicator_code": code, "value": None if np.isnan(v) else v})
    raw = pd.DataFrame(rows)
    # deliberate problems
    long_gap = (raw["iso3"] == "MMR") & (raw["indicator_code"] == "SE.SEC.ENRR") & raw["year"].between(2005, 2012)
    raw.loc[long_gap, "value"] = None
    raw.loc[raw.index[5], "value"] = -4.0
    raw = pd.concat([raw, raw.iloc[[10]]], ignore_index=True)
    return raw
