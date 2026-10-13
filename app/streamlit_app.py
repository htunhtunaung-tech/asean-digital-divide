"""Interactive dashboard for the ASEAN digital divide project.

Run the pipeline first (python -m src.pipeline), then:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config, style  # noqa: E402

# DATA_DIR lets you point the app at another output folder (used in testing).
BASE = Path(os.environ.get("DATA_DIR", ROOT))
PROCESSED = BASE / "data" / "processed"
REPORTS = BASE / "reports"

st.set_page_config(page_title="ASEAN Digital Divide", page_icon="🌏", layout="wide")

SEQ_SCALE = [[i / (len(style.SEQUENTIAL) - 1), c] for i, c in enumerate(style.SEQUENTIAL)]
LAYOUT = dict(
    font=dict(family="Inter, system-ui, sans-serif", size=13),
    margin=dict(l=10, r=10, t=95, b=10),
    title=dict(y=0.97, yanchor="top"),
    hoverlabel=dict(font_size=12),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="rgba(128,128,128,0.18)"),
)
INDICATOR_COLS = list(config.INDICATORS.values())


@st.cache_data
def load():
    panel = pd.read_csv(PROCESSED / "panel_clean.csv")
    out = {"panel": panel}
    for name in ["trend_summary", "clusters", "regression_results", "missing_report", "cluster_selection"]:
        f = REPORTS / f"{name}.csv"
        out[name] = pd.read_csv(f) if f.exists() else None
    for name in ["findings.md", "cleaning_log.md"]:
        f = REPORTS / name
        out[name] = f.read_text(encoding="utf-8") if f.exists() else ""
    return out


if not (PROCESSED / "panel_clean.csv").exists():
    st.error("No processed data found. Run `python -m src.pipeline` first, then reload this page.")
    st.stop()

D = load()
panel = D["panel"]
countries = sorted(panel["country"].unique())
focus_name = config.COUNTRIES[config.FOCUS_COUNTRY]

# ------------------------------------------------------------------ header
st.title("Bridging the Gap: The Digital Divide and Education Across ASEAN")
st.caption(f"World Bank World Development Indicators, {config.START_YEAR}–{config.END_YEAR} · "
           f"{len(countries)} countries · cleaned panel of {len(panel):,} country-years")

# ------------------------------------------------------------------ filters (one row)
f1, f2, f3 = st.columns([2, 3, 2])
with f1:
    indicator = st.selectbox("Indicator", INDICATOR_COLS, index=0,
                             format_func=lambda c: config.LABELS[c])
with f2:
    highlight = st.multiselect("Highlight countries (up to 3)", countries,
                               default=[focus_name] if focus_name in countries else [],
                               max_selections=3)
with f3:
    years = panel.dropna(subset=[indicator])["year"]
    year_max = int(years.max()) if len(years) else config.END_YEAR
    year = st.slider("Year (map and scatter)", int(config.START_YEAR), year_max, year_max)

tab_overview, tab_trends, tab_rel, tab_clusters, tab_model, tab_findings, tab_quality = st.tabs(
    ["Overview", "Trends", "Relationships", "Clusters", "Regression", "Findings", "Data quality"])

# ------------------------------------------------------------------ overview
with tab_overview:
    t = D["trend_summary"]
    if t is not None and highlight:
        cols = st.columns(len(highlight))
        median = t["internet_latest"].median()
        for c, name in zip(cols, highlight):
            r = t[t["country"] == name].iloc[0]
            c.metric(f"{name} · internet use ({int(r['latest_year'])})",
                     f"{r['internet_latest']:.1f}%",
                     f"{r['internet_latest'] - median:+.1f} pts vs ASEAN median")

    snap = panel[panel["year"] == year]
    fig = px.choropleth(snap, locations="iso3", color=indicator, hover_name="country",
                        color_continuous_scale=SEQ_SCALE,
                        labels={indicator: config.LABELS[indicator]})
    fig.update_geos(fitbounds="locations", visible=False, 
                    showcountries=True, bgcolor="rgba(0,0,0,0)",
                    countrycolor="rgba(128,128,128,0.4)", showland=True,
                    landcolor="rgba(128,128,128,0.08)")
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.update_layout(**{**LAYOUT, "height": 520,
                         "title": dict(text=f"{config.LABELS[indicator]}, {year}", y=0.97, yanchor="top"),
                         "coloraxis_colorbar": dict(title=None, thickness=12)})
    st.plotly_chart(fig, width="stretch")
    missing = snap.loc[snap[indicator].isna(), "country"].tolist()
    if missing:
        st.caption(f"No data for {year}: {', '.join(missing)} (shown blank, not zero).")

# ------------------------------------------------------------------ trends
with tab_trends:
    fig = go.Figure()
    for name, g in panel.groupby("country"):
        g = g.dropna(subset=[indicator])
        if name in highlight or g.empty:
            continue
        fig.add_trace(go.Scatter(x=g["year"], y=g[indicator], name=name, mode="lines",
                                 line=dict(color=style.CONTEXT, width=1.2), showlegend=False,
                                 hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>"))
    med = panel.groupby("year")[indicator].median().dropna()
    fig.add_trace(go.Scatter(x=med.index, y=med.values, name="ASEAN median", mode="lines",
                             line=dict(color=style.INK_2, width=2, dash="dash"),
                             hovertemplate="<b>ASEAN median</b><br>%{x}: %{y:.1f}<extra></extra>"))
    # Colors follow the selection slot, so a series keeps its color while others are added.
    for i, name in enumerate(highlight):
        g = panel[panel["country"] == name].dropna(subset=[indicator])
        imputed = g[f"{indicator}_imputed"].astype(bool) if f"{indicator}_imputed" in g else False
        fig.add_trace(go.Scatter(
            x=g["year"], y=g[indicator], name=name, mode="lines+markers",
            line=dict(color=style.SERIES[i], width=2.6),
            marker=dict(size=7, symbol=["circle-open" if v else "circle" for v in imputed]
                        if hasattr(imputed, "__iter__") else "circle"),
            hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>"))
        if len(g):
            fig.add_annotation(x=g["year"].iloc[-1], y=g[indicator].iloc[-1], text=f"<b>{name}</b>",
                               xanchor="left", xshift=8, showarrow=False)
    fig.update_layout(**{**LAYOUT, "height": 520, "hovermode": "closest",
                         "title": dict(text=config.LABELS[indicator], y=0.97, yanchor="top")})
    st.plotly_chart(fig, width="stretch")
    st.caption("Gray: other ASEAN countries (hover to identify). Open markers are years filled by "
               "interpolation; solid markers are reported values.")

# ------------------------------------------------------------------ relationships
with tab_rel:
    c1, c2 = st.columns(2)
    x = c1.selectbox("X axis", INDICATOR_COLS + ["log_gdp_pc"], index=0,
                     format_func=lambda c: config.LABELS[c], key="x")
    y = c2.selectbox("Y axis", INDICATOR_COLS + ["log_gdp_pc"], index=INDICATOR_COLS.index("sec_enroll_gross"),
                     format_func=lambda c: config.LABELS[c], key="y")
    allyrs = panel.dropna(subset=[x, y])
    snap = allyrs[allyrs["year"] == year]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=allyrs[x], y=allyrs[y], mode="markers", name="All country-years",
                             marker=dict(color=style.CONTEXT, size=6),
                             text=allyrs["country"] + " " + allyrs["year"].astype(str),
                             hovertemplate="%{text}<br>x=%{x:.1f}, y=%{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=snap[x], y=snap[y], mode="markers+text", name=str(year),
                             text=snap["country"], textposition="top center",
                             marker=dict(color=style.SERIES[0], size=11, line=dict(color="white", width=1.5)),
                             hovertemplate="<b>%{text}</b><br>x=%{x:.1f}, y=%{y:.1f}<extra></extra>"))
    fig.update_layout(**{**LAYOUT, "height": 540,
                         "xaxis": dict(title=config.LABELS[x], showgrid=False),
                         "yaxis": dict(title=config.LABELS[y], gridcolor="rgba(128,128,128,0.18)")})
    st.plotly_chart(fig, width="stretch")
    if len(allyrs) > 3:
        rho = allyrs[[x, y]].corr(method="spearman").iloc[0, 1]
        st.caption(f"Spearman correlation across all {len(allyrs)} country-years: **{rho:.2f}**. "
                   "Correlation across countries mixes many factors — see the Regression tab.")

# ------------------------------------------------------------------ clusters
with tab_clusters:
    cl = D["clusters"]
    if cl is None:
        st.info("Run the pipeline to generate clusters.")
    else:
        sel = D["cluster_selection"]
        k = int(sel.loc[sel["silhouette"].idxmax(), "k"])
        st.markdown(f"K-means on standardized recent-average indicators chose **k = {k}** "
                    f"(silhouette {sel['silhouette'].max():.2f}).")
        fig = go.Figure()
        for rank, g in cl.groupby("cluster_rank"):
            fig.add_trace(go.Scatter(
                x=g["log_gdp_pc"], y=g["internet_users_pct"], mode="markers+text",
                name=g["cluster"].iloc[0], text=g["country"], textposition="top center",
                marker=dict(size=14, color=style.SERIES[int(rank)], line=dict(color="white", width=1.5)),
                hovertemplate="<b>%{text}</b><br>log GDP pc: %{x:.2f}<br>Internet: %{y:.1f}%<extra></extra>"))
        fig.update_layout(**{**LAYOUT, "height": 520,
                             "xaxis": dict(title=config.LABELS["log_gdp_pc"], showgrid=False),
                             "yaxis": dict(title=config.LABELS["internet_users_pct"],
                                           gridcolor="rgba(128,128,128,0.18)")})
        st.plotly_chart(fig, width="stretch")
        show = cl.drop(columns=["cluster_rank"]).rename(columns=lambda c: config.LABELS.get(c, c))
        st.dataframe(show, width="stretch", hide_index=True)

# ------------------------------------------------------------------ regression
with tab_model:
    reg = D["regression_results"]
    if reg is None:
        st.info("Run the pipeline to generate regression results.")
    else:
        st.markdown("**Outcome:** secondary enrollment (% gross). **Key variable:** internet use, "
                    "per 10 percentage points. Controls: log GDP per capita (PPP), urban share. "
                    "Driscoll–Kraay standard errors.")
        key = reg[reg["variable"].str.startswith("internet_10pp")].iloc[::-1]
        fig = go.Figure()
        fig.add_vline(x=0, line_color=style.INK_2, line_width=1)
        fig.add_trace(go.Scatter(
            x=key["coef"], y=key["model"], mode="markers",
            marker=dict(size=11, color=style.SERIES[0]),
            error_x=dict(type="data", symmetric=False, array=key["ci_high"] - key["coef"],
                         arrayminus=key["coef"] - key["ci_low"], color=style.SERIES[0], thickness=2),
            customdata=key[["ci_low", "ci_high", "n_obs"]],
            hovertemplate="<b>%{y}</b><br>coef %{x:.2f}<br>95% CI %{customdata[0]:.2f} to "
                          "%{customdata[1]:.2f}<br>n = %{customdata[2]}<extra></extra>",
            showlegend=False))
        fig.update_layout(**{**LAYOUT, "height": 380,
                             "title": dict(text="Internet use coefficient across specifications (95% CI)", y=0.95, yanchor="top"),
                             "xaxis": dict(title="Change in enrollment (pts) per +10 pts internet use",
                                           gridcolor="rgba(128,128,128,0.18)"),
                             "yaxis": dict(showgrid=False)})
        st.plotly_chart(fig, width="stretch")
        st.dataframe(reg.round(3), width="stretch", hide_index=True)
        st.caption("These are associations. Fixed effects remove stable country differences and "
                   "region-wide shocks, but not time-varying confounders.")

# ------------------------------------------------------------------ findings / quality
with tab_findings:
    st.markdown(D["findings.md"] or "_Run the pipeline to generate findings._")

with tab_quality:
    mr = D["missing_report"]
    if mr is not None:
        mr = mr.set_index(mr.columns[0])
        mr.columns = [config.LABELS.get(c, c).split(" (")[0] for c in mr.columns]
        fig = px.imshow(mr, text_auto=".0f", color_continuous_scale=SEQ_SCALE, zmin=0, zmax=100,
                        aspect="auto", labels=dict(color="% missing"))
        fig.update_layout(**{**LAYOUT, "height": 480, "title": dict(text="Share of years missing before cleaning (%)", y=0.97, yanchor="top"),
                             "xaxis": dict(showgrid=False), "yaxis": dict(showgrid=False, title=None)})
        st.plotly_chart(fig, width="stretch")
    st.markdown(D["cleaning_log.md"])

st.divider()
st.caption("Built by Htun Htun Aung · Source code: src/ · Data: World Bank WDI (CC BY 4.0)")
