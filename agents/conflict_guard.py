# agriflow-nexus/agents/conflict_guard.py
# ConflictGuard: spatially scans ACLED for recent events near routes
from __future__ import annotations
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any, List

from google.cloud import bigquery
from agents.base_agent import BaseAgent
from config.config import Config

DATASET = Config.BIGQUERY_DATASET


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km."""
    R = 6371
    dlat, dlon = map(radians, (lat2 - lat1, lon2 - lon1))
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


class ConflictGuard(BaseAgent):
    """Scans ACLED table for recent conflicts near each planned route."""
    def __init__(self):
        super().__init__("conflict_guard", "Conflict Guard")
        self.client = bigquery.Client()
        self.status = "ready"

    # ---------- BaseAgent ----------
    def communicate_with_agent(self, tgt: str, msg: Dict[str, Any]) -> bool:
        print(f"ConflictGuard → {tgt}: risk assessment ready")
        return True

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        routes      = data.get("routes", [])
        farm_coords = data.get("farm_coords", {})
        assessments = [self._assess_route(r, farm_coords) for r in routes]

        return {
            **data,
            "risk_assessments": assessments,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ---------- helpers ----------
    def _assess_route(self, route, farm_coords):
        stops = route.get("stops", [])
        if not stops:
            return {"route": route, "risk_level": "low", "conflicts": []}

        pts = [farm_coords[s] for s in stops if s in farm_coords]
        if not pts:
            return {"route": route, "risk_level": "low", "conflicts": []}

        lat_min = min(p[0] for p in pts) - .5
        lat_max = max(p[0] for p in pts) + .5
        lon_min = min(p[1] for p in pts) - .5
        lon_max = max(p[1] for p in pts) + .5
        conflicts = self._recent_conflicts(lat_min, lat_max, lon_min, lon_max)

        # enrich events with distance + severity
        ref_lat, ref_lon = pts[0]
        for ev in conflicts:
            ev["distance_km"] = round(_haversine(ref_lat, ref_lon,
                                                 ev["latitude"], ev["longitude"]), 1)
            ev["severity"] = min(1.0, ev["fatalities"] / 10)

        # decide risk level
        fatals = sum(ev["fatalities"] for ev in conflicts)
        lvl = ("high" if fatals > 10 or len(conflicts) > 5
               else "medium" if conflicts else "low")

        return {"route": route, "risk_level": lvl, "conflicts": conflicts}

    def _recent_conflicts(self, lat_min, lat_max, lon_min, lon_max):
        end   = datetime.utcnow().date()
        start = end - timedelta(days=90)

        sql = f"""
        SELECT date, event, sub_event, fatalities,
               lat   AS latitude,
               lon   AS longitude
        FROM `{self.client.project}.{DATASET}.acled_events_sadc`
        WHERE date BETWEEN @s AND @e
          AND lat BETWEEN @lat_min AND @lat_max
          AND lon BETWEEN @lon_min AND @lon_max
        """

        try:
            rows = self.client.query(
                sql,
                bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("s", "DATE",   start),
                        bigquery.ScalarQueryParameter("e", "DATE",   end),
                        bigquery.ScalarQueryParameter("lat_min", "FLOAT64", lat_min),
                        bigquery.ScalarQueryParameter("lat_max", "FLOAT64", lat_max),
                        bigquery.ScalarQueryParameter("lon_min", "FLOAT64", lon_min),
                        bigquery.ScalarQueryParameter("lon_max", "FLOAT64", lon_max),
                    ]
                ),
            ).result()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[ConflictGuard] query failed → {exc}")
            return []

