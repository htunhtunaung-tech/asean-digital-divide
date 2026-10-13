"""End-to-end test of the pipeline on synthetic data (no network needed).

    pytest -q
"""
import numpy as np
import pandas as pd
import pytest

from src import clean, config, eda, model, report
from src.clean import interpolate_with_gap_limit
from tests.fixture import make_raw


@pytest.fixture()
def project(tmp_path, monkeypatch):
    for attr, sub in [("DATA_RAW", "data/raw"), ("DATA_PROCESSED", "data/processed"),
                      ("REPORTS", "reports"), ("FIGURES", "reports/figures")]:
        p = tmp_path / sub
        p.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(config, attr, p)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    make_raw().to_csv(config.DATA_RAW / "wdi_raw.csv", index=False)
    return tmp_path


def test_interpolation_respects_gap_limit():
    s = pd.Series([1.0, np.nan, 3.0, np.nan, np.nan, np.nan, np.nan, 8.0, np.nan])
    filled, flags = interpolate_with_gap_limit(s, max_gap=3)
    assert filled[1] == 2.0 and flags[1]                 # short gap filled
    assert filled[3:7].isna().all()                      # 4-year gap left alone
    assert np.isnan(filled[8]) and not flags[8]          # no extrapolation


def test_full_pipeline(project):
    panel = clean.main()
    assert len(panel) == len(config.COUNTRIES) * (config.END_YEAR - config.START_YEAR + 1)
    assert not panel.duplicated(["iso3", "year"]).any()
    assert (panel[list(config.INDICATORS.values())].min() >= 0).all()
    # the deliberate 8-year gap for Myanmar enrollment must stay missing
    mmr = panel[(panel.iso3 == "MMR") & panel.year.between(2005, 2012)]
    assert mmr["sec_enroll_gross"].isna().all()

    eda.main()
    table, clusters, scores = model.main()
    assert set(clusters["iso3"]) == set(config.COUNTRIES)
    # the synthetic data has a true effect of +2.5 per 10pp internet; pooled OLS should be positive
    pooled = table[(table.model.str.startswith("(1)")) & (table.variable == "internet_10pp")]
    assert pooled["coef"].iloc[0] > 0

    md = report.main()
    assert "Findings" in md and "n/a" not in md.split("## 3.")[0].split("## 2.")[0]
    for f in ["internet_trends.png", "missing_heatmap.png", "correlation_heatmap.png",
              "internet_vs_enrollment.png", "clusters.png"]:
        assert (config.FIGURES / f).stat().st_size > 10_000
