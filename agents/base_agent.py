# agriflow-nexus/agents/base_agent.py
# BaseAgent class for agent-based systems
# This class defines the basic structure and methods that all agents should implement.
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import uuid
from config.config import Config
DATASET = Config.BIGQUERY_DATASET     # everywhere

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.created_at = datetime.utcnow()
        self.message_queue: list[Dict[str, Any]] = []
        self.status = "initialised"

    # ---------- to be implemented ----------
    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    @abstractmethod
    def communicate_with_agent(self, target_agent: str,
                               message: Dict[str, Any]) -> bool: ...

    # ---------- common helpers ----------
    def receive_message(self, msg: Dict[str, Any]) -> bool:
        msg["received_at"] = datetime.utcnow()
        msg["id"] = str(uuid.uuid4())
        self.message_queue.append(msg)
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "queue_len": len(self.message_queue),
            "created_at": self.created_at.isoformat()
        }
