# agents/__init__.py
from dataclasses import dataclass
from typing import Any, Dict, Callable, List
from agents.base_agent import BaseAgent

@dataclass
class Message:
    payload: Dict[str, Any]
    source: str
    dest: str

class Orchestrator:
    """
    Synchronous, single-thread orchestrator that just walks message hops.
    """
    def __init__(self,
                 agents: List["BaseAgent"],
                 router: Callable[[Message], str]):
        self.router = router
        # map id -> instance
        self.agents = {a.agent_id: a for a in agents}

    def start(self, first_msg: Message):
        msg = first_msg
        while msg.dest:
            agent = self.agents.get(msg.dest)
            if agent is None:
                raise ValueError(f"No agent named {msg.dest}")
            reply = agent.process_data(msg.payload)

            # let the agent log / do side effects
            agent.communicate_with_agent(self.router(msg), reply)

            # hop to next
            msg = Message(
                payload=reply,
                source=agent.agent_id,
                dest=self.router(msg)
            )
