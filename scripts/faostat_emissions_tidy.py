# ag-optimizer/scripts/faostat_emissions_tidy.py
#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
from faostat_helpers import read_any, area_to_iso, detect_year_cols

SRC = "data/raw/faostat/FAOSTAT_Emissions_from_Crops_data_en_6-15-2025.csv"
LOWER, UPPER = 2003, 2023
OUT  = Path("data/sample/crop_emissions_tidy.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = read_any(SRC)
df["country_iso"] = df["Area"].map(area_to_iso)
df = df.dropna(subset=["country_iso"])

# ---------- long vs wide --------------------------------
if "Year" in df.columns and "Value" in df.columns:
    tidy = (df[["country_iso", "Item", "Year", "Value"]]
              .rename(columns={"Item": "variable",
                               "Year": "year",
                               "Value": "value"}))
    tidy = tidy[tidy["year"].between(LOWER, UPPER)]
else:
    years = [c for c in detect_year_cols(df)
             if LOWER <= int(str(c)[-4:]) <= UPPER]
    tidy = df.melt(
        id_vars=["country_iso", "Item"],
        value_vars=years,
        var_name="year",
        value_name="value"
    ).rename(columns={"Item": "variable"})
    tidy["year"] = tidy["year"].str[-4:].astype(int)

tidy.to_csv(OUT, index=False)
print("✅  crop emissions rows:", len(tidy))
