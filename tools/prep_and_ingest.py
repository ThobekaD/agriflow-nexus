#!/usr/bin/env python
# agriflow-nexus
import os, pathlib, re, sys, pandas as pd
from google.cloud import bigquery

# ------------ canonical lists -------------------------------------------------
SADC_ISO = {
    "AGO","BWA","COM","COD","SWZ","LSO","MDG","MWI",
    "MUS","MOZ","NAM","SYC","ZAF","TZA","ZMB","ZWE"
}
CTY_TO_ISO = {
    "Angola":"AGO","Botswana":"BWA","Comoros":"COM",
    "Democratic Republic of Congo":"COD",
    "Democratic Republic of the Congo":"COD",
    "DR Congo":"COD","Eswatini":"SWZ","Lesotho":"LSO",
    "Madagascar":"MDG","Malawi":"MWI","Mauritius":"MUS",
    "Mozambique":"MOZ","Namibia":"NAM","Seychelles":"SYC",
    "South Africa":"ZAF","Tanzania":"TZA",
    "United Republic of Tanzania":"TZA","Zambia":"ZMB","Zimbabwe":"ZWE"
}
BQ_DATASET, BQ_REGION = "ag_flow", "africa-south1"
client = bigquery.Client(location=BQ_REGION)
PROJECT = client.project

# ------------ util helpers ----------------------------------------------------
def normalise_text(col: pd.Series) -> pd.Series:
    return col.astype(str).str.strip()

def to_iso(col: pd.Series) -> pd.Series:
    col = normalise_text(col)
    mapped = col.replace(CTY_TO_ISO)
    # if it’s still not a 3-letter string, set NaN
    mapped = mapped.where(mapped.str.match(r"^[A-Z]{3}$", na=False))
    return mapped

def bq_load(df: pd.DataFrame, table: str):
    table_id = f"{PROJECT}.{BQ_DATASET}.{table}"
    job = client.load_table_from_dataframe(
        df, table_id,
        job_config=bigquery.LoadJobConfig(
            autodetect=True, write_disposition="WRITE_TRUNCATE"
        ),
    )
    job.result()
    print(f"✓ {table}: {len(df):,} rows → {table_id}")

# ------------ specific fixers -------------------------------------------------
DATA_DIR = pathlib.Path("data/sample")

def fix_fertiliser():
    df = pd.read_csv(DATA_DIR/"Fertilizers by Product.csv")
    df["country_iso"] = to_iso(df["Area"])
    keep = df[df["country_iso"].isin(SADC_ISO)]
    out = (keep
        .loc[:, ["country_iso","Year","Item","Unit","Value"]]
        .rename(columns={
            "Year":"year","Item":"fertilizer_type",
            "Unit":"unit","Value":"tonnes"})
    )
    bq_load(out, "fertilizer_usage_sadc")

def fix_producer_prices():
    df = pd.read_csv(DATA_DIR/"Annual_Commodity_SADC_2013_2024.csv")
    df["country_iso"] = to_iso(df["Area"])
    keep = df[df["country_iso"].isin(SADC_ISO)]
    out = (keep
        .loc[:, ["country_iso","Year","Item","Value"]]
        .rename(columns={
            "Year":"year","Item":"commodity",
            "Value":"price_usd_per_tonne"})
    )
    bq_load(out, "commodity_prices_sadc")

def fix_emissions():
    df = pd.read_csv(DATA_DIR/"Emissions_from_Energy_use_in_agriculture_2012_to_2022.csv")
    df["country_iso"] = to_iso(df["Area"])
    keep = df[(df["country_iso"].isin(SADC_ISO))
              & (df["Element"].str.contains("Emissions",case=False))]
    out = (keep
        .loc[:, ["country_iso","Year","Element","Unit","Value"]]
        .rename(columns={"Year":"year","Value":"value"})
    )
    bq_load(out, "emissions_energy_sadc")

def fix_fx():
    df = pd.read_csv(DATA_DIR/"Exchange_rates_2013_to_2024.csv")
    df["country_iso"] = to_iso(df["Area"])
    keep = df[df["country_iso"].isin(SADC_ISO)]
    out = (keep
        .loc[:,["country_iso","Year","Value"]]
        .rename(columns={"Year":"year","Value":"lcu_per_usd"})
    )
    bq_load(out, "fx_rates_sadc")

# optional generic helper for wide-to-long datasets (e.g. population)
def tidy_wide(fp: pathlib.Path, id_col: str, var_name: str, table: str,
              year_lo=2000, year_hi=2030):
    df = pd.read_csv(fp)
    df[id_col] = to_iso(df[id_col])
    yrs = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c))]
    yrs = [c for c in yrs if year_lo <= int(c) <= year_hi]
    tidy = df.melt(id_vars=[id_col], value_vars=yrs,
                   var_name="year", value_name="value")
    tidy["year"] = tidy["year"].astype(int)
    tidy["variable"] = var_name
    tidy = tidy[ tidy[id_col].isin(SADC_ISO) ]
    bq_load(tidy.rename(columns={id_col:"country_iso"}), table)

# ------------ main -----------------------------------------------------------
def main():
    fix_fertiliser()
    fix_producer_prices()
    fix_emissions()
    fix_fx()
    # population is already tidy, but if you ever need:
    # tidy_wide(DATA_DIR/"sadc_population_africa.csv", "country_iso",
    #           "population", "population_sadc")
    print("🎉  finished")

if __name__ == "__main__":
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        sys.exit("❌  GOOGLE_APPLICATION_CREDENTIALS not set")
    main()
