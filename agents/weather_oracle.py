# agriflow-nexus/agents/weather_oracle.py
# WeatherOracle agent for weather forecasting and data retrieval
# Produces 7day country wide forecast windows
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Any
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from agents.base_agent import BaseAgent
from config.config import Config

DATASET   = Config.BIGQUERY_DATASET         
PRECIP_T  = "precip_sadc"
SOIL_T    = "soil_moist_sadc"
TMAX_T    = "temp_sadc"

class WeatherOracle(BaseAgent):
    def __init__(self) -> None:
        super().__init__("weather_oracle", "Weather Oracle")
        self.client = bigquery.Client()
        self.status = "ready"

    # ---------- BaseAgent ----------
    def communicate_with_agent(self, target_agent: str,
                               message: Dict[str, Any]) -> bool:
        print(f"WeatherOracle → {target_agent}: "
              f"{len(message['forecast'])}-day forecast ready")
        return True

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        iso   = data["country_iso"]
        start = data.get("start", datetime.utcnow().date())
        days  = int(data.get("days", 7))

        sql = f"""
        WITH pr AS (
          SELECT DATE(date) AS d, AVG(value) AS pr 
          FROM `{self.client.project}.{DATASET}.{PRECIP_T}`
          WHERE country_iso=@iso
            AND DATE(date) BETWEEN @start AND DATE_ADD(@start, INTERVAL @d DAY)
          GROUP BY d
        ),
        sm AS (
          SELECT DATE(date) AS d, AVG(value) AS sm
          FROM `{self.client.project}.{DATASET}.{SOIL_T}`
          WHERE country_iso=@iso
            AND DATE(date) BETWEEN @start AND DATE_ADD(@start, INTERVAL @d DAY)
          GROUP BY d
        ),
        tx AS (
          SELECT DATE(date) AS d, AVG(value) AS tmax
          FROM `{self.client.project}.{DATASET}.{TMAX_T}`
          WHERE country_iso=@iso
            AND DATE(date) BETWEEN @start AND DATE_ADD(@start, INTERVAL @d DAY)
          GROUP BY d
        )
        SELECT
          COALESCE(pr.d, sm.d, tx.d) AS date,
          pr.pr, sm.sm, tx.tmax,
          CASE
            WHEN pr.pr < 2  AND sm.sm < 60 THEN 'good_harvest_window'
            WHEN pr.pr > 10 AND sm.sm > 80 THEN 'high_flood_risk'
            ELSE 'normal'
          END AS tag
        FROM pr
        FULL OUTER JOIN sm ON pr.d = sm.d
        FULL OUTER JOIN tx ON COALESCE(pr.d, sm.d) = tx.d
        ORDER BY date
        """

        try:
            rows = [
                dict(r) for r in self.client.query(
                    sql,
                    job_config=bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("iso",   "STRING", iso),
                            bigquery.ScalarQueryParameter("start", "DATE",   start),
                            bigquery.ScalarQueryParameter("d",     "INT64",  days),
                        ]
                    ),
                ).result()
            ]
        except NotFound as e:
            print("[WeatherOracle] BigQuery tables missing – falling back to mock data")
            rows = [
                {
                    "date": str(start + timedelta(i)),
                    "pr": 0,
                    "tmax": 30,
                    "sm": 50,
                    "tag": "good_harvest_window" if i in (2, 3) else None,
                }
                for i in range(days)
            ]

        return {
            **data,
            "forecast": rows,
            "origin": "WeatherOracle",
            "generated_at": datetime.utcnow().isoformat(),
        }
