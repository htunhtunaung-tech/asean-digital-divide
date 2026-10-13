"""Step 3 — Exploratory analysis: trend metrics and figures.

Output:
  reports/trend_summary.csv            per-country internet growth and gap metrics
  reports/figures/internet_trends.png  every country in gray, focus country highlighted
  reports/figures/missing_heatmap.png  % missing per country x indicator (before filling)
  reports/figures/correlation_heatmap.png
  reports/figures/internet_vs_enrollment.png

Usage:
    python -m src.eda
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from . import config, style

INDICATORS = list(config.INDICATORS.values())


def load_panel() -> pd.DataFrame:
    return pd.read_csv(config.DATA_PROCESSED / "panel_clean.csv")


def latest_value(g: pd.DataFrame, col: str) -> tuple[float, float]:
    """Most recent non-missing (year, value) for one country."""
    s = g.dropna(subset=[col])
    if s.empty:
        return (np.nan, np.nan)
    row = s.iloc[-1]
    return (int(row["year"]), float(row[col]))


def value_at(g: pd.DataFrame, col: str, year: int) -> float:
    s = g.loc[g["year"] == year, col]
    return float(s.iloc[0]) if len(s) and pd.notna(s.iloc[0]) else np.nan


def trend_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-country internet adoption metrics."""
    col = "internet_users_pct"
    leader_iso = (panel.dropna(subset=[col]).sort_values("year")
                  .groupby("iso3")[col].last().idxmax())
    rows = []
    for iso, g in panel.sort_values("year").groupby("iso3"):
        yr, latest = latest_value(g, col)
        v2010 = value_at(g, col, 2010)
        crossed = g.loc[g[col] >= 50, "year"]
        leader_latest = value_at(panel[panel["iso3"] == leader_iso], col, yr) if pd.notna(yr) else np.nan
        rows.append({
            "iso3": iso,
            "country": config.COUNTRIES[iso],
            "internet_2010": v2010,
            "latest_year": yr,
            "internet_latest": latest,
            "avg_gain_pp_per_year_since_2010": (latest - v2010) / (yr - 2010)
            if pd.notna(v2010) and pd.notna(yr) and yr > 2010 else np.nan,
            "first_year_above_50pct": int(crossed.iloc[0]) if len(crossed) else np.nan,
            "gap_to_leader_pp": leader_latest - latest if pd.notna(latest) else np.nan,
        })
    out = pd.DataFrame(rows).sort_values("internet_latest", ascending=False)
    out.attrs["leader"] = config.COUNTRIES[leader_iso]
    return out.round(2)


def _end_label(ax, x, y, text, color, dy=0.0):
    ax.annotate(text, (x, y), xytext=(6, dy), textcoords="offset points",
                va="center", fontsize=9, color=style.INK, fontweight="bold")
    ax.plot([x], [y], "o", color=color, markersize=6, markeredgecolor=style.SURFACE,
            markeredgewidth=1.5, zorder=5)


def fig_internet_trends(panel: pd.DataFrame) -> None:
    col = "internet_users_pct"
    focus = config.FOCUS_COUNTRY
    fig, ax = plt.subplots(figsize=(9, 5.6))
    labels = []  # (y, text, text color, bold, leader-line color) — placed together at the end so they never overlap

    for iso, g in panel.groupby("iso3"):
        g = g.dropna(subset=[col])
        if iso == focus or g.empty:
            continue
        ax.plot(g["year"], g[col], color=style.CONTEXT, linewidth=1.2, zorder=1)
        labels.append((g[col].iloc[-1], config.COUNTRIES[iso], style.INK_2, False, style.GRID))

    median = panel.groupby("year")[col].median().dropna()
    ax.plot(median.index, median.values, color=style.SERIES[1], linewidth=2,
            linestyle=(0, (4, 2)), zorder=3)
    ax.plot([median.index[-1]], [median.values[-1]], "o", color=style.SERIES[1], markersize=6,
            markeredgecolor=style.SURFACE, markeredgewidth=1.5, zorder=5)
    labels.append((median.values[-1], "ASEAN median", style.INK, True, style.SERIES[1]))

    g = panel[panel["iso3"] == focus].dropna(subset=[col])
    if not g.empty:
        ax.plot(g["year"], g[col], color=style.SERIES[0], linewidth=2.6, zorder=4)
        ax.plot([g["year"].iloc[-1]], [g[col].iloc[-1]], "o", color=style.SERIES[0], markersize=6,
                markeredgecolor=style.SURFACE, markeredgewidth=1.5, zorder=5)
        labels.append((g[col].iloc[-1], config.COUNTRIES[focus], style.INK, True, style.SERIES[0]))

    # Simple label repel: sort by height, then push labels apart to a minimum gap.
    min_gap = 4.2
    labels.sort(key=lambda t: t[0])
    ys = [t[0] for t in labels]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + min_gap)
    overflow = ys[-1] - 103 if ys else 0
    if overflow > 0:
        ys = [y - overflow for y in ys]
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = min(ys[i], ys[i + 1] - min_gap)
    x_end = config.END_YEAR + 0.6
    for (y0, text, color, bold, line_color), y in zip(labels, ys):
        if abs(y - y0) > 0.8:  # thin leader line when a label had to move
            ax.plot([config.END_YEAR + 0.1, x_end - 0.15], [y0, y], color=line_color,
                    linewidth=1.2 if bold else 0.8, zorder=0, clip_on=False)
        ax.annotate(text, (x_end, y), va="center", fontsize=8.5 if bold else 7.5, color=color,
                    fontweight="bold" if bold else "normal", annotation_clip=False)

    ax.set_title(f"Internet use across ASEAN, {config.START_YEAR}–{config.END_YEAR}")
    ax.set_ylabel(config.LABELS[col])
    ax.set_ylim(0, 105)
    ax.set_xlim(config.START_YEAR, config.END_YEAR + 3.5)
    ax.grid(axis="x", visible=False)
    fig.text(0.01, -0.02, "Source: World Bank, World Development Indicators. Gray lines: other ASEAN countries.",
             fontsize=8, color=style.INK_2)
    fig.savefig(config.FIGURES / "internet_trends.png")
    plt.close(fig)


def _heatmap(ax, data: pd.DataFrame, cmap, vmin, vmax, fmt, text_threshold):
    im = ax.imshow(data.values, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(data.shape[1]), data.columns, rotation=35, ha="right")
    ax.set_yticks(range(data.shape[0]), data.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data.values[i, j]
            if np.isnan(v):
                continue
            dark_cell = text_threshold(v)
            ax.text(j, i, format(v, fmt), ha="center", va="center", fontsize=8,
                    color=style.SURFACE if dark_cell else style.INK)
    return im


def fig_missing_heatmap() -> None:
    missing = pd.read_csv(config.REPORTS / "missing_report.csv", index_col=0)
    missing.columns = [config.LABELS.get(c, c).split(" (")[0] for c in missing.columns]
    cmap = LinearSegmentedColormap.from_list("seq", style.SEQUENTIAL)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    im = _heatmap(ax, missing, cmap, 0, 100, ".0f", lambda v: v > 55)
    ax.set_title("Share of years missing before cleaning (%)")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=style.INK_2, labelsize=8)
    fig.savefig(config.FIGURES / "missing_heatmap.png")
    plt.close(fig)


def fig_correlation(panel: pd.DataFrame) -> pd.DataFrame:
    cols = ["internet_users_pct", "mobile_subs_per100", "log_gdp_pc", "urban_pct",
            "sec_enroll_gross", "primary_completion", "edu_spend_gdp_pct"]
    corr = panel[cols].corr(method="spearman")
    short = [config.LABELS[c].split(" (")[0] for c in cols]
    corr.index = corr.columns = short
    cmap = LinearSegmentedColormap.from_list("div", style.DIVERGING)
    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    im = _heatmap(ax, corr, cmap, -1, 1, ".2f", lambda v: abs(v) > 0.6)
    ax.set_title("Spearman correlation, all country-years")
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=style.INK_2, labelsize=8)
    fig.savefig(config.FIGURES / "correlation_heatmap.png")
    plt.close(fig)
    return corr


def fig_internet_vs_enrollment(panel: pd.DataFrame) -> None:
    x, y = "internet_users_pct", "sec_enroll_gross"
    d = panel.dropna(subset=[x, y])
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    ax.scatter(d[x], d[y], s=14, color=style.CONTEXT, edgecolor="none", zorder=1,
               label="All country-years")
    latest = d.sort_values("year").groupby("iso3").tail(1)
    ax.scatter(latest[x], latest[y], s=64, color=style.SERIES[0], edgecolor=style.SURFACE,
               linewidth=1.5, zorder=3, label="Latest year per country")
    for _, r in latest.iterrows():
        ax.annotate(f"{r['country']} ({int(r['year'])})", (r[x], r[y]), xytext=(6, 4),
                    textcoords="offset points", fontsize=8, color=style.INK)
    ax.set_xlabel(config.LABELS[x])
    ax.set_ylabel(config.LABELS[y])
    ax.set_title("Internet use and secondary enrollment")
    ax.legend(loc="lower right")
    fig.savefig(config.FIGURES / "internet_vs_enrollment.png")
    plt.close(fig)


def main() -> pd.DataFrame:
    style.apply()
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    trends = trend_summary(panel)
    trends.to_csv(config.REPORTS / "trend_summary.csv", index=False)
    pd.Series({"leader": trends.attrs["leader"]}).to_csv(config.REPORTS / "trend_meta.csv")
    fig_internet_trends(panel)
    fig_missing_heatmap()
    fig_correlation(panel)
    fig_internet_vs_enrollment(panel)
    print(f"  saved trend_summary.csv and 4 figures -> {config.FIGURES.relative_to(config.ROOT)}")
    return trends


if __name__ == "__main__":
    main()
