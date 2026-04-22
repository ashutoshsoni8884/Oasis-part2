"""
Response Formatter — transforms raw Oracle agent output into
the structured ChatResponse schema the frontend expects.
"""

import logging
from Backend.models.chat import ChatResponse, KPI, ChartData, ChartDataset
from Backend.services.agent_registry import get_agent

logger = logging.getLogger(__name__)


def format_oracle_response(
    oracle_output: str,
    intent: str,
    confidence: float,
    agent_id: str,
) -> ChatResponse:
    """
    Parse Oracle agent free-text output into a structured ChatResponse.

    Oracle agents typically return a narrative text response. This formatter:
    1. Uses the raw text as the narrative
    2. Attempts to extract any structured data if present
    3. Generates follow-up suggestions based on the intent
    """
    agent = get_agent(agent_id)

    if not oracle_output or not oracle_output.strip():
        return ChatResponse(
            success=False,
            fallback=True,
            message="Oracle agent returned an empty response.",
        )

    # Check if the response is HTML
    oracle_output_stripped = oracle_output.strip()
    if oracle_output_stripped.startswith('<') and ('<' in oracle_output_stripped or '>' in oracle_output_stripped):
        # Likely HTML response
        html = oracle_output_stripped
        narrative = None
        logger.info('Oracle agent returned HTML response')
    else:
        # Plain text response
        narrative = oracle_output_stripped
        html = None

    # Generate contextual follow-ups based on intent
    follow_ups = _generate_follow_ups(intent, agent_id)

    return ChatResponse(
        success=True,
        intent=intent,
        confidence=confidence,
        agent_id=agent_id,
        agent_name=agent.name if agent else agent_id,
        narrative=narrative,
        html=html,
        kpis=None,       # KPIs would need structured Oracle output or post-processing
        columns=None,
        rows=None,
        charts=None,
        follow_ups=follow_ups,
    )


def _generate_follow_ups(intent: str, agent_id: str) -> list[str]:
    """Generate contextual follow-up suggestions based on the intent."""
    follow_up_map = {
        "AR_CREDIT_QUERY": [
            "Show credit limit history",
            "Generate ageing report",
            "List all overdue invoices",
        ],
        "AR_AGING_REPORT": [
            "Drill into 90+ days bucket",
            "Compare with last quarter",
            "Show top 10 debtors",
        ],
        "PPM_MARGIN_RISK": [
            "Show detailed cost breakdown",
            "Revenue forecast for next quarter",
            "List all at-risk projects",
        ],
        "PPM_REVENUE": [
            "Compare actuals vs forecast",
            "Show revenue by project",
            "Year-to-date revenue trend",
        ],
        "FINANCE_CLOSE": [
            "Show full close checklist",
            "Escalate pending approvals",
            "Compare with last month's close time",
        ],
        "PROCUREMENT_QUERY": [
            "Show vendor spend YTD",
            "List expiring contracts",
            "Pending approval summary",
        ],
        "HCM_LEAVE": [
            "Team availability calendar",
            "Approve all pending requests",
            "Show leave balance summary",
        ],
        "HCM_PAYROLL": [
            "Show payroll calendar",
            "Salary revision pending list",
            "Headcount report",
        ],
    }

    return follow_up_map.get(intent, [
        "Tell me more",
        "Show related data",
        "What actions can I take?",
    ])
