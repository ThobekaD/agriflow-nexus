
## agriflow-nexus/agents/field_sentinel.py
from __future__ import annotations
from datetime import datetime, timedelta, date
from typing import Dict, Any
from google.cloud import bigquery
from config.config import Config
from agents.base_agent import BaseAgent

DATASET   = Config.BIGQUERY_DATASET           
PRECIP_T  = "precip_sadc"
SOIL_T    = "soil_moist_sadc"

class FieldSentinel(BaseAgent):
    """Detect drought or flood risk for the last 30 days."""
    def __init__(self) -> None:
        super().__init__("field_sentinel", "Field Sentinel")
        self.client = bigquery.Client(location=Config.CLOUD_REGION)
        self.status = "ready"

    # -------------- BaseAgent hooks --------------------
    def communicate_with_agent(self, tgt: str, msg: Dict[str, Any]) -> bool:
        print(f"FieldSentinel → {tgt}: {msg['risk']}")
        return True

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        iso   = data.get("country_iso", "BWA")
        end   = self._latest_date(iso)

        # --- NEW: ensure end is a datetime.date -----------------------
        if isinstance(end, str):
            end = datetime.fromisoformat(end).date()
        elif isinstance(end, datetime):
            end = end.date()
        # --------------------------------------------------------------

        start = end - timedelta(days=30)
        risk  = self._risk_score(iso, start, end)

        return {
            **data,
            "window":       f"{start} → {end}",
            "risk":         risk,
            "origin":       "FieldSentinel",
            "generated_at": datetime.utcnow().isoformat(),
        }

    # --- helpers --------------------------------------------------
    def _latest_date(self, iso: str):
        sql = f"""
        SELECT MAX(DATE(date)) AS max_d              -- ▲ PATCH ① (cast)
        FROM `{Config.PROJECT_ID}.{DATASET}.{PRECIP_T}`
        WHERE country_iso=@iso"""
        row = next(self.client.query(
            sql,
            bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("iso","STRING",iso)]
            )).result(), None)
        return row.max_d or datetime(2023,12,31).date()

    def _risk_score(self, iso, start, end):
        sql = f"""
        SELECT
            CASE
                WHEN pr.avg_precip < 2 AND sm.avg_soil < 30 THEN 'drought'
                WHEN pr.avg_precip > 8 AND sm.avg_soil > 80 THEN 'flood'
                ELSE 'normal'
            END AS risk
        FROM
            (SELECT AVG(value) AS avg_precip FROM `{Config.PROJECT_ID}.{DATASET}.{PRECIP_T}` WHERE country_iso=@iso AND DATE(date) BETWEEN @s AND @e) AS pr,
            (SELECT AVG(value) AS avg_soil FROM `{Config.PROJECT_ID}.{DATASET}.{SOIL_T}` WHERE country_iso=@iso AND DATE(date) BETWEEN @s AND @e) AS sm
        """

        row = next(self.client.query(
            sql,
            bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("iso","STRING",iso),
                bigquery.ScalarQueryParameter("s","DATE",start),
                bigquery.ScalarQueryParameter("e","DATE",end),
            ])
        ).result(), None)
        # Check if row or row.risk is None, which happens if there's no data at all
        return row.risk if row and row.risk is not None else "normal"