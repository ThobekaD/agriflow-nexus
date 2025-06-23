#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, sys
from faostat_helpers import read_any, area_to_iso, detect_year_cols

SRC   = "data/raw/faostat/FAOSTAT_Country_Investment_Statistics_Profile_data_en_6-15-2025.csv"
LOWER, UPPER = 2003, 2023
OUT   = Path("data/sample/country_investment_tidy.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = read_any(SRC)
df["country_iso"] = df["Area"].map(area_to_iso)
df = df.dropna(subset=["country_iso"])

years = [c for c in detect_year_cols(df) if LOWER <= int(str(c)[-4:]) <= UPPER]
tidy = df.melt(
    id_vars=["country_iso", "Element"],
    value_vars=years,
    var_name="year",
    value_name="value"
).rename(columns={"Element": "variable"})

tidy["year"] = tidy["year"].str[-4:].astype(int)
tidy.to_csv(OUT, index=False)
print("✅  country_investment rows:", len(tidy))
