from agents.prompts import DIAGNOSTICIAN
from agents.runner import MODEL_SONNET, AgentConfig

CONFIG = AgentConfig(
    name="Diagnostician",
    system_prompt=DIAGNOSTICIAN,
    tool_names=[
        "get_route_demand",
        "get_market_share",
        "get_fleet_composition",
        "get_cancellation_rate",
        "compare_periods",
    ],
    model=MODEL_SONNET,
)
