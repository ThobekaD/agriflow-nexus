
#!/usr/bin/env python3
"""
Collect all World Bank Pink-Sheet CSVs that are passed in on the command line,
keep only crude-oil rows and the years 2003-2023, and write a tidy CSV that can
be loaded straight into BigQuery.

Usage
-----
python scripts/extract_all_oil_commodities.py \
       "data/raw/worldbank/CRUDE_PETRO-1W.csv" \
       data/sample/crude_oil_prices_2003_2023.csv
"""

import sys, glob, pandas as pd, pathlib

def clean_one(csv_file: str) -> pd.DataFrame:
    """Read one Pink-Sheet CSV and return crude-oil rows (2003-2023)."""
    df = pd.read_csv(csv_file)
    # normalise column names --------------------------------------------------
    df.columns = [c.strip() for c in df.columns]
    year_col  = df.columns[0]   # usually "period"
    price_col = df.columns[1]   # the long descriptive header
    df = (df.rename(columns={year_col:  "year",
                             price_col:"usd_per_bbl"})
            .assign(year = lambda d: pd.to_numeric(d["year"], errors="coerce"))
            .loc[lambda d: d["year"].between(2003, 2023)]
            .loc[:, ["year", "usd_per_bbl"]])
    df["source"] = pathlib.Path(csv_file).name         # helpful lineage column
    return df

def main(in_pattern: str, out_csv: str) -> None:
    all_files = glob.glob(in_pattern)
    if not all_files:
        sys.exit(f"[err] no files matched: {in_pattern}")
    tidy = (pd.concat([clean_one(f) for f in all_files], ignore_index=True)
              .sort_values("year"))
    tidy.to_csv(out_csv, index=False)
    print(f"✅  Saved → {out_csv}  (rows={len(tidy)})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: extract_all_commodities.py <glob> <out_csv>")
    main(sys.argv[1], sys.argv[2])
