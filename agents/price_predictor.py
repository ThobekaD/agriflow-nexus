
#!/usr/bin/env python
# agriflow-nexus/agents/price_predictor.py
"""
PricePredictor
──────────────
Cascade:
  ① BigQuery ML (ARIMA_PLUS)
  ② five-year rolling mean  (+diesel trend)
  ③ country–commodity spot table
  ④ random stub
"""
from __future__ import annotations
import re, random
from datetime import datetime
from typing import Dict, Any

from google.cloud import bigquery
from google.api_core.exceptions import BadRequest, GoogleAPICallError

from config.config import Config
from agents.base_agent import BaseAgent
from utils.commodity_spot_prices import PRICES

# ── constants ─────────────────────────────────────────────────────────
DATASET_RAW = Config.BIGQUERY_DATASET            # ag_flow
DATASET_ML  = f"{Config.BIGQUERY_DATASET}_ml"    # ag_flow_ml
COMMODITY_T = "commodity_prices_sadc"
DIESEL_T    = "fuel_price_sadc"
ROLLING_W   = 5
LOCATION    = Config.CLOUD_REGION
# ──────────────────────────────────────────────────────────────────────


def _model_id(comm: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", comm.lower())
    return f"{DATASET_ML}.{safe}_forecast"


class PricePredictor(BaseAgent):
    def __init__(self):
        super().__init__("price_predictor", "Price Predictor")
        self.client = bigquery.Client(location=LOCATION)
        self.trained_ok: dict[str, bool | None] = {}

    # ------------------------------------------------------------------
    def communicate_with_agent(self, tgt: str, msg: Dict[str, Any]) -> bool:
        print(f"PricePredictor → {tgt}: {msg['commodity']} via {msg['method_used']}")
        return True

    # ------------------------------------------------------------------
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        commodity   = data.get("commodity", "Maize (corn)")
        horizon     = int(data.get("horizon", 12))
        shift_pct   = float(data.get("price_shift", 0)) / 100.0
        iso         = data.get("country_iso", "BWA")

        # (1) make sure a model exists
        if self.trained_ok.get(commodity) is None:
            self.trained_ok[commodity] = self._train_ml(commodity)

        # (2) cascade
        if self.trained_ok[commodity]:
            forecast, method = self._ml_forecast(_model_id(commodity), horizon), "bq_ml"
        else:
            forecast, method = self._rolling_mean_forecast(commodity, horizon), "rolling_mean"

        if not forecast:
            forecast, method = self._spot_forecast(iso, commodity, horizon), "spot_price"
        if not forecast:
            forecast, method = self._stub(horizon), "stub"

        # (3) optional manual shift
        if shift_pct:
            for p in forecast:
                p["price"] = round(p["price"] * (1 + shift_pct), 2)

        return {
            **{k: v for k, v in data.items() if k not in ("commodity", "horizon")},
            "commodity":    commodity,
            "forecast":     forecast,
            "method_used":  method,
            "origin":       "PricePredictor",
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ── ML layer ──────────────────────────────────────────────────────
    def _train_ml(self, commodity: str) -> bool:
        sql = f"""
        CREATE OR REPLACE MODEL `{_model_id(commodity)}`
        OPTIONS(model_type='ARIMA_PLUS',
                time_series_timestamp_col='date',
                time_series_data_col='price',
                auto_arima=TRUE) AS
        SELECT
          DATE_FROM_UNIX_DATE(0) + INTERVAL year-1970 YEAR AS date,
          price_usd_per_tonne AS price                        -- ← correct column
        FROM `{Config.PROJECT_ID}.{DATASET_RAW}.{COMMODITY_T}`
        WHERE LOWER(commodity)=LOWER(@c)
        """
        try:
            self.client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("c", "STRING", commodity)]
                ),
            ).result()
            return False
        except (BadRequest, GoogleAPICallError) as e:
            print(f"[PricePredictor] ML disabled → {e.message.splitlines()[0]}")
            return False

    def _ml_forecast(self, model: str, horizon: int):
        try:
            rows = self.client.query(
                f"""
                SELECT EXTRACT(YEAR FROM forecast_timestamp) AS year,
                       forecast_value                       AS price
                FROM ML.FORECAST(MODEL `{model}`, STRUCT(@h AS horizon))
                """,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("h", "INT64", horizon)]
                ),
            ).result()
            return [dict(r) for r in rows]
        except (BadRequest, GoogleAPICallError):
            self.trained_ok[model.split(".")[1].replace("_forecast", "")] = False
            return []

    # ── rolling-mean fallback ─────────────────────────────────────────
    def _rolling_mean_forecast(self, commodity: str, horizon: int):
        sql = f"""
        WITH cp AS (
          SELECT year,
                 AVG(price_usd_per_tonne) OVER
                     (ORDER BY year ROWS BETWEEN {ROLLING_W - 1} PRECEDING AND CURRENT ROW) AS ma
          FROM `{Config.PROJECT_ID}.{DATASET_RAW}.{COMMODITY_T}`
          WHERE LOWER(commodity)=LOWER(@c)
        ),
        dz AS (
          SELECT year,
                 AVG(diesel_price_usd) OVER
                     (ORDER BY year ROWS BETWEEN {ROLLING_W - 1} PRECEDING AND CURRENT ROW) AS diesel
          FROM (
            SELECT year,
                   AVG(CAST(value AS FLOAT64)) AS diesel_price_usd
            FROM `{Config.PROJECT_ID}.{DATASET_RAW}.{DIESEL_T}`
            WHERE fuel_type='Diesel'
            GROUP BY year
          )
        )
        SELECT
          (SELECT ma     FROM cp ORDER BY year DESC LIMIT 1) AS base,
          (SELECT diesel FROM dz ORDER BY year DESC LIMIT 1) AS diesel,
          (SELECT year   FROM cp ORDER BY year DESC LIMIT 1) AS y0
        """
        row = next(
            self.client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("c", "STRING", commodity)]
                ),
            ).result(),
            None,
        )
        if not row or any(row[k] is None for k in ("base", "diesel", "y0")):
            return []
        base, slope, y0 = float(row.base), (row.diesel / 1000.0), int(row.y0)
        return [
            {"year": y0 + i, "price": round(base * (1 + slope * i), 2)}
            for i in range(1, horizon + 1)
        ]


    # ── spot & stub ───────────────────────────────────────────────────
    @staticmethod
    def _spot_forecast(iso: str, commodity: str, horizon: int):
        spot = PRICES.get(iso, {}).get(commodity)
        if spot is None:
            return []
        y0 = datetime.utcnow().year
        return [{"year": y0 + i, "price": spot} for i in range(1, horizon + 1)]

    @staticmethod
    def _stub(horizon: int):
        y0 = datetime.utcnow().year
        return [
            {"year": y0 + i, "price": round(100 + random.uniform(-10, 10), 2)}
            for i in range(1, horizon + 1)
        ]
