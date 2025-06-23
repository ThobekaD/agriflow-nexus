# agriflow-nexus/agents/negotiation_agent.py
from __future__ import annotations
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from google.cloud import bigquery, aiplatform
import vertexai
from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import asyncio
import json
from config.config import Config
DATASET = Config.BIGQUERY_DATASET     # everywhere

class NegotiationAgent(BaseAgent):
    """
    Handles complex multi-party negotiations between farmers, transporters, and buyers.
    """
    def __init__(self):
        super().__init__("negotiation_agent", "Negotiation Agent")

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a simulated negotiation based on the parties and constraints provided.
        """
        parties = data.get("negotiation_parties", [])
        if not parties:
            return {**data, "negotiation_outcome": "No negotiation required."}

        print("NegotiationAgent: Starting negotiation session...")
        agreement = self._run_negotiation_rounds(parties)
        
        return {
            **data,
            "negotiation_agreement": agreement,
        }

    def _run_negotiation_rounds(self, parties: List[Dict]) -> Dict:
        """Simulates negotiation rounds to find a compromise."""
        # This is a simplified model of negotiation
        farmer = next((p for p in parties if p['type'] == 'farmer'), None)
        buyer = next((p for p in parties if p['type'] == 'buyer'), None)

        if not farmer or not buyer:
            return {"status": "failed", "reason": "Missing parties."}
        
        min_price = farmer['constraints']['min_price']
        max_price = buyer['constraints']['max_price']

        if min_price > max_price:
            return {"status": "failed", "reason": "No price overlap."}

        # Simple compromise: meet in the middle
        agreed_price = (min_price + max_price) / 2
        
        print(f"NegotiationAgent: Agreement reached at price {agreed_price:.2f}")

        return {
            "status": "success",
            "agreed_price": round(agreed_price, 2),
            "quality": buyer['constraints']['quality'],
            "parties": [farmer['id'], buyer['id']]
        }

    def communicate_with_agent(self, target_agent: str, message: Dict[str, Any]) -> bool:
        print(f"NegotiationAgent -> {target_agent}: Negotiation outcome shared.")
        return True
