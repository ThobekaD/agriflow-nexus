
# ag-optimizer/scripts/day3_4.sh
# ------------------------------------------------------------------
#  Day-3-4 one-shot ETL (2003–2023 slice)
#  BigQuery location: africa-south1
# ------------------------------------------------------------------
set -euo pipefail

PROJECT="fieldsense-optimizer"
CORE="asco_core"       # raw/source tables
DERIVED="asco_derived" # analytical marts
LOCATION="africa-south1"

# 1) Make sure we're in the right GCP project
gcloud config set project "$PROJECT"

# 2) Ensure the derived dataset exists
if ! bq --location="$LOCATION" ls -d "$DERIVED" &>/dev/null; then
  echo "🆕 Creating dataset $DERIVED"
  bq --location="$LOCATION" mk --dataset "$DERIVED" || true
else
  echo "✅ Dataset $DERIVED already exists"
fi

# 3) Quick sanity counts
bq query --location="$LOCATION" --use_legacy_sql=false --format=prettyjson "
SELECT 'acled_events'     AS tbl, COUNT(*) AS row_cnt FROM \`$CORE.acled_events\`
UNION ALL
SELECT 'gadm_lvl2'        AS tbl, COUNT(*)       FROM \`$CORE.gadm_lvl2\`
UNION ALL
SELECT 'crude_oil_prices' AS tbl, COUNT(*)       FROM \`$CORE.crude_oil_prices\`;"

# 4) Build / refresh acled_events_geo (filter to 2003–2023)
echo "🔄 Building $CORE.acled_events_geo …"
bq query --location="$LOCATION" --use_legacy_sql=false "
CREATE OR REPLACE TABLE \`$CORE.acled_events_geo\`
PARTITION BY DATE_TRUNC(date, MONTH)
CLUSTER BY country_iso AS
SELECT
  *,
  ST_GEOGPOINT(lon, lat)                      AS geom,
  EXTRACT(YEAR FROM date)                     AS year
FROM   \`$CORE.acled_events\`
WHERE  lat IS NOT NULL
  AND  lon IS NOT NULL
  AND  EXTRACT(YEAR FROM date) BETWEEN 2003 AND 2023;
"

# 5) Spatial join ACLED × GADM-lvl2
echo "🗺️  Creating $DERIVED.acled_l2 …"
bq query --location="$LOCATION" --use_legacy_sql=false "
CREATE OR REPLACE TABLE \`$DERIVED.acled_l2\`
PARTITION BY DATE_TRUNC(date, MONTH)
CLUSTER BY GID_2 AS
SELECT a.*,
       g.GID_0, g.GID_1, g.NAME_1, g.GID_2, g.NAME_2
FROM   \`$CORE.acled_events_geo\` a
JOIN   \`$CORE.gadm_lvl2\`      g
ON     ST_INTERSECTS(a.geom, g.geom);
"

# 6) Enrich with yearly crude-oil price
echo "💲 Enriching with crude oil prices …"
bq query --location="$LOCATION" --use_legacy_sql=false "
CREATE OR REPLACE TABLE \`$DERIVED.acled_enriched\`
PARTITION BY DATE_TRUNC(date, MONTH)
CLUSTER BY GID_2 AS
SELECT e.*,
       p.usd_per_bbl
FROM   \`$DERIVED.acled_l2\`  e
LEFT JOIN \`$CORE.crude_oil_prices\` p
  ON e.year = p.year;
"

# 7) Build region-year KPI table (no partitioning needed)
echo "📊 Building $DERIVED.kpi_region_year …"
bq query --location="$LOCATION" --use_legacy_sql=false "
CREATE OR REPLACE TABLE \`$DERIVED.kpi_region_year\` AS
SELECT NAME_1,
       year,
       COUNT(*)        AS events,
       SUM(fatalities) AS deaths
FROM   \`$DERIVED.acled_enriched\`
GROUP  BY NAME_1, year;
"

echo -e "\n🎉 Day-3-4 pipeline finished! 🎉\n"
