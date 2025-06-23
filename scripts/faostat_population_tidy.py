# ag-optimizer/scripts/faostat_population_tidy.py
#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
from faostat_helpers import read_any, area_to_iso, detect_year_cols

# NOTE: file name contains a space; adjust path accordingly
SRC = "data/raw/faostat/FAOSTAT_Annual population_data_en_6-15-2025.csv"
LOWER, UPPER = 2003, 2023
OUT  = Path("data/sample/population_tidy.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = read_any(SRC)
df["country_iso"] = df["Area"].map(area_to_iso)
df = df.dropna(subset=["country_iso"])

if "Year" in df.columns and "Value" in df.columns:
    tidy = (df[["country_iso", "Year", "Value"]]
              .rename(columns={"Year": "year", "Value": "value"}))
    tidy = tidy[tidy["year"].between(LOWER, UPPER)]
    tidy["variable"] = "population"
else:
    years = [c for c in detect_year_cols(df)
             if LOWER <= int(str(c)[-4:]) <= UPPER]
    tidy = df.melt(
        id_vars=["country_iso"],
        value_vars=years,
        var_name="year",
        value_name="value"
    )
    tidy["year"] = tidy["year"].str[-4:].astype(int)
    tidy["variable"] = "population"

tidy.to_csv(OUT, index=False)
print("✅  population rows:", len(tidy))
