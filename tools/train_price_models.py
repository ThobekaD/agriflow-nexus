#!/usr/bin/env python

# agriflow-nexus/tools/train_price_models.py
"""
Batch-train every distinct commodity found in ag_flow.commodity_prices_sadc_view
and store the ARIMA_PLUS model in ag_flow_ml.<commodity>_forecast
"""
#!/usr/bin/env python
import sys, pathlib           
sys.path.append(               
    str(pathlib.Path(__file__).resolve().parent.parent)
)                              

from google.cloud import bigquery
from agents.price_predictor import PricePredictor
client = bigquery.Client(location="africa-south1")
pp     = PricePredictor()

# 1. get the list of commodities we have data for
rows = client.query("""
    SELECT DISTINCT commodity
    FROM `ag_flow.commodity_prices_sadc`
    ORDER BY commodity
""").result()
commodities = [r.commodity for r in rows]

print(f"Found {len(commodities)} commodities → training…\n")

# 2. call the agent’s private _train_ml() once per commodity
for comm in commodities:
    ok = pp._train_ml(comm)
    status = "✅" if ok else "⚠️  failed – rolling mean fallback will be used"
    print(f"{status}  {comm}")

print("\nDone!")
