"""
Upload local CSV/XLSX/GPKG files to BigQuery dataset ag_flow.
Run:  python tools/bq_ingest.py
"""

import glob, pathlib, pandas as pd
from google.cloud import bigquery
import geopandas as gpd

DATASET  = "ag_flow"
LOCATION = "africa-south1"
client   = bigquery.Client(location=LOCATION)

# ---------- single helper ----------------------------------------------------
def load_df(df: pd.DataFrame, table: str):
    """Load a Pandas (or GeoPandas) DataFrame to BigQuery and overwrite."""
    if isinstance(df, gpd.GeoDataFrame):
        # drop geometry column – OR convert to WKT if you actually need it
        df = df.drop(columns=[c for c in df.columns if str(df[c].dtype) == "geometry"])
    job = client.load_table_from_dataframe(
        df,
        f"{DATASET}.{table}",
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True,
        ),
    )
    job.result()
    print(f"✓ {table:<25} ({len(df):,} rows)")

# ---------- wrappers ---------------------------------------------------------
def load_csv(path: str | pathlib.Path, table: str):
    load_df(pd.read_csv(path), table)

def load_xlsx(path: str | pathlib.Path, table: str):
    load_df(pd.read_excel(path, sheet_name=0), table)

def load_gpkg(path: str | pathlib.Path, table: str):
    load_df(gpd.read_file(path), table)

# ---------- file mapping -----------------------------------------------------
mapping = {
    "data/sample/sm_sadc_*.csv" : "soil_moist_sadc",
    "data/sample/preci_*csv"    : "precip_sadc",
    "data/sample/temp_*csv"     : "temp_sadc",
    "data/sample/*fuel_price*.csv" : "fuel_price_sadc",
    "data/sample/*acled*.csv"   : "acled_events_sadc",
    "data/sample/*population*.csv" : "population_sadc",
    "data/sample/*Exchange*.csv": "fx_rates_sadc",
    "data/sample/*Commodity*.csv": "commodity_prices_sadc",
    "data/sample/*Fertilizer*.csv": "fertilizer_usage_sadc",
    "data/sample/*Emissions*.csv": "emissions_energy_sadc",
    "data/sample/*.gpkg"                 : "road_network_sadc",
}

# ---------- drive ------------------------------------------------------------
if __name__ == "__main__":
    for pattern, table in mapping.items():
        for f in glob.glob(pattern):
            ext = pathlib.Path(f).suffix.lower()
            # choose table name
            tbl = table or pathlib.Path(f).stem  # auto from filename if None
            # route to loader
            if ext == ".csv":
                load_csv(f, tbl)
            elif ext in (".xls", ".xlsx"):
                load_xlsx(f, tbl)
            elif ext == ".gpkg":
                load_gpkg(f, tbl)
            else:
                print(f"⚠️  skipped {f}")
