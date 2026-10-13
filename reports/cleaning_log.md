# Cleaning log

- **Load:** 1,925 raw rows, 11 countries, 7 indicators
- **Scope:** dropped 0 rows outside study countries/years/indicators
- **Duplicates:** dropped 0 duplicate country-year-indicator rows
- **Validity:** set 0 negative and 0 >100% values to missing
- **Reshape:** panel of 275 country-years x 7 indicators
- **Missing (before):** 244 of 1925 cells (12.7%) missing
- **Interpolation:** filled 37 cells (gaps <= 3 years, within-country, no extrapolation); 207 cells left missing
- **Derived:** added log_gdp_pc = ln(GDP per capita, PPP)
- **Saved:** data\processed\panel_clean.csv
