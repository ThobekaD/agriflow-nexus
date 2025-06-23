#!/usr/bin/env python
import geopandas as gpd, pandas as pd, pathlib

RAW = pathlib.Path("data/sample/gadm_africa_lvl2.gpkg")   # original upload
OUT = pathlib.Path("data/clean/road_network_sadc.csv")    # will match other loaders

gdf = gpd.read_file(RAW)[["geometry", "NAME_0", "ISO_0"]]  # keep only what we need
gdf = gdf[gdf["ISO_0"].isin({                     # whitelist SADC
    "AGO","BWA","COM","COD","SWZ","LSO","MDG","MWI",
    "MUS","MOZ","NAM","SYC","ZAF","TZA","ZMB","ZWE"})
]

# convert geometry to WKT (text) because our ingest strips geometry anyway
gdf["wkt"] = gdf.geometry.apply(lambda geom: geom.wkt)
df = pd.DataFrame(gdf.drop(columns="geometry"))

df.to_csv(OUT, index=False)
print(f"✓ wrote cleaned roads to {OUT}")
