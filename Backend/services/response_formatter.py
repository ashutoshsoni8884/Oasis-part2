# services/response_formatter.py

"""
Response Formatter — transforms raw Oracle agent output into
the structured ChatResponse schema the frontend expects.
"""

import logging
import re
from models.chat import ChatResponse, KPI, ChartData, ChartDataset
from services.agent_registry import get_agent

logger = logging.getLogger(__name__)


def format_oracle_response(
    oracle_output: str,
    intent: str,
    confidence: float,
    agent_id: str,
) -> ChatResponse:
    """
    Parse Oracle agent free-text output into a structured ChatResponse.
    """
    agent = get_agent(agent_id)

    # Safe string conversion and stripping
    if isinstance(oracle_output, dict):
        oracle_output_str = ""
        oracle_output_stripped = ""
    else:
        oracle_output_str = str(oracle_output)
        oracle_output_stripped = oracle_output_str.strip()

    # Empty check
    if not oracle_output and not isinstance(oracle_output, dict):
        return ChatResponse(
            success=False,
            fallback=True,
            message="Oracle agent returned an empty response.",
        )

    # Initialize fields
    narrative = None
    html = None
    kpis = None
    columns = None
    rows = None
    charts = None

    # Check if the response contains HTML table
    if isinstance(oracle_output, str):
        # Check for HTML table
        if '<table' in oracle_output_stripped.lower() and '<tr>' in oracle_output_stripped.lower():
            logger.info('Oracle agent returned HTML table response')
            # Extract the HTML table and clean it
            html = _extract_and_clean_html_table(oracle_output_stripped)
            # Also extract plain text narrative
            narrative = _extract_text_before_table(oracle_output_stripped)
            
        # Check for pipe-style table (Subscription summary issue)
        elif '|' in oracle_output_stripped and ('Service Type' in oracle_output_stripped or 'Invoice Number' in oracle_output_stripped):
            logger.info('Oracle agent returned pipe-style table response - converting to HTML')
            html, columns, rows = _convert_pipe_table_to_html(oracle_output_stripped)
            narrative = _extract_text_before_table(oracle_output_stripped)
            
        # Check if it's plain text or JSON
        else:
            try:
                if isinstance(oracle_output, dict):
                    parsed = oracle_output
                else:
                    import json
                    parsed = json.loads(oracle_output_stripped)
                    
                if isinstance(parsed, dict):
                    narrative = parsed.get("message") or parsed.get("text") or parsed.get("output") or parsed.get("narrative")
                    if not narrative and not any([parsed.get("kpis"), parsed.get("columns"), parsed.get("rows")]):
                        narrative = oracle_output_stripped
                    
                    kpis = parsed.get("kpis")
                    columns = parsed.get("columns")
                    rows = parsed.get("rows")
                    charts = parsed.get("charts")
                else:
                    narrative = str(parsed)
            except Exception:
                narrative = oracle_output_stripped

    # Generate follow-ups
    follow_ups = _generate_follow_ups(intent, agent_id)

    return ChatResponse(
        success=True,
        intent=intent,
        confidence=confidence,
        agent_id=agent_id,
        agent_name=agent.name if agent else agent_id,
        narrative=narrative,
        html=html,
        kpis=kpis,
        columns=columns,
        rows=rows,
        charts=charts,
        follow_ups=follow_ups,
    )


def _extract_and_clean_html_table(html_text: str) -> str:
    """Extract and clean HTML table from response."""
    import re
    
    # Find the table
    table_match = re.search(r'<table.*?>(.*?)</table>', html_text, re.DOTALL | re.IGNORECASE)
    if table_match:
        table_html = table_match.group(0)
        # Clean up the table - add proper styling
        table_html = re.sub(r'<table', '<table style="border-collapse:collapse;width:100%;margin:12px 0;"', table_html)
        table_html = re.sub(r'<th', '<th style="text-align:left;padding:10px 12px;border:1px solid #e2e8f0;background:#f5f5f5;font-weight:600;"', table_html)
        table_html = re.sub(r'<td', '<td style="text-align:left;padding:8px 12px;border:1px solid #e2e8f0;"', table_html)
        return table_html
    return html_text


def _convert_pipe_table_to_html(text: str) -> tuple[str, list[str], list[list[str]]]:
    """Convert pipe-style table (like | col1 | col2 |) to HTML table."""
    import re
    
    lines = text.split('\n')
    html_lines = []
    columns = []
    rows = []
    
    in_table = False
    header_found = False
    
    for line in lines:
        line = line.strip()
        if '|' in line and len(line) > 3:
            # This is a table row
            cells = [cell.strip() for cell in line.split('|')]
            cells = [c for c in cells if c]  # Remove empty cells
            
            if cells:
                if not header_found and any(word in line for word in ['Service Type', 'Invoice Number', 'Customer Number']):
                    # This is the header row
                    columns = cells
                    html_lines.append('<thead>')
                    html_lines.append('<tr>')
                    for cell in cells:
                        html_lines.append(f'<th style="text-align:left;padding:10px 12px;border:1px solid #e2e8f0;background:#f5f5f5;font-weight:600;">{cell}</th>')
                    html_lines.append('</tr>')
                    html_lines.append('</thead>')
                    html_lines.append('<tbody>')
                    header_found = True
                    in_table = True
                elif header_found:
                    # This is a data row
                    rows.append(cells)
                    html_lines.append('<tr>')
                    for cell in cells:
                        html_lines.append(f'<td style="text-align:left;padding:8px 12px;border:1px solid #e2e8f0;">{cell}</td>')
                    html_lines.append('</tr>')
    
    if in_table:
        html_lines.append('</tbody>')
        table_html = '<table style="border-collapse:collapse;width:100%;margin:12px 0;">\n' + '\n'.join(html_lines) + '\n</table>'
        return table_html, columns, rows
    
    return text, None, None


def _extract_text_before_table(text: str) -> str:
    """Extract text that appears before any table in the response."""
    import re
    
    # Find where the table starts
    table_match = re.search(r'(<table|Subscription Summary|\n\s*\|)', text)
    if table_match:
        before_text = text[:table_match.start()].strip()
        # Clean up the text
        before_text = re.sub(r'\s+', ' ', before_text)
        return before_text
    
    # If no table found, return first 200 chars as summary
    return text[:200] if len(text) > 200 else text


def _generate_follow_ups(intent: str, agent_id: str) -> list[str]:
    """Generate contextual follow-up suggestions."""
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

    # For subscription and credit agents
    if "SUBSCRIPTION" in str(agent_id).upper():
        return [
            "Show upcoming renewals",
            "View product details",
            "Check coverage expirations",
        ]
    elif "CREDIT" in str(agent_id).upper() or "AR" in str(agent_id).upper():
        return [
            "Show payment history",
            "View credit limit details",
            "List open invoices",
        ]
    elif "COLLECTOR" in str(agent_id).upper():
        return [
            "Create promise to pay",
            "Create dispute",
            "Send invoice copy",
        ]

    return follow_up_map.get(intent, [
        "Tell me more",
        "Show related data",
        "What actions can I take?",
    ])