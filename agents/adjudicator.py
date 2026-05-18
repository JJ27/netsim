from agents.prompts import ADJUDICATOR
from agents.runner import MODEL_SONNET, AgentConfig

CONFIG = AgentConfig(
    name="Adjudicator",
    system_prompt=ADJUDICATOR,
    tool_names=["simulate_scenario", "get_route_demand"],
    model=MODEL_SONNET,
)
