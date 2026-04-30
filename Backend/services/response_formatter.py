"""
Response Formatter — transforms raw Oracle agent output into
the structured ChatResponse schema the frontend expects.
"""

import logging
import re
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

    # Safe string conversion and stripping
    if isinstance(oracle_output, dict):
        oracle_output_str = "" # We will handle dict below
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

    # Check if the response is HTML (only if it's a string)
    if isinstance(oracle_output, str) and oracle_output_stripped.startswith('<') and ('<' in oracle_output_stripped or '>' in oracle_output_stripped):
        # Parse HTML response to extract narrative and structured data
        narrative, columns, rows = _parse_html_response(oracle_output_stripped)
        logger.info('Oracle agent returned HTML response (parsed into structured data)')
        html = None # We prefer structured data over raw HTML
    else:
        # Plain text or JSON response
        try:
            if isinstance(oracle_output, dict):
                parsed = oracle_output
            else:
                import json
                parsed = json.loads(oracle_output_stripped)
                
            if isinstance(parsed, dict):
                # Extract narrative
                narrative = parsed.get("message") or parsed.get("text") or parsed.get("output") or parsed.get("narrative")
                if not narrative and not any([parsed.get("kpis"), parsed.get("columns"), parsed.get("rows")]):
                    # Fallback to stringified version if nothing useful found
                    narrative = oracle_output_stripped
                
                # Extract structured data
                kpis = parsed.get("kpis")
                columns = parsed.get("columns")
                rows = parsed.get("rows")
                charts = parsed.get("charts")
            else:
                narrative = str(parsed)
        except Exception:
            narrative = oracle_output_stripped
        html = None

    # Generate contextual follow-ups based on intent
    follow_ups = _generate_follow_ups(intent, agent_id)

    # Heuristic: Detect and parse plain-text tables if columns/rows are missing
    if narrative and not columns and not rows:
        detected_cols, detected_rows = _detect_and_parse_table(narrative)
        if detected_cols and detected_rows:
            columns = detected_cols
            rows = detected_rows
            # Clean up narrative to remove the table if it's redundant
            lines = narrative.split('\n')
            # Find where the table starts (roughly)
            table_start_idx = -1
            table_headers_keywords = ["Invoice", "Amount", "Balance", "Date", "Status"]
            for i, line in enumerate(lines):
                if sum(1 for k in table_headers_keywords if k.lower() in line.lower()) >= 2:
                    table_start_idx = i
                    break
            
            if table_start_idx != -1:
                # Keep lines before the table
                narrative = '\n'.join(lines[:table_start_idx]).strip()

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


def _parse_html_response(html_text: str) -> tuple[str, list[str], list[list[str]]]:
    """Extract narrative and structured table data from an HTML response."""
    # Extract table if present
    table_match = re.search(r'<table.*?>.*?</table>', html_text, re.DOTALL | re.IGNORECASE)
    
    narrative = html_text
    columns = None
    rows = None
    
    if table_match:
        table_html = table_match.group(0)
        # Narrative is what remains when table is removed
        narrative_raw = html_text.replace(table_html, "")
        
        # Clean narrative (strip tags)
        narrative = re.sub(r'<.*?>', '\n', narrative_raw)
        narrative = '\n'.join([l.strip() for l in narrative.split('\n') if l.strip()])
        
        # Extract headers from <th>
        columns = re.findall(r'<th.*?>\s*(.*?)\s*</th>', table_html, re.DOTALL | re.IGNORECASE)
        if columns:
            # Strip any remaining HTML tags from column names
            columns = [re.sub(r'<.*?>', '', c).strip() for c in columns]
        
        # Extract rows from <tr>
        tr_matches = re.findall(r'<tr.*?>\s*(.*?)\s*</tr>', table_html, re.DOTALL | re.IGNORECASE)
        rows = []
        for i, tr_content in enumerate(tr_matches):
            # Skip rows that only contain headers (we already got columns)
            if i == 0 and '<th' in tr_content.lower():
                continue
            
            # Extract cells from <td>
            cells = re.findall(r'<td.*?>\s*(.*?)\s*</td>', tr_content, re.DOTALL | re.IGNORECASE)
            # If no <td>, try <th> (sometimes headers are in <td>)
            if not cells and not columns:
                cells = re.findall(r'<th.*?>\s*(.*?)\s*</th>', tr_content, re.DOTALL | re.IGNORECASE)
                if cells:
                    columns = [re.sub(r'<.*?>', '', c).strip() for c in cells]
                    continue
                    
            if cells:
                # Strip internal tags from cells (like <strong> or <span>)
                clean_cells = [re.sub(r'<.*?>', '', c).strip() for c in cells]
                rows.append(clean_cells)
    else:
        # No table, just clean the HTML tags from narrative
        narrative = re.sub(r'<.*?>', '\n', html_text)
        narrative = '\n'.join([l.strip() for l in narrative.split('\n') if l.strip()])

    return narrative, columns, rows



def _detect_and_parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    """
    Attempt to detect a table in plain text and parse it into columns and rows.
    Handles 'congested' tables where columns touch each other.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) < 2:
        return None, None

    # Common table headers for AR/Finance
    table_headers = [
        "Invoice", "Amount", "Balance", "Date", "Status", "Number", "Customer", 
        "Due", "Project", "Margin", "Variance", "PO", "Vendor", "Employee",
        "Entered", "Balance", "Account"
    ]

    header_line_idx = -1
    for i, line in enumerate(lines):
        # Look for lines that contain multiple header keywords
        matches = sum(1 for h in table_headers if h.lower() in line.lower())
        if matches >= 2:
            header_line_idx = i
            break

    if header_line_idx == -1:
        return None, None

    header_line = lines[header_line_idx]
    
    # Try to split header line. Congested headers might look like "Invoice NumberEntered Amount (USD)"
    # Insert spaces before capital letters that follow lowercase letters or punctuation
    temp_header = re.sub(r'([a-z\)\]])([A-Z])', r'\1 \2', header_line)
    
    # Also handle specific smashed headers based on keywords
    for h in table_headers:
        temp_header = re.sub(f"({h})([A-Z0-9])", r"\1 \2", temp_header, flags=re.IGNORECASE)
    
    # Split by multiple spaces or common separators
    cols = [c.strip() for c in re.split(r'\s{2,}', temp_header) if c.strip()]
    
    # If we still have very few columns, try splitting by single spaces but be careful
    if len(cols) < 2:
        cols = [c.strip() for c in temp_header.split('  ') if c.strip()]
    if len(cols) < 2:
        # Last resort: split by single space if it looks like a header
        cols = [c.strip() for c in temp_header.split(' ') if c.strip()]

    parsed_rows = []
    # Process subsequent lines as rows
    for row_idx, line in enumerate(lines[header_line_idx + 1:]):
        # Skip total lines if they don't have enough data, but try to parse them if they do
        row_text = line
        
        # 1. Insert spaces between Amount and Date (both YYYY-MM-DD and DD/MM/YYYY)
        row_text = re.sub(r'(\d+\.\d{2})(\d{4}-\d{2}-\d{2})', r'\1 \2', row_text)
        row_text = re.sub(r'(\d+\.\d{2})(\d{2}/\d{2}/\d{2,4})', r'\1 \2', row_text)
        
        # 2. Insert spaces between Date and Status/Word
        row_text = re.sub(r'(\d{4}-\d{2}-\d{2})([A-Z][a-z]+)', r'\1 \2', row_text)
        row_text = re.sub(r'(\d{2}/\d{2}/\d{2,4})([A-Z][a-z]+)', r'\1 \2', row_text)
        
        # 3. Insert spaces between Amount and Amount (if smashed)
        row_text = re.sub(r'(\d+\.\d{2})(\d+\.\d{2})', r'\1 \2', row_text)

        # 4. Handle Invoice Number smashed with Amount
        # e.g. "13008630.00" -> "13008 630.00" (heuristic: 5+ digits followed by amount)
        row_text = re.sub(r'(\d{5,})(\d+\.\d{2})', r'\1 \2', row_text)

        # Split by multiple spaces or our newly inserted single spaces
        row_cells = [c.strip() for c in re.split(r'\s+', row_text) if c.strip()]
        
        # If we have a reasonable number of cells compared to columns
        if len(row_cells) >= len(cols) - 1:
            # Pad or trim to match col count
            if len(row_cells) < len(cols):
                row_cells += [""] * (len(cols) - len(row_cells))
            parsed_rows.append(row_cells[:len(cols)])
        elif "total" in line.lower() and len(row_cells) >= 2:
            # Handle total line specifically even if it has fewer columns
            # Map total values to Amount columns if possible
            total_row = [row_cells[0]] # "Total"
            # Try to align amounts
            if len(row_cells) == 3: # Total, Val1, Val2
                total_row += [row_cells[1], row_cells[2]]
            else:
                total_row += [row_cells[1]]
            
            # Pad to match column count
            while len(total_row) < len(cols):
                total_row.append("")
            parsed_rows.append(total_row)

    if len(parsed_rows) > 0:
        return cols, parsed_rows

    return None, None


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
