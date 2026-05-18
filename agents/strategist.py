from agents.prompts import STRATEGIST
from agents.runner import MODEL_OPUS, AgentConfig

CONFIG = AgentConfig(
    name="Strategist",
    system_prompt=STRATEGIST,
    tool_names=["get_network_state", "get_market_share", "get_route_demand"],
    model=MODEL_OPUS,
)
