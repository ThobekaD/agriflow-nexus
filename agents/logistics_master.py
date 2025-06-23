
# agriflow-nexus/agents/logistics_master.py
# LogisticsMaster – VRP + cost + rest-stops + road-snap
from __future__ import annotations
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt, ceil
from typing import Dict, List, Tuple, Any

from ortools.constraint_solver import pywrapcp
from google.cloud import bigquery
import shapely.wkt, shapely.geometry, shapely.strtree       # ↩ pip install shapely

from agents.base_agent import BaseAgent
from utils.country_meta import DIESEL_USD_L, PETROL_USD_L
from config.config import Config

DATASET = Config.BIGQUERY_DATASET
ROAD_T  = "road_network_sadc"

# --- constants --------------------------------------------------------
FUEL_EFF_KM_PER_L = 3.0
REST_INTERVAL_KM  = 500
# ---------------------------------------------------------------------


def _km(p: Tuple[float, float], q: Tuple[float, float]) -> float:
    R = 6371
    dlat, dlon = map(radians, (q[0] - p[0], q[1] - p[1]))
    a = (sin(dlat / 2)**2 +
         cos(radians(p[0])) * cos(radians(q[0])) * sin(dlon / 2)**2)
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _pump(iso: str, fuel="diesel"):
    tbl = DIESEL_USD_L if fuel == "diesel" else PETROL_USD_L
    return tbl.get(iso, 1.35)


class LogisticsMaster(BaseAgent):
    """VRP + road-snap final leg + risk/fuel/ESG additives."""
    def __init__(self):
        super().__init__("logistics_master", "Logistics Master")
        self._road_index = None       # lazy-loaded

    # ---------- messaging ----------
    def communicate_with_agent(self, tgt: str, msg: Dict[str, Any]) -> bool:
        print("LogisticsMaster final plan →", tgt)
        return True

    # ---------- main ----------
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        farms      = data["farm_coords"]
        start      = data["start_coord"]
        end        = data["end_coord"]
        iso        = data.get("country_iso", "BWA")
        payload_t  = float(data.get("payload_tonnes", 10.0))

        # OR-Tools distance matrix
        customers  = list(farms)
        coords     = [start] + [farms[c] for c in customers]
        n          = len(coords)
        dist = [[int(_km(coords[i], coords[j]) * 1000) for j in range(n)]
                for i in range(n)]

        mgr = pywrapcp.RoutingIndexManager(n, 2, 0)
        rt  = pywrapcp.RoutingModel(mgr)
        cb  = rt.RegisterTransitCallback(
            lambda i, j: dist[mgr.IndexToNode(i)][mgr.IndexToNode(j)])
        rt.SetArcCostEvaluatorOfAllVehicles(cb)

        search = pywrapcp.DefaultRoutingSearchParameters()
        search.time_limit.seconds = 5
        sol = rt.SolveWithParameters(search)

        routes: List[Dict[str, any]] = []
        if sol:
            for v in range(2):
                idx, metres = rt.Start(v), 0
                path: List[str] = []
                while not rt.IsEnd(idx):
                    nxt = sol.Value(rt.NextVar(idx))
                    metres += dist[mgr.IndexToNode(idx)][mgr.IndexToNode(nxt)]
                    node = mgr.IndexToNode(nxt)
                    if node:                           # node 0 == depot
                        path.append(customers[node - 1])
                    idx = nxt

                last_stop = start if not path else farms[path[-1]]
                final_leg_km = self._road_snap_km(last_stop, end, iso)
                total_km = metres / 1000 + final_leg_km

                routes.append({
                    "truck":        f"T{v + 1}",
                    "stops":        path,
                    "distance_km":  round(metres / 1000, 1),
                    "final_leg_km": round(final_leg_km, 1),
                    "total_km":     round(total_km, 1),
                    "eta_hours":    round(total_km / 60, 2),
                    "rest_stops":   max(0, ceil(total_km / REST_INTERVAL_KM) - 1),
                })

        # --- merge conflict risk (if upstream agent ran) ----------------
        risk_map = {ra["route"]["truck"]: ra
                    for ra in data.get("risk_assessments", [])}
        for r in routes:
            ra              = risk_map.get(r["truck"], {})
            r["risk_level"] = ra.get("risk_level", "low")
            r["conflicts"]  = ra.get("conflicts", [])

        # --- fuel & cost-to-serve --------------------------------------
        diesel_usd = _pump(iso)
        for r in routes:
            litres = r["total_km"] / FUEL_EFF_KM_PER_L
            cost   = litres * diesel_usd
            r["fuel_usd"]       = round(cost, 2)
            r["cost_per_tonne"] = round(cost / payload_t, 2)

        return {
            **data,
            "routes": routes,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ---------- helpers ----------
    def _road_snap_km(self, point_latlon, end_latlon, iso):
        """Return km from (point→end), snapped to nearest road if possible."""
        # lazy-load once
        if self._road_index is None:
            self._load_roads(iso)

        pt = shapely.geometry.Point(point_latlon[1], point_latlon[0])      # lon, lat
        try:                                        # ▲ PATCH ④ – robust nearest
            nearest_geom = (self._road_index.nearest(pt)
                            if self._road_index else None)
            # shapely 2.0 returns an index (numpy.int64); resolve it
            if hasattr(nearest_geom, "__iter__") or hasattr(nearest_geom, "geom_type"):
                geom = nearest_geom
            elif nearest_geom is not None:          # numeric index
                geom = self._road_index.geometries[nearest_geom]
            else:
                geom = None

            if geom is None or not hasattr(geom, "interpolate"):
                return _km(point_latlon, end_latlon)    # plain straight-line
            snapped_pt = geom.interpolate(geom.project(pt))
            return _km((snapped_pt.y, snapped_pt.x), end_latlon)
        except Exception:
            return _km(point_latlon, end_latlon)        # graceful fallback

    def _load_roads(self, iso):
        sql = f"SELECT wkt FROM `{Config.PROJECT_ID}.{DATASET}.{ROAD_T}` WHERE country_iso='{iso}'"
        rows = bigquery.Client().query(sql).result()
        segs = [shapely.wkt.loads(r.wkt) for r in rows]
        self._road_index = shapely.strtree.STRtree(segs) if segs else None
