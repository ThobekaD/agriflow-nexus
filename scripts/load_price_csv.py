# ag-agents/scripts/load_price_csv.py
import os, re, pandas as pd
from pathlib import Path
from google.cloud import bigquery

CSV      = Path("data/sample/5 Commodity Prices 2020 - 2025.csv")
PROJECT  = "fieldsense-optimizer"
DATASET  = "asco_core"          # keep if you really want it in core
TABLE    = "commodity_prices_2020_2025"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "fieldsense-optimizer-8a9980b3d49a.json"
)

# ---------- helper ----------------------------------------------------
def _iso(value: str | float) -> str | None:
    """
    • If it's already like 'BWA', return it.
    • Otherwise extract '(BWA)' from 'Botswana (BWA)'.
    • Returns None on anything else (e.g. NaN/blank rows).
    """
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"[A-Z]{3}", value):        # ready to use
            return value
        m = re.search(r"\b([A-Z]{3})\b", value)
        if m:
            return m.group(1)
    return None
# ---------------------------------------------------------------------

def tidy() -> pd.DataFrame:
    df = pd.read_csv(CSV, skip_blank_lines=True)

    # ISO extraction
    df["country_iso"] = df["Country"].apply(_iso)
    df["Commodity"]   = df["Commodity"].ffill()
    df = df.drop(columns=["Country"])

    # wide → long
    df = df.melt(id_vars=["country_iso", "Commodity"],
                 var_name="year", value_name="price")

    # clean & cast
    df["price"] = (df["price"].astype(str)
                              .str.replace(r"[^\d\.]", "", regex=True)
                              .replace("", pd.NA)
                              .astype(float))
    df["year"]  = df["year"].str.extract(r"(\d{4})").astype(int)
    df = df.dropna(subset=["price"])
    df.columns = ["country_iso", "commodity", "year", "price"]
    return df

def load(df: pd.DataFrame) -> None:
    client     = bigquery.Client(project=PROJECT)
    table_ref  = f"{PROJECT}.{DATASET}.{TABLE}"
    job = client.load_table_from_dataframe(
        df,
        table_ref,
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("country_iso", "STRING"),
                bigquery.SchemaField("commodity",   "STRING"),
                bigquery.SchemaField("year",        "INT64"),
                bigquery.SchemaField("price",       "FLOAT64"),
            ],
        ),
    )
    job.result()
    print(f"✅ Loaded {len(df):,} rows into {table_ref}")

if __name__ == "__main__":
    tidy_df = tidy()
    load(tidy_df)
