#!/usr/bin/env python3
import pandas as pd
import pycountry
from pathlib import Path

# — INPUT / OUTPUT paths —————————————————————————————
SRC = Path("data/raw/faostat/FAOSTAT_Country_Investment_Statistics_Profile_data_en_6-15-2025.csv")
OUT = Path("data/sample/country_investment_tidy.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

# — read the FAO CSV ————————————————————————————————
df = pd.read_csv(SRC)

# — map full country names → ISO3 ——————————————————————
def area_to_iso(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

df["country_iso"] = df["Area"].map(area_to_iso)

# — drop rows with no ISO, then filter years ————————————
df = df.dropna(subset=["country_iso"])
df = df[df["Year"].between(2003, 2023)]

# — pick columns and tidy ——————————————————————————
# We'll treat each distinct Element (e.g. "Gross capital formation")
# as a separate variable.
tidy = df[["country_iso", "Year", "Element", "Value"]].rename(
    columns={"Year": "year", "Element": "variable", "Value": "value"}
)

# — write out a CSV BigQuery can ingest ———————————————————
tidy.to_csv(OUT, index=False)
print(f"✅  Saved {OUT} with {len(tidy):,} rows")
