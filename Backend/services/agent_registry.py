"""
Agent Registry — single source of truth for all available agents.
Maps agent IDs to their metadata and intent list.
"""

from models.agent import AgentConfig

AGENTS: list[AgentConfig] = [
    AgentConfig(
        id="ar",
        name="AR Credit Management",
        short_name="AR Credit",
        icon="💳",
        color="#1A5C99",
        bg="#E8F1FB",
        intents=["AR_CREDIT_QUERY", "AR_AGING_REPORT"],
        description="Accounts receivable, invoices, credit limits, ageing reports",
    ),
    AgentConfig(
        id="ppm",
        name="PPM Margin Risk",
        short_name="PPM Margin",
        icon="📊",
        color="#276749",
        bg="#E6F4EC",
        intents=["PPM_MARGIN_RISK", "PPM_REVENUE"],
        description="Project margin analysis, revenue forecasting, risk assessment",
    ),
    AgentConfig(
        id="finance",
        name="Finance Close",
        short_name="Finance",
        icon="📅",
        color="#7B4F12",
        bg="#FEF3CD",
        intents=["FINANCE_CLOSE"],
        description="Month-end close, journal approvals, period management",
    ),
    AgentConfig(
        id="procurement",
        name="Procurement",
        short_name="Procurement",
        icon="🛒",
        color="#553C9A",
        bg="#EDE9F8",
        intents=["PROCUREMENT_QUERY"],
        description="Purchase orders, vendor management, approvals",
    ),
    AgentConfig(
        id="hcm",
        name="HCM / Payroll",
        short_name="HCM",
        icon="👥",
        color="#9E2B1C",
        bg="#FDECEA",
        intents=["HCM_LEAVE", "HCM_PAYROLL"],
        description="Leave requests, payroll, employee data, team management",
    ),
]

# Lookup helpers
AGENT_MAP: dict[str, AgentConfig] = {a.id: a for a in AGENTS}
INTENT_TO_AGENT: dict[str, str] = {}
for agent in AGENTS:
    for intent in agent.intents:
        INTENT_TO_AGENT[intent] = agent.id


def get_agent(agent_id: str) -> AgentConfig | None:
    return AGENT_MAP.get(agent_id)


def get_agent_for_intent(intent: str) -> AgentConfig | None:
    agent_id = INTENT_TO_AGENT.get(intent)
    return AGENT_MAP.get(agent_id) if agent_id else None


def get_all_agents() -> list[AgentConfig]:
    return AGENTS
