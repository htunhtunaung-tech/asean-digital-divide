"""Project-wide settings: countries, indicators, paths and years.

Everything the pipeline needs to know lives here, so changing the scope of the
study (e.g. adding a country or an indicator) is a one-file edit.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

START_YEAR = 2000
END_YEAR = 2024

# ASEAN member states + Timor-Leste (admitted as the 11th member in 2025).
COUNTRIES = {
    "BRN": "Brunei",
    "KHM": "Cambodia",
    "IDN": "Indonesia",
    "LAO": "Lao PDR",
    "MYS": "Malaysia",
    "MMR": "Myanmar",
    "PHL": "Philippines",
    "SGP": "Singapore",
    "THA": "Thailand",
    "VNM": "Viet Nam",
    "TLS": "Timor-Leste",
}

# World Bank WDI indicator code -> short column name used everywhere else.
INDICATORS = {
    "IT.NET.USER.ZS": "internet_users_pct",      # Individuals using the Internet (% of population)
    "IT.CEL.SETS.P2": "mobile_subs_per100",      # Mobile cellular subscriptions (per 100 people)
    "NY.GDP.PCAP.PP.KD": "gdp_pc_ppp",           # GDP per capita, PPP (constant international $)
    "SP.URB.TOTL.IN.ZS": "urban_pct",            # Urban population (% of total)
    "SE.SEC.ENRR": "sec_enroll_gross",           # School enrollment, secondary (% gross)
    "SE.PRM.CMPT.ZS": "primary_completion",      # Primary completion rate (% of relevant age group)
    "SE.XPD.TOTL.GD.ZS": "edu_spend_gdp_pct",    # Government expenditure on education (% of GDP)
}

LABELS = {
    "internet_users_pct": "Internet users (% of population)",
    "mobile_subs_per100": "Mobile subscriptions (per 100 people)",
    "gdp_pc_ppp": "GDP per capita, PPP (constant intl $)",
    "log_gdp_pc": "log GDP per capita (PPP)",
    "urban_pct": "Urban population (%)",
    "sec_enroll_gross": "Secondary enrollment (% gross)",
    "primary_completion": "Primary completion rate (%)",
    "edu_spend_gdp_pct": "Education spending (% of GDP)",
}

# Interpolation never fills gaps longer than this many consecutive years,
# and never extrapolates past a country's first/last observed value.
MAX_INTERP_GAP = 3

FOCUS_COUNTRY = "MMR"
