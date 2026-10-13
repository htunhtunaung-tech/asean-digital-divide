# Bridging the Gap: The Digital Divide and Education Across ASEAN

An end-to-end data analysis of internet access and education outcomes in the 11 ASEAN
member states, 2000–2024 — from API download to cleaned panel, statistical models,
clustering, and an interactive dashboard.

**Author:** Htun Htun Aung (Louis) · [GitHub](https://github.com/htunhtunaung-tech) · [LinkedIn](https://www.linkedin.com/in/htun-htun-aung-a282a8346)

**Live dashboard:** _add your Streamlit Cloud link here_

---

## The question

1. How has internet use changed across ASEAN since 2000, and how fast is each country closing the gap?
2. Is internet access associated with secondary-school enrollment **after** accounting for income,
   urbanization, and fixed differences between countries?
3. Can countries be grouped by their digital and education development paths?

## Data

World Bank **World Development Indicators**, pulled live through the World Bank API (no manual downloads,
so the whole project is reproducible with one command).

| Indicator | WDI code |
|---|---|
| Internet users (% of population) | `IT.NET.USER.ZS` |
| Mobile subscriptions (per 100 people) | `IT.CEL.SETS.P2` |
| GDP per capita, PPP (constant intl $) | `NY.GDP.PCAP.PP.KD` |
| Urban population (%) | `SP.URB.TOTL.IN.ZS` |
| Secondary enrollment (% gross) | `SE.SEC.ENRR` |
| Primary completion rate (%) | `SE.PRM.CMPT.ZS` |
| Government education spending (% of GDP) | `SE.XPD.TOTL.GD.ZS` |

Countries: Brunei, Cambodia, Indonesia, Lao PDR, Malaysia, Myanmar, Philippines, Singapore,
Thailand, Viet Nam, Timor-Leste. Data license: CC BY 4.0.

## Method

| Step | Script | What it does |
|---|---|---|
| 1. Fetch | `src/fetch_data.py` | Calls the World Bank API with pagination and retries; saves a tidy long CSV. |
| 2. Clean | `src/clean.py` | Removes duplicates, sets impossible values to missing, reshapes to a country-year panel, fills short gaps (≤ 3 years) by **within-country** linear interpolation with no extrapolation, and flags every filled cell. Every decision is written to `reports/cleaning_log.md`. |
| 3. Explore | `src/eda.py` | Adoption speed and gap-to-leader per country; missing-data heatmap; Spearman correlations; scatter plots. |
| 4. Model | `src/model.py` | Five panel regressions (pooled OLS → country fixed effects → two-way fixed effects → lagged internet → plus education spending) with Driscoll–Kraay standard errors; k-means clustering with k chosen by silhouette score. |
| 5. Report | `src/report.py` | Writes `reports/findings.md` with every number pulled from the outputs. |
| Dashboard | `app/streamlit_app.py` | Map, trends, relationships, clusters, regression coefficients, findings, and data-quality tabs. |

**Why these choices**
- *Fixed effects:* the raw cross-country correlation mixes internet growth with everything else that
  makes richer countries different. Country fixed effects compare each country with itself over time;
  year fixed effects remove region-wide shocks (e.g. COVID-19).
- *Driscoll–Kraay errors:* with only 11 countries, cluster-robust errors are unreliable;
  Driscoll–Kraay handles serial and cross-country correlation.
- *No cross-country imputation:* filling Myanmar's missing years with Thailand's numbers would invent data.

## Findings

**1. Everyone got connected, but not at the same speed.**
Using each country's latest year of data, the ASEAN median internet use was **72.8%**. Malaysia led the
region; Timor-Leste was lowest at **35.0%**. Thailand grew fastest since 2010, at about
**4.9 percentage points a year**.

**2. Myanmar grew fast from almost zero, then the data stops.**
Myanmar went from **0.2% in 2010 to 45.5% in 2020** (about 4.5 points a year), yet was still
**44.1 points behind Malaysia** in 2020. The World Bank series has no Myanmar values after 2020,
so the most recent years, including the period after 2021, are a gap in the evidence itself.

**3. The internet–education link disappears when countries are compared with themselves.**
Across countries, a 10-point rise in internet use goes with **+1.01 points** of secondary enrollment
(95% CI +0.38 to +1.65). But once each country is compared with itself over time and region-wide
trends are removed, the estimate is **−0.84** (95% CI −3.46 to +1.77), and with a one-year lag
**−1.63** (95% CI −3.98 to +0.72). Neither is distinguishable from zero. The raw correlation mostly
reflects stable differences between countries (income, institutions), not internet growth itself.

**4. Countries form three loose groups, and the education gap is not the internet gap.**
K-means on 7 standardized indicators chose 3 groups (silhouette 0.28, so the groups overlap and are
best read as tendencies):
- **Group 1, higher income and urbanization:** Brunei, Malaysia, Singapore
- **Group 2, lower secondary enrollment and mobile subscriptions:** Cambodia, Lao PDR
- **Group 3, lower internet use and income:** Indonesia, Myanmar, Philippines, Thailand, Timor-Leste, Viet Nam

Cambodia and Lao PDR stand apart mainly because of school enrollment, not connectivity, which echoes
finding 3: where a country sits on education does not simply follow where it sits on internet access.

**5. What this suggests for Myanmar.**
In this data, getting more people online did not by itself track higher school enrollment. That is
consistent with connectivity being necessary but not sufficient: access likely needs to come with
digital-literacy and school-focused programs to show up in education outcomes. (This is an
interpretation of associations, not a tested causal claim.)

## Limitations

- 11 countries is a small panel; estimates are imprecise and sensitive to specification.
- Gross enrollment can exceed 100% and does not measure learning.
- Results are associations, not causal effects.
- Education indicators have many missing years for some countries (see the Data quality tab).

## Run it yourself

```bash
git clone https://github.com/htunhtunaung-tech/asean-digital-divide.git
cd asean-digital-divide
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m src.pipeline            # downloads data and runs every step (~1 minute)
streamlit run app/streamlit_app.py
pytest -q                         # tests run on synthetic data, no internet needed
```

### Deploy the dashboard (free)
1. Run the pipeline locally and **commit** `data/` and `reports/` (they are small CSVs and PNGs).
2. Push to GitHub, then on [share.streamlit.io](https://share.streamlit.io) choose the repo and set the
   main file to `app/streamlit_app.py`.

## Project structure

```
asean-digital-divide/
├── app/streamlit_app.py      interactive dashboard
├── src/
│   ├── config.py             countries, indicators, paths
│   ├── fetch_data.py         World Bank API download
│   ├── clean.py              cleaning + logged decisions
│   ├── eda.py                trend metrics + figures
│   ├── model.py              panel regressions + clustering
│   ├── report.py             auto-generated findings
│   ├── style.py              shared colorblind-safe chart style
│   └── pipeline.py           runs everything
├── tests/                    pytest suite on synthetic data
├── data/raw, data/processed  created by the pipeline
└── reports/                  CSVs, figures, findings, cleaning log
```

## Ideas to extend
- Add learning-outcome data (PISA / SEA-PLM) instead of enrollment.
- Sub-national analysis for Myanmar or Thailand.
- Add a gender gap view (female vs male internet use where available).