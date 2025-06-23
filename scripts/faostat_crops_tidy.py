#!/usr/bin/env python3
# scripts/faostat_crops_tidy.py
from pathlib import Path
import pandas as pd
from faostat_helpers import read_any, area_to_iso, detect_year_cols

SRC   = "data/raw/faostat/FAOSTAT_Crops_and_livestock_products_data_en_6-15-2025.csv"
LOWER, UPPER = 2003, 2023
OUT   = Path("data/sample/crops_livestock_tidy.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

df = read_any(SRC)

# ---------------- country ISO mapping -------------------
df["country_iso"] = df["Area"].map(area_to_iso)
df = df.dropna(subset=["country_iso"])

# ---------------- long vs wide --------------------------
if "Year" in df.columns and "Value" in df.columns:
    # Already long format
    tidy = (df[["country_iso", "Item", "Year", "Value"]]
              .rename(columns={"Item": "variable",
                               "Year": "year",
                               "Value": "value"}))
    tidy = tidy[tidy["year"].between(LOWER, UPPER)]
else:
    # Wide format → melt
    year_cols = [c for c in detect_year_cols(df)
                 if LOWER <= int(str(c)[-4:]) <= UPPER]
    tidy = df.melt(
        id_vars=["country_iso", "Item"],
        value_vars=year_cols,
        var_name="year",
        value_name="value"
    ).rename(columns={"Item": "variable"})
    tidy["year"] = tidy["year"].str[-4:].astype(int)

# ---------------- save -------------------------
tidy.to_csv(OUT, index=False)
print(f"✅  Saved {OUT} with {len(tidy):,} rows")
