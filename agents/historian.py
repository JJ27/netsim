from agents.prompts import HISTORIAN
from agents.runner import MODEL_SONNET, AgentConfig

CONFIG = AgentConfig(
    name="Historian",
    system_prompt=HISTORIAN,
    tool_names=["get_network_state", "compare_periods", "get_fleet_composition"],
    model=MODEL_SONNET,
)
