#!/usr/bin/env python3
"""
Convert one or many NetCDF files to a tidy Africa-wide CSV
---------------------------------------------------------

Usage:
    python nc_to_csv_africa.py "<wildcard/path/*.nc>" <variable_name>

Example:
    python nc_to_csv_africa.py "data/raw/cru/CRU_maximum_temperature*.nc" tasmax
"""

import sys, glob, json, urllib.request
from pathlib import Path

import xarray as xr
import pandas as pd
from shapely.geometry import Point, shape
from tqdm import tqdm

# ---------------------------------------------------------------------------#
# CLI args
# ---------------------------------------------------------------------------#
try:
    PATTERN = sys.argv[1]          # "*.nc"
    VAR     = sys.argv[2]          # "tasmax", "pr", "sm", …
except IndexError:
    sys.exit("❌  Syntax:  nc_to_csv_africa.py '<glob_pattern>' <var_name>")

OUT_DIR = Path("data/sample")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / f"{VAR}_africa.csv"

# Africa bounding box
LAT_MIN, LAT_MAX = -35, 37
LON_MIN, LON_MAX = -20, 55

# ---------------------------------------------------------------------------#
# Lightweight ISO-finder for Africa (Natural-Earth GeoJSON)
# ---------------------------------------------------------------------------#
NE_FILE = Path("data/raw/ne_africa_110m.geojson")
if not NE_FILE.exists():
    NE_FILE.parent.mkdir(parents=True, exist_ok=True)
    url = ("https://raw.githubusercontent.com/nvkelso/"
           "natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson")
    print("⤵️  Downloading Natural-Earth low-res polygons …")
    urllib.request.urlretrieve(url, NE_FILE)

with open(NE_FILE) as f:
    AFRICA_POLYS = [
        (feat["properties"]["ADM0_A3"], shape(feat["geometry"]))
        for feat in json.load(f)["features"]
        if feat["properties"]["CONTINENT"] == "Africa"
    ]

def latlon_to_iso(lat, lon):
    pt = Point(lon, lat)
    for iso, poly in AFRICA_POLYS:
        if poly.contains(pt):
            return iso
    return None

# ---------------------------------------------------------------------------#
# Convert each NetCDF file → append to CSV (streaming, low-mem)
# ---------------------------------------------------------------------------#
WRITE_HEADER = not OUT_CSV.exists()
files = sorted(glob.glob(PATTERN))
if not files:
    sys.exit(f"❌  No files match pattern: {PATTERN}")

print(f"🔄  Processing {len(files)} NetCDF files → {OUT_CSV}")
for f in tqdm(files, unit="file"):
    try:
        ds = xr.open_dataset(f, engine="h5netcdf")

        # Fix 0-360 → -180-180 longitudes if needed
        if ds.lon.max() > 180:
            ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))

        # Choose correct lat slice direction
        lat_descending = ds.lat[0] > ds.lat[-1]
        lat_slice = slice(LAT_MAX, LAT_MIN) if lat_descending else slice(LAT_MIN, LAT_MAX)

        da = ds[VAR].sel(lat=lat_slice, lon=slice(LON_MIN, LON_MAX))

        # Resample to monthly means regardless of source frequency
        if "time" in da.dims:
            da = da.resample(time="MS").mean(skipna=True)

        df = (da.to_dataframe(name="value")
                .reset_index()
                .dropna(subset=["value"]))

        df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-01")
        df.drop(columns=["time"], inplace=True)

        # ISO tag
        df["country_iso"] = [latlon_to_iso(lat, lon) for lat, lon in zip(df.lat, df.lon)]
        df.dropna(subset=["country_iso"], inplace=True)
        df = df[["country_iso", "date", "lat", "lon", "value"]]

        df.to_csv(OUT_CSV, mode="a", header=WRITE_HEADER, index=False)
        WRITE_HEADER = False
        ds.close()

    except Exception as e:
        print("⚠️  Skipping", f, "→", e)

if WRITE_HEADER:  # nothing written
    print("❌  No rows matched the Africa bbox or variable name. CSV not created.")
else:
    print(f"✅  Finished. Rows in file: {sum(1 for _ in open(OUT_CSV))}")
