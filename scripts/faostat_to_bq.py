# ag-optimizer/scripts/faostat_to_bq.py
import pandas as pd, sys, pathlib, re
AF_ISO = {   # 54 ISO-3 codes
 'DZA','AGO','BEN','BWA','BFA','BDI','CMR','CPV','CAF','TCD','COM','COG','CIV','COD','DJI',
 'EGY','GNQ','ERI','SWZ','ETH','GAB','GMB','GHA','GIN','GNB','KEN','LSO','LBR','LBY','MDG',
 'MWI','MLI','MRT','MUS','MAR','MOZ','NAM','NER','NGA','RWA','STP','SEN','SYC','SLE','SOM',
 'ZAF','SSD','SDN','TZA','TGO','TUN','UGA','ZMB','ZWE'}

SRC  = sys.argv[1]                      # path to .csv or .xlsx
LOWER = 2003
UPPER = 2023
dst  = pathlib.Path("data/sample") / (pathlib.Path(SRC).stem + "_tidy.csv")
dst.parent.mkdir(parents=True, exist_ok=True)

print("↺  Reading", SRC)
if SRC.lower().endswith((".xls", ".xlsx")):
    df = pd.read_excel(SRC)
else:
    df = pd.read_csv(SRC)

# --------- Find year columns (flexible) ----------
year_cols = [c for c in df.columns if re.match(r"\d{4}", str(c))]
meta_cols = [c for c in df.columns if c not in year_cols]

# --------- Keep only Africa & years -------------
if "Area Code (ISO3)" in meta_cols:
    iso_col = "Area Code (ISO3)"
elif "Country Code" in meta_cols:
    iso_col = "Country Code"
else:
    iso_col = meta_cols[0]   # fallback

df = df[df[iso_col].isin(AF_ISO)]
year_cols = [c for c in year_cols if LOWER <= int(c) <= UPPER]

tidy = df.melt(id_vars=meta_cols, value_vars=year_cols,
               var_name="year", value_name="value")

# Optional: rename first variable column to `variable`
first_var = [c for c in meta_cols if c not in
             (iso_col, "Country", "Area", "Item")][0]
tidy = tidy.rename(columns={iso_col: "country_iso", first_var: "variable"})

tidy.to_csv(dst, index=False)
print(f"✅  Saved {dst} rows={len(tidy):,}")
