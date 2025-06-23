

# agriflow-nexus/agents/sustainability_agent.py
"""
SustainabilityAgent – synchronous version
Calculates carbon footprint, water usage & a simple social-impact proxy.
"""
from __future__ import annotations
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from config.config import Config

class SustainabilityAgent(BaseAgent):
    def __init__(self):
        super().__init__("sustainability_agent", "Sustainability Optimizer")
        self.carbon_factor = 2.68  # kg CO₂ / L diesel
        self.water_factor = {      # L water / kg produce
            # 22 trained commodities + default
            'Barley': 1425, 'Beans, dry': 5000, 'Cabbages': 200,
            'Cereals n.e.c.': 2000, 'Cow peas, dry': 4800,
            'Maize (corn)': 1222, 'Meat of cattle with the bone, fresh or chilled': 15400,
            'Meat of chickens, fresh or chilled': 4300,
            'Meat of goat, fresh or chilled': 8800,
            'Meat of pig with the bone, fresh or chilled': 6000,
            'Meat of sheep, fresh or chilled': 10400,
            'Millet': 4500, 'Potatoes': 250, 'Raw milk of cattle': 1000,
            'Rice': 4000, 'Sorghum': 2865, 'Soya beans': 2000,
            'Spinach': 300, 'Sugar cane': 200, 'Sunflower seed': 3300,
            'Tomatoes': 180, 'Wheat': 1827, 'default': 1500,
        }

    # ------------------------------------------------------------------
    def communicate_with_agent(self, tgt: str, msg: Dict[str, Any]) -> bool:
        print(f"SustainabilityAgent → {tgt}: metrics ready")
        return True

    # ------------------------------------------------------------------
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        routes   = data.get('routes', [])
        payload  = data.get('payload_tonnes', 10.0)
        
        # Get the list of commodities and use the first one for calculations.
        # Provide a default value if the list is missing or empty.
        commodities = data.get('commodities', [])
        commodity = commodities[0] if commodities else 'default'

        metrics = [self._route_metrics(r, payload, commodity) for r in routes]
        overall = self._overall_score(metrics)
        recs    = self._recommend(metrics)

        return {
            **data,
            'sustainability_metrics':        metrics,
            'overall_sustainability_score':  overall,
            'total_carbon_footprint_kg_co2': sum(m['carbon_footprint_kg_co2'] for m in metrics),
            'sustainability_recommendations': recs,
        }

    # ---------- helpers ------------------------------------------------
    def _route_metrics(self, route: Dict[str, Any], payload_t: float, commodity: str):
        FUEL_EFF = 3.0                            # km / L
        km = float(route.get('total_km', 0))
        liters = km / FUEL_EFF
        carbon = liters * self.carbon_factor
        water  = payload_t * 1000 * self.water_factor.get(commodity, self.water_factor['default'])
        social = 0.75
        grade  = self._grade(carbon, water, social)
        return {
            'truck_id': route.get('truck', 'N/A'),
            'carbon_footprint_kg_co2': round(carbon, 2),
            'estimated_water_usage_liters': round(water, 2),
            'social_impact_score': social,
            'sustainability_grade': grade,
        }

    @staticmethod
    def _grade(carbon, water, social) -> str:
        carbon_s = max(0, 1 - carbon / 10000)
        water_s  = max(0, 1 - water  / 5e7)
        score    = 0.4 * carbon_s + 0.3 * water_s + 0.3 * social
        return (
            'A+' if score >= .9 else
            'A'  if score >= .8 else
            'B'  if score >= .7 else
            'C'  if score >= .6 else
            'D'  if score >= .5 else 'F'
        )

    @staticmethod
    def _overall_score(metrics: List[Dict[str, Any]]) -> float:
        if not metrics:
            return 0.0
        g2s = {'A+': 1.0, 'A': 0.9, 'B': 0.8, 'C': 0.7, 'D': 0.6, 'F': 0.4}
        return round(sum(g2s[m['sustainability_grade']] for m in metrics) / len(metrics), 2)

    @staticmethod
    def _recommend(metrics: List[Dict[str, Any]]) -> List[str]:
        recs = []
        if sum(m['carbon_footprint_kg_co2'] for m in metrics) > 5000:
            recs.append("High carbon footprint – optimise routes or use greener trucks.")
        for m in metrics:
            if m['sustainability_grade'] in ('D', 'F'):
                truck_id = m.get('truck_id', 'N/A') # Safely get the truck ID
                recs.append(f"Truck {truck_id} graded {m['sustainability_grade']} – review distance & load.")
        return recs or ["Metrics within acceptable range – good job!"]