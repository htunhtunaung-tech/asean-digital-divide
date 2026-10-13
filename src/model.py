"""Step 4 — Statistical modeling and clustering.

A. Panel regression (does internet access track education outcomes once we
   account for income, urbanization, and fixed country/year differences?)

   Outcome: secondary enrollment (% gross). Internet use is scaled per 10
   percentage points so the coefficient reads as "a 10-point rise in internet use
   is associated with a b-point change in enrollment".

   (1) Pooled OLS            — the naive cross-country correlation
   (2) Country FE            — compares each country with itself over time
   (3) Country + year FE     — also removes region-wide shocks/trends
   (4) (3) with internet lagged one year — a weak guard against reverse timing
   (5) (3) plus education spending — smaller sample, robustness check

   Standard errors: Driscoll–Kraay (robust to heteroskedasticity, serial and
   cross-sectional correlation). With only ~11 countries, cluster-robust errors
   are unreliable, so they are not the headline.

B. Clustering — group countries by their recent digital + education profile
   (k-means on standardized features; k chosen by silhouette score, k = 2..4).

Output:
  reports/regression_results.csv     coefficient table for all specs
  reports/regression_summary.txt     full model printouts
  reports/clusters.csv               country -> cluster, with features
  reports/cluster_selection.csv      silhouette score per k
  reports/figures/clusters.png

Usage:
    python -m src.model
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import config, style

OUTCOME = "sec_enroll_gross"
CONTROLS = ["log_gdp_pc", "urban_pct"]


# ---------------------------------------------------------------- regression
def prepare_regression_data(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel.copy().sort_values(["iso3", "year"])
    d["internet_10pp"] = d["internet_users_pct"] / 10
    d["internet_10pp_lag1"] = d.groupby("iso3")["internet_10pp"].shift(1)
    return d.set_index(["iso3", "year"])


def _fit(d: pd.DataFrame, x: list[str], entity: bool, time: bool, name: str):
    cols = [OUTCOME] + x
    sample = d[cols].dropna()
    exog = sample[x]
    if not entity and not time:
        exog = sm.add_constant(exog)
    model = PanelOLS(sample[OUTCOME], exog, entity_effects=entity, time_effects=time,
                     drop_absorbed=True, check_rank=False)
    res = model.fit(cov_type="kernel")  # Driscoll-Kraay
    return name, res


def run_regressions(panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    d = prepare_regression_data(panel)
    base = ["internet_10pp"] + CONTROLS
    specs = [
        _fit(d, base, False, False, "(1) Pooled OLS"),
        _fit(d, base, True, False, "(2) Country FE"),
        _fit(d, base, True, True, "(3) Country + year FE"),
        _fit(d, ["internet_10pp_lag1"] + CONTROLS, True, True, "(4) Two-way FE, internet lagged"),
        _fit(d, base + ["edu_spend_gdp_pct"], True, True, "(5) Two-way FE + edu spending"),
    ]
    rows, text = [], []
    for name, res in specs:
        ci = res.conf_int()
        for var in res.params.index:
            if var == "const":
                continue
            rows.append({
                "model": name,
                "variable": var,
                "coef": res.params[var],
                "std_err": res.std_errors[var],
                "ci_low": ci.loc[var, "lower"],
                "ci_high": ci.loc[var, "upper"],
                "p_value": res.pvalues[var],
                "n_obs": int(res.nobs),
                "n_countries": int(res.entity_info["total"]),
                "r2_within": res.rsquared_within,
                "r2_overall": res.rsquared_overall,
            })
        text.append(f"{'=' * 78}\n{name}\n{'=' * 78}\n{res.summary}\n")
    table = pd.DataFrame(rows)
    return table, "\n".join(text)


# ---------------------------------------------------------------- clustering
CLUSTER_FEATURES = ["internet_users_pct", "mobile_subs_per100", "log_gdp_pc",
                    "urban_pct", "sec_enroll_gross", "primary_completion"]


SHORT_NAMES = {
    "internet_users_pct": "internet use",
    "mobile_subs_per100": "mobile subscriptions",
    "log_gdp_pc": "income (GDP per capita)",
    "urban_pct": "urbanization",
    "sec_enroll_gross": "secondary enrollment",
    "primary_completion": "primary completion",
    "internet_growth_pp_yr": "internet growth since 2010",
}


def country_profiles(panel: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Average of each feature over each country's most recent `window` years,
    plus how fast internet use grew (pp/year) since 2010."""
    recent = panel[panel["year"] > config.END_YEAR - window]
    prof = recent.groupby(["iso3", "country"])[CLUSTER_FEATURES].mean()

    growth = {}
    for iso, g in panel.groupby("iso3"):
        s = g.set_index("year")["internet_users_pct"].dropna()
        s = s[s.index >= 2010]
        growth[iso] = np.polyfit(s.index, s.values, 1)[0] if len(s) >= 3 else np.nan
    prof["internet_growth_pp_yr"] = prof.index.get_level_values("iso3").map(growth)
    return prof


def run_clustering(panel: pd.DataFrame, k_range=range(2, 5), seed: int = 42):
    prof = country_profiles(panel)
    features = prof.copy()
    # A country missing one feature entirely (e.g. no enrollment data) gets the
    # cross-country median so it can still be placed; this is logged in the output.
    imputed_cells = features.isna()
    features = features.fillna(features.median())
    X = StandardScaler().fit_transform(features)

    scores = []
    for k in k_range:
        if k >= len(features):
            break
        km = KMeans(n_clusters=k, n_init=50, random_state=seed).fit(X)
        scores.append({"k": k, "silhouette": silhouette_score(X, km.labels_)})
    scores = pd.DataFrame(scores)
    best_k = int(scores.loc[scores["silhouette"].idxmax(), "k"])
    km = KMeans(n_clusters=best_k, n_init=50, random_state=seed).fit(X)

    out = prof.reset_index()
    out["cluster_id"] = km.labels_

    # Clusters are formed from ALL features, so a name based on internet use alone
    # would mislead. Instead each group is numbered (by average internet use,
    # highest first) and described by the features that most set it apart:
    # the standardized (z-score) group means furthest from the ASEAN average.
    z = pd.DataFrame(X, columns=features.columns)
    z["cluster_id"] = km.labels_
    z_means = z.groupby("cluster_id").mean()
    order = out.groupby("cluster_id")["internet_users_pct"].mean().sort_values(ascending=False).index
    profiles = {}
    for cid in order:
        top = z_means.loc[cid].abs().sort_values(ascending=False).index[:2]
        parts = [f"{'higher' if z_means.loc[cid, f] > 0 else 'lower'} {SHORT_NAMES[f]}" for f in top]
        profiles[cid] = " and ".join(parts)
    out["cluster_rank"] = out["cluster_id"].map({cid: i for i, cid in enumerate(order)})
    out["cluster"] = out["cluster_rank"].map(lambda r: f"Group {r + 1}")
    out["cluster_profile"] = out["cluster_id"].map(profiles)
    out["features_imputed"] = [", ".join(c for c in imputed_cells.columns if imputed_cells.iloc[i][c])
                               for i in range(len(out))]
    out = out.drop(columns="cluster_id").sort_values(["cluster_rank", "internet_users_pct"],
                                                     ascending=[True, False])
    return out, scores, best_k


def fig_clusters(clusters: pd.DataFrame) -> None:
    style.apply()
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    for rank, g in clusters.groupby("cluster_rank"):
        ax.scatter(g["log_gdp_pc"], g["internet_users_pct"], s=90, color=style.SERIES[rank],
                   edgecolor=style.SURFACE, linewidth=1.8, label=f"{g['cluster'].iloc[0]}\n{g['cluster_profile'].iloc[0]}", zorder=3)
        for _, r in g.iterrows():
            ax.annotate(r["country"], (r["log_gdp_pc"], r["internet_users_pct"]), xytext=(7, 4),
                        textcoords="offset points", fontsize=8.5, color=style.INK)
    ax.set_xlabel(config.LABELS["log_gdp_pc"] + " — recent average")
    ax.set_ylabel(config.LABELS["internet_users_pct"] + " — recent average")
    ax.set_title("Country clusters by digital and education profile")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), title="Cluster", title_fontsize=9)
    fig.text(0.01, -0.02, "k-means on 7 standardized indicators; shown on 2 of them. "
             "Labels name each country so color is never the only cue.", fontsize=8, color=style.INK_2)
    fig.savefig(config.FIGURES / "clusters.png")
    plt.close(fig)


def main():
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(config.DATA_PROCESSED / "panel_clean.csv")

    table, text = run_regressions(panel)
    table.round(4).to_csv(config.REPORTS / "regression_results.csv", index=False)
    (config.REPORTS / "regression_summary.txt").write_text(text, encoding="utf-8")
    print(f"  ran {table['model'].nunique()} regression specs")

    clusters, scores, k = run_clustering(panel)
    clusters.round(3).to_csv(config.REPORTS / "clusters.csv", index=False)
    scores.round(4).to_csv(config.REPORTS / "cluster_selection.csv", index=False)
    fig_clusters(clusters)
    print(f"  clustering chose k={k} (silhouette {scores['silhouette'].max():.3f})")
    return table, clusters, scores


if __name__ == "__main__":
    main()