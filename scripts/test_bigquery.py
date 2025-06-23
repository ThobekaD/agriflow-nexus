from google.cloud import bigquery
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "fieldsense-optimizer-8a9980b3d49a.json"
print("Connecting …")
rows = bigquery.Client().query("SELECT CURRENT_DATE() AS today").result()
for r in rows:
    print("✅ BigQuery works, today is", r.today)
