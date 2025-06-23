# agriflow-nexus/agents/adaptive_learning_agent.py
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

class AdaptiveLearningAgent(BaseAgent):
    """
    Agent that learns from outcomes and continuously improves predictions.
    Uses a custom ML model that is retrained with feedback.
    """
    def __init__(self):
        super().__init__("adaptive_learning", "Adaptive Learning Agent")
        self.client = bigquery.Client()
        try:
            vertexai.init()
        except Exception as e:
            print(f"Vertex AI initialization failed: {e}. Some features may be disabled.")
        self.model_cache: Dict[str, Any] = {}
        self.feedback_buffer: List[Dict[str, Any]] = []
        self.status = "ready"

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes new data by first learning from any available feedback,
        then generating enhanced predictions based on the updated models.
        """
        # In a real-world scenario, this would be an async call
        # For this synchronous orchestrator, we'll run it directly
        self._update_models_from_feedback_sync()
        
        model_confidence = self._calculate_confidence()
        print(f"AdaptiveLearningAgent: Model confidence is {model_confidence:.2f}")

        return {
            **data,
            "model_confidence": model_confidence,
            "learning_iteration": len(self.model_cache.get('history', []))
        }

    def _update_models_from_feedback_sync(self):
        """
        Synchronous version of model update for the current orchestrator.
        """
        if len(self.feedback_buffer) < 10:
            return

        print(f"AdaptiveLearningAgent: Updating models with {len(self.feedback_buffer)} new feedback points.")
        df = pd.DataFrame(self.feedback_buffer)
        
        if 'actual_price' in df.columns and not df['actual_price'].isnull().all():
            df_train = df.dropna(subset=['actual_price', 'weather_score', 'conflict_risk', 'logistics_cost'])
            if len(df_train) < 10:
                return

            X = df_train[['weather_score', 'conflict_risk', 'logistics_cost']].values
            y = df_train['actual_price'].values
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(X_scaled, y)
            
            score = model.score(X_scaled, y)
            self.model_cache['price_predictor'] = {
                'model': model, 'scaler': scaler, 'last_updated': datetime.utcnow(),
                'training_points': len(df_train), 'score': score,
                'history': self.model_cache.get('history', []) + [{'time': datetime.utcnow(), 'score': score}]
            }
            print(f"AdaptiveLearningAgent: Price prediction model updated. New R^2 score: {score:.4f}")
            self.feedback_buffer.clear()

    def _calculate_confidence(self) -> float:
        """Calculate a confidence score based on the state of the cached model."""
        if 'price_predictor' in self.model_cache:
            score = self.model_cache['price_predictor'].get('score', 0.5)
            last_updated = self.model_cache['price_predictor'].get('last_updated', datetime(2000, 1, 1))
            days_since_update = (datetime.utcnow() - last_updated).days
            time_decay_factor = max(0, 1 - (days_since_update / 30.0))
            return score * time_decay_factor
        return 0.5

    def add_feedback(self, feedback_data: Dict[str, Any]):
        """Adds real-world outcome data to the learning buffer."""
        self.feedback_buffer.append(feedback_data)

    def communicate_with_agent(self, target_agent: str, message: Dict[str, Any]) -> bool:
        print(f"AdaptiveLearningAgent -> {target_agent}: Model status updated.")
        return True

