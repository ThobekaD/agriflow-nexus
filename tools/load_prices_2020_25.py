"""
Load the user-supplied CSV (2020-2025 spot prices) into the canonical
table `asco_core.commodity_prices_all`, then *optionally* retrain the
ARIMA+ model for each commodity.
Run:  python tools/load_prices_2020_25.py path/to/prices.csv
"""
import sys, re, pandas as pd
from google.cloud import bigquery

CSV = sys.argv[1]
PROJECT = "fieldsense-optimizer"          # <-- change if different
DATASET = "asco_core"
TABLE   = f"{PROJECT}.{DATASET}.commodity_prices_all"

def iso_from_country(cell: str) -> str:
    # "Botswana (BWA)" ➜ "BWA"
    m = re.search(r"\((\w{3})\)", cell or "")
    return m.group(1) if m else "UNK"

def tidy(df: pd.DataFrame) -> pd.DataFrame:
    df["Country"].ffill(inplace=True)      # propagate country name down
    df = df.melt(id_vars=["Country","Commodity"],
                 var_name="year",
                 value_name="price")
    df["year"]  = df["year"].str.extract(r"(\d{4})").astype(int)
    df["price"] = (df["price"]
                     .str.replace(r"[^\d\.]", "", regex=True)
                     .astype(float))
    df["country_iso"] = df["Country"].apply(iso_from_country)
    return df[["year","commodity","price","country_iso"]]

def main():
    raw  = pd.read_csv(CSV)
    tidy_df = tidy(raw)
    print("Rows to append:", len(tidy_df))

    bq = bigquery.Client(project=PROJECT)
    job = bq.load_table_from_dataframe(
        tidy_df,
        TABLE,
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=["ALLOW_FIELD_ADDITION"],
        ),
    )
    job.result()
    print("✓ data appended to", TABLE)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python ... prices.csv")
    main()
