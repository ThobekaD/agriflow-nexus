# development_log.md
## Day 1  –  Data Foundations (17 Jun 2025)

### Completed
- ✔️  Generated Africa-wide weather layers  
  - `temp_max_africa` (tasmax, 2003-2019)  
  - `precip_africa` (pr, 2003-2019)  
  - `soil_moist_africa` (sm, 2003-2023)
- ✔️  Loaded weather CSVs into BigQuery dataset **asco_core**
- ✔️  Converted HOTOSM / gROADS roads data → `africa_roads` BigQuery GIS table
- ✔️  Extracted 2003-2023 commodity prices from World-Bank workbook → `commodity_prices`
- ✔️  Ingested FAOSTAT Country Investment Statistics → `country_investment`
- ✔️  Added `.gitignore` rule to keep large CSVs out of Git

### Notes / Challenges
- CRU & C3S datasets use descending latitude; added auto-slice fix in `nc_to_csv_africa.py`.
- `bq` CLI required **gcloud init --console-only** due to Safari HTTPS-only issue.

### Next (Day 2)
1. Code **WeatherOracle** agent to query `asco_core` tables.
2. Stub **FieldSentinel** (single farm lat/lon → ISO3).
3. Test ADK orchestrator FieldSentinel → WeatherOracle → console output.

_Total time spent: 10 h (weather 4 h, roads 1 h, prices 2 h, FAO 1 h, docs 1 h,
troubleshooting 1 h)._

- Re-downloaded full gROADS shapefile set ( .shp .shx .dbf .prj )
- Recreated missing .shx with `SHAPE_RESTORE_SHX=YES` (if applicable)
- Converted to GeoJSONSeq and loaded into BigQuery as `asco_core.africa_roads`

### Commodity prices (revised)

- Extracted **all 55 World-Bank ag commodities** (nominal & real) for 2003-2023  
  using `scripts/extract_all_commodities.py` → 100 k+ tidy rows  
- Loaded into BigQuery as **asco_core.commodity_prices_all**  
  (schema: Year, price, commodity, unit, series_type)

### 18 Jun 2025 – Commodity price ingestion
- Added `scripts/extract_all_commodities.py`
- Extracted all World-Bank ag commodities (nominal + real) for 2003-2023
  → `data/sample/commodity_prices_2003_2023.csv`
- Loaded into BigQuery as `asco_core.commodity_prices_all`

