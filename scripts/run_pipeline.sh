#!/usr/bin/env bash
# scripts/run_pipeline.sh  ── one-shot + QA + helper commands
# -------------------------------------------------------------
#  • reruns the 2003-2023 ETL
#  • basic QA queries
#  • echoes Git & Cloud-Scheduler helpers
# -------------------------------------------------------------
set -euo pipefail

PROJECT="fieldsense-optimizer"
CORE="asco_core"
DERIVED="asco_derived"
LOCATION="africa-south1"

# ──────────────────────────────────────────────────────────────
echo "🔐 1) Selecting GCP project …"
gcloud config set project "$PROJECT" >/dev/null

# ──────────────────────────────────────────────────────────────
echo "🏗️  2) Ensuring dataset ${DERIVED} exists …"
bq --location="$LOCATION" mk --dataset "$DERIVED" 2>/dev/null || \
  echo "   ↳ already there."
# ──────────────────────────────────────────────────────────────
echo "🔍 4) Spot-check tables …"
bq query --location="$LOCATION" --use_legacy_sql=false --format=prettyjson "
SELECT 'acled_enriched' AS tbl,
       MIN(year) AS min_y,
       MAX(year) AS max_y,
       COUNT(*)  AS rows
FROM \`${DERIVED}.acled_enriched\`;
"

echo "🎲  Random sample:"
bq query --location="$LOCATION" --use_legacy_sql=false --format=prettyjson "
SELECT event_date, country_iso, NAME_1, NAME_2,
       usd_per_bbl, fatalities
FROM   \`${DERIVED}.acled_enriched\`
ORDER  BY RAND()
LIMIT 10;
"

# ──────────────────────────────────────────────────────────────
echo "💡 5) Next manual steps — copy/paste as needed:"
cat <<'EOF'

# 5-A  Commit + push
git add scripts/day3_4.sh scripts/run_pipeline.sh docs/data_lineage_day3_4.md
git commit -m "feat: unified ETL + QA script (2003-23)"
git push origin main
git tag v1.0-day4 && git push --tags

# 5-B  OPTIONAL — schedule weekly rerun (Mon 03:00)
gcloud scheduler jobs create cron ag-optimizer-pipeline \
    --schedule="0 3 * * 1" --location=africa-south1 \
    --time-zone="Africa/Johannesburg" \
    --uri="https://storage.googleapis.com/<YOUR_BUCKET>/run_pipeline.sh" \
    --http-method=GET

# 5-C  OPTIONAL — open Looker Studio and build a viz on:
#      asco_derived.kpi_region_year
EOF

echo -e "\n✅  Done.  Review the two QA blocks above, then follow the Git or Scheduler hints if required."
