
# agriflow-nexus/orchestrator.py
"""
Synchronous pass-the-parcel orchestrator with a parallel
PricePredictor pool (ML ➔ rolling mean ➔ spot-price ➔ stub).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
import json, concurrent.futures as cf, asyncio
from config.config import Config

# ── Agents ------------------------------------------------------------
from agents.field_sentinel           import FieldSentinel
from agents.weather_oracle           import WeatherOracle
from agents.price_predictor          import PricePredictor
from agents.conflict_guard           import ConflictGuard
from agents.logistics_master         import LogisticsMaster
from agents.sustainability_agent     import SustainabilityAgent
from agents.adaptive_learning_agent  import AdaptiveLearningAgent


@dataclass
class Message:
    payload: Dict[str, Any]
    source: str
    dest: Optional[str]
    created_at: datetime = datetime.utcnow()

class Orchestrator:
    def __init__(self):
        self.registry = {
            "field_sentinel":          FieldSentinel(),
            "weather_oracle":          WeatherOracle(),
            "price_predictor":         PricePredictor(),
            "conflict_guard":          ConflictGuard(),
            "logistics_master":        LogisticsMaster(),
            "sustainability_agent":    SustainabilityAgent(),
            "adaptive_learning_agent": AdaptiveLearningAgent(),
        }

    # ------------------------------------------------------------------
    def _exec(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run an agent & transparently await coroutines."""
        try:
            agent = self.registry[name]
            out = agent.process_data(payload)
            if asyncio.iscoroutine(out):
                out = asyncio.run(out)
            print(f"✓ {name}")
            return out
        except Exception as e:
            print(f"⚠️  {name} failed → {e}")
            return payload  # pass-through on failure

    # ------------------------------------------------------------------
    def start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Stage 1 – parallel (run all except price predictor)
        stage1 = ["weather_oracle", "conflict_guard", "field_sentinel"]
        with cf.ThreadPoolExecutor(max_workers=len(stage1)) as ex:
            futures = {ex.submit(self._exec, n, payload): n for n in stage1}
            merged  = payload.copy()
            for f in cf.as_completed(futures):
                merged.update(f.result())

        # Stage 1.5 – Price Forecasting Loop for each commodity
        all_forecasts = {}
        commodities = payload.get("commodities", [])
        if commodities:
            price_predictor_agent = self.registry["price_predictor"]
            for comm in commodities:
                # Create a specific payload for this commodity
                price_payload = merged.copy()
                price_payload["commodity"] = comm
                
                # Run the agent
                price_result = price_predictor_agent.process_data(price_payload)
                
                # Store the forecast
                if "forecast" in price_result:
                    all_forecasts[comm] = price_result["forecast"]
            
            # Add the collected forecasts to the main result
            merged["commodity_forecasts"] = all_forecasts

        # Stage 2 – sequential
        merged.update(self._exec("logistics_master",     merged))
        merged.update(self._exec("sustainability_agent", merged))

        # Stage 3 – learning
        final = self._exec("adaptive_learning_agent", merged)

        print("\n=== FINAL OUTPUT ===")
        print(json.dumps(final, indent=2, default=str))
        return final
