# agriflow-nexus/main.py
"""
AgriFlow Nexus – CLI bootstrap chain
FieldSentinel → WeatherOracle → PricePredictor → ConflictGuard → LogisticsMaster
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent))

from agents.field_sentinel   import FieldSentinel
from agents.weather_oracle   import WeatherOracle
from agents.price_predictor  import PricePredictor
from agents.conflict_guard   import ConflictGuard
from agents.logistics_master import LogisticsMaster
from utils.farm_locations    import FARMS_BY_COUNTRY          # ← NEW
from orchestrator            import Orchestrator

AGENTS = [
    FieldSentinel(),
    WeatherOracle(),
    PricePredictor(),
    ConflictGuard(),
    LogisticsMaster(),
]

ROUTE = {
    "field_sentinel":  "weather_oracle",
    "weather_oracle":  "price_predictor",
    "price_predictor": "conflict_guard",
    "conflict_guard":  "logistics_master",
}

if __name__ == "__main__":
    orch = Orchestrator()
    seed_payload = {
        "country_iso": "BWA",
        "commodity":   "Barley",
        "horizon":     12,
        "start_coord": (-24.65, 25.91),    
        "end_coord"  : (-25.90, 28.20), 
        "farm_coords": FARMS_BY_COUNTRY["BWA"],
        "routes": [
            {"truck": "T1", "stops": []},
            {"truck": "T2", "stops": list(FARMS_BY_COUNTRY["BWA"].keys())},
        ],
    }
    orch.start(seed_payload)        # ← hand over a dict, not a Message