"""
Mock Agent Service — returns rich demo data for each agent.
Used when MOCK_MODE=true (default) or Oracle credentials are unavailable.
"""

import asyncio
import random
from Backend.models.chat import ChatResponse, KPI, ChartData, ChartDataset


# ─── Mock response data per agent ──────────────────────────────────────────────

MOCK_DATA = {
    "ar": {
        "narrative": "Found 3 unpaid invoices for Siemens totalling **$48,200**. Two invoices are overdue by more than 14 days. Credit utilisation is at 64% of the approved limit.",
        "kpis": [
            KPI(label="Total Outstanding", value="$48,200", trend="+12%", up=False),
            KPI(label="Overdue Amount", value="$31,000", trend="14+ days", up=False),
            KPI(label="Credit Limit", value="$75,000", trend="64% used", up=True),
            KPI(label="Open Invoices", value="3", trend="This month", up=None),
        ],
        "columns": ["Invoice No", "Amount", "Due Date", "Days Overdue", "Status"],
        "rows": [
            ["INV-2024-118", "$18,000", "01 Mar 2024", "47 days", "Overdue"],
            ["INV-2024-134", "$13,000", "15 Mar 2024", "33 days", "Overdue"],
            ["INV-2024-201", "$17,200", "10 Apr 2024", "—", "Pending"],
        ],
        "charts": [
            ChartData(
                chart_type="bar",
                title="Invoice Amounts",
                labels=["INV-2024-118", "INV-2024-134", "INV-2024-201"],
                datasets=[
                    ChartDataset(label="Amount ($)", data=[18000, 13000, 17200], color="#1A5C99"),
                ],
            ),
            ChartData(
                chart_type="doughnut",
                title="Credit Utilisation",
                labels=["Used", "Available"],
                datasets=[
                    ChartDataset(label="Credit", data=[48200, 26800], color="#1A5C99"),
                ],
            ),
        ],
        "follow_ups": [
            "Show credit limit history for Siemens",
            "Generate ageing report for Q1",
            "Draft dunning letter for Siemens",
        ],
    },
    "ppm": {
        "narrative": "Identified **2 of 3 active projects** below the 20% margin threshold this quarter. Project Alpha requires immediate attention with only 11% actual margin against 22% planned.",
        "kpis": [
            KPI(label="At-Risk Projects", value="2 / 3", trend="This quarter", up=False),
            KPI(label="Portfolio Margin", value="14.2%", trend="vs 20% target", up=False),
            KPI(label="Revenue Variance", value="-$218K", trend="vs forecast", up=False),
            KPI(label="Projects on Track", value="1", trend="Project Delta", up=True),
        ],
        "columns": ["Project", "Planned Margin", "Actual Margin", "Variance", "Status"],
        "rows": [
            ["Project Alpha", "22%", "11%", "-$142K", "At Risk"],
            ["Project Delta", "18%", "16%", "-$18K", "On Track"],
            ["Project Zeta", "25%", "8%", "-$58K", "At Risk"],
        ],
        "charts": [
            ChartData(
                chart_type="bar",
                title="Planned vs Actual Margin",
                labels=["Alpha", "Delta", "Zeta"],
                datasets=[
                    ChartDataset(label="Planned %", data=[22, 18, 25], color="#276749"),
                    ChartDataset(label="Actual %", data=[11, 16, 8], color="#9E2B1C"),
                ],
            ),
        ],
        "follow_ups": [
            "Show revenue forecast for Project Alpha",
            "Drill into Project Zeta cost breakdown",
            "Compare Q1 vs Q2 margins",
        ],
    },
    "finance": {
        "narrative": "Month-end close is delayed by **2 days** due to 3 pending journal approvals. The FX Revaluation entry is the most critical blocker — it was due yesterday.",
        "kpis": [
            KPI(label="Journals Pending", value="3", trend="Blocking close", up=False),
            KPI(label="Close Delay", value="2 days", trend="Target: Apr 20", up=False),
            KPI(label="Completed Steps", value="18 / 24", trend="75% done", up=True),
            KPI(label="Critical Blockers", value="1", trend="FX Revaluation", up=False),
        ],
        "columns": ["Blocker", "Owner", "Due Date", "Priority", "Status"],
        "rows": [
            ["FX Revaluation JE", "Treasury Team", "17 Apr 2024", "Critical", "Overdue"],
            ["Accruals Review", "Controller", "18 Apr 2024", "High", "Pending"],
            ["Prepaid Amortisation", "Finance Ops", "18 Apr 2024", "Medium", "Pending"],
        ],
        "charts": [
            ChartData(
                chart_type="doughnut",
                title="Close Progress",
                labels=["Completed", "Remaining"],
                datasets=[
                    ChartDataset(label="Steps", data=[18, 6], color="#276749"),
                ],
            ),
        ],
        "follow_ups": [
            "Escalate FX Revaluation to Treasury",
            "Show full close checklist",
            "Who owns the accruals review?",
        ],
    },
    "procurement": {
        "narrative": "Found **4 open purchase orders** above $50,000 totalling $342,500. Two are pending approval — PO-2024-0891 (Dell, $120K) has been waiting 5 business days.",
        "kpis": [
            KPI(label="Open POs > $50K", value="4", trend="This period", up=None),
            KPI(label="Total Value", value="$342,500", trend="Committed spend", up=None),
            KPI(label="Pending Approval", value="2", trend="$215,000 held", up=False),
            KPI(label="Avg Processing", value="4.2 days", trend="vs 3 day SLA", up=False),
        ],
        "columns": ["PO Number", "Vendor", "Amount", "Raised By", "Status"],
        "rows": [
            ["PO-2024-0891", "Dell Technologies", "$120,000", "IT Dept", "Pending Approval"],
            ["PO-2024-0902", "Accenture LLP", "$95,000", "PMO", "Approved"],
            ["PO-2024-0915", "SAP SE", "$75,500", "Finance", "Pending Approval"],
            ["PO-2024-0920", "Infosys Ltd", "$52,000", "Delivery", "Approved"],
        ],
        "charts": [
            ChartData(
                chart_type="bar",
                title="PO Amounts by Vendor",
                labels=["Dell", "Accenture", "SAP", "Infosys"],
                datasets=[
                    ChartDataset(label="Amount ($)", data=[120000, 95000, 75500, 52000], color="#553C9A"),
                ],
            ),
            ChartData(
                chart_type="pie",
                title="PO Status Distribution",
                labels=["Pending Approval", "Approved"],
                datasets=[
                    ChartDataset(label="Count", data=[2, 2], color="#553C9A"),
                ],
            ),
        ],
        "follow_ups": [
            "Approve PO-2024-0891",
            "Show vendor spend YTD",
            "List POs expiring this month",
        ],
    },
    "hcm": {
        "narrative": "Your team has **5 pending leave requests** this week. 2 employees have overlapping leave on April 23rd — you may want to stagger approvals to maintain coverage.",
        "kpis": [
            KPI(label="Pending Requests", value="5", trend="Needs action", up=False),
            KPI(label="Approved This Month", value="8", trend="Total", up=True),
            KPI(label="Team Available", value="19 / 24", trend="Apr 23rd", up=None),
            KPI(label="Overlap Risk", value="Apr 23", trend="2 clashing", up=False),
        ],
        "columns": ["Employee", "Leave Type", "From", "To", "Status"],
        "rows": [
            ["Arun Mehta", "Annual Leave", "22 Apr 2024", "25 Apr 2024", "Pending"],
            ["Priya Nair", "Sick Leave", "18 Apr 2024", "19 Apr 2024", "Pending"],
            ["Ravi Kumar", "Casual Leave", "23 Apr 2024", "23 Apr 2024", "Pending"],
            ["Sneha Rao", "Annual Leave", "23 Apr 2024", "26 Apr 2024", "Pending"],
            ["Kiran Shah", "Paternity Leave", "29 Apr 2024", "10 May 2024", "Pending"],
        ],
        "charts": [
            ChartData(
                chart_type="bar",
                title="Leave Requests by Type",
                labels=["Annual", "Sick", "Casual", "Paternity"],
                datasets=[
                    ChartDataset(label="Count", data=[2, 1, 1, 1], color="#9E2B1C"),
                ],
            ),
        ],
        "follow_ups": [
            "Approve all non-conflicting requests",
            "Show payroll calendar for May",
            "Team availability report this quarter",
        ],
    },
}


async def get_mock_response(agent_id: str, intent: str, confidence: float, query: str) -> ChatResponse:
    """Return a mock response for the given agent. Simulates API latency."""
    # Simulate processing time
    await asyncio.sleep(0.5 + random.random() * 0.5)

    data = MOCK_DATA.get(agent_id)
    if not data:
        return ChatResponse(
            success=False,
            fallback=True,
            message=f"No mock data configured for agent '{agent_id}'.",
        )

    from services.agent_registry import get_agent
    agent = get_agent(agent_id)

    return ChatResponse(
        success=True,
        intent=intent,
        confidence=confidence,
        agent_id=agent_id,
        agent_name=agent.name if agent else agent_id,
        narrative=data["narrative"],
        kpis=data["kpis"],
        columns=data["columns"],
        rows=data["rows"],
        charts=data.get("charts"),
        follow_ups=data["follow_ups"],
    )
