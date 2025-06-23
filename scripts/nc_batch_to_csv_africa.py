import xarray as xr, pandas as pd, glob, sys, os, json, urllib.request
from pathlib import Path
from shapely.geometry import Point, shape
from tqdm import tqdm

# --- CLI args ---------------------------------------------------------------
PATTERN   = sys.argv[1]   # "data/raw/cru/CRU_*_temperature_*.nc"
VAR       = sys.argv[2]   # "tmx"  or  "pre"  or  "sm"
OUT_CSV   = Path(f"data/sample/{VAR}_africa.csv")
AFRICA_BOX = dict(lat=slice(-35, 37), lon=slice(-20, 55))

# --- cheap ISO-finder (no geopandas) ----------------------------------------
NE = Path("data/raw/ne_africa_110m.geojson")
if not NE.exists():
    url = ("https://raw.githubusercontent.com/nvkelso/"
           "natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson")
    urllib.request.urlretrieve(url, NE)

with open(NE) as f:
    AFRICA_POLYS = [(feat["properties"]["ADM0_A3"],
                     shape(feat["geometry"]))
                    for feat in json.load(f)["features"]
                    if feat["properties"]["CONTINENT"] == "Africa"]

def latlon_to_iso(lat, lon):
    pt = Point(lon, lat)
    for iso, poly in AFRICA_POLYS:
        if poly.contains(pt):
            return iso
    return None

# --- prep output file --------------------------------------------------------
WRITE_HEADER = not OUT_CSV.exists()
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# --- process each file -------------------------------------------------------
files = sorted(glob.glob(PATTERN))
print(f"Processing {len(files)} NetCDF files → {OUT_CSV}")

for f in tqdm(files, unit="file"):
    try:
        ds = xr.open_dataset(f, engine="h5netcdf")   # ↓ memory, safer than netcdf4
        if ds.lon.max() > 180:
            ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))

        da = ds[VAR].sel(**AFRICA_BOX)

        # daily → monthly; dekadal → monthly; monthly stays monthly
        if "time" in da.dims:
            da = da.resample(time="1M").mean(skipna=True)

        df = (da.to_dataframe(name="value")
                 .reset_index()
                 .dropna(subset=["value"]))

        df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-01")
        df.drop(columns=["time"], inplace=True)

        # ISO tagging
        df["country_iso"] = [latlon_to_iso(lat, lon) for lat, lon in zip(df.lat, df.lon)]
        df.dropna(subset=["country_iso"], inplace=True)

        # keep only useful columns
        df = df[["country_iso", "date", "lat", "lon", "value"]]

        df.to_csv(OUT_CSV, mode="a",
                  header=WRITE_HEADER, index=False)
        WRITE_HEADER = False
        ds.close()

    except Exception as e:
        print("⚠️  skipping", f, "→", e)

print("✅  Finished. Rows in file:",
      sum(1 for _ in open(OUT_CSV)))
