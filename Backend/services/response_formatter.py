"""
Response Formatter — transforms raw Oracle agent output into
the structured ChatResponse schema the frontend expects.
"""

import logging
from models.chat import ChatResponse, KPI, ChartData, ChartDataset
from services.agent_registry import get_agent

logger = logging.getLogger(__name__)


async def format_oracle_response(
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

    # Check if the response contains HTML
    if isinstance(oracle_output, str):
        import re
        # Find all HTML tags (simplified regex)
        html_tags = re.findall(r'<[a-z/][^>]*>', oracle_output_stripped, re.IGNORECASE)
        if html_tags:
            # If the entire output is HTML, just use it
            if oracle_output_stripped.startswith('<') and oracle_output_stripped.endswith('>'):
                html = oracle_output_stripped
                narrative = None
            else:
                # Embedded HTML - extract it and keep the rest as narrative
                # For now, let's just use the whole string as html if it contains tags, 
                # but the frontend prefers structured data if possible.
                # A better approach: extract specific tags like <div> or <table>
                html_matches = re.finditer(r'<(div|table|span|p|br|b|i|strong|em)[^>]*>.*?</\1>|<(br|hr|img)[^>]*>', oracle_output_stripped, re.IGNORECASE | re.DOTALL)
                extracted_html = []
                remaining_text = oracle_output_stripped
                
                for match in html_matches:
                    extracted_html.append(match.group(0))
                    # We don't remove it from text yet, just detect it
                
                if extracted_html:
                    html = "\n".join(extracted_html)
                    # Clean up narrative by removing the html tags we found
                    for h in extracted_html:
                        remaining_text = remaining_text.replace(h, "")
                    narrative = remaining_text.strip()
                else:
                    # Fallback for simple tags or non-matching pairs
                    narrative = oracle_output_stripped
                    html = None
        else:
            # Plain text or JSON response
            try:
                import json
                parsed = json.loads(oracle_output_stripped)
                if isinstance(parsed, dict):
                    # Extract narrative
                    narrative = parsed.get("message") or parsed.get("text") or parsed.get("output") or parsed.get("narrative")
                    if not narrative and not any([parsed.get("kpis"), parsed.get("columns"), parsed.get("rows")]):
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
    elif isinstance(oracle_output, dict):
        parsed = oracle_output
        narrative = parsed.get("message") or parsed.get("text") or parsed.get("output") or parsed.get("narrative")
        kpis = parsed.get("kpis")
        columns = parsed.get("columns")
        rows = parsed.get("rows")
        charts = parsed.get("charts")
    else:
        narrative = str(oracle_output)
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
            narrative = _remove_table_from_narrative(narrative, detected_cols)
        else:
            # ULTIMATE FALLBACK: Use Gemini to format the unstructured response
            logger.info("Heuristic parsing failed — attempting LLM-based formatting")
            llm_result = await _format_with_gemini(narrative, intent, agent_id)
            if llm_result:
                narrative = llm_result.get("narrative") or narrative
                columns = llm_result.get("columns")
                rows = llm_result.get("rows")
                kpis = llm_result.get("kpis") or kpis
                charts = llm_result.get("charts") or charts

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
        kpis=kpis,
        columns=columns,
        rows=rows,
        charts=charts,
        follow_ups=follow_ups,
    )


async def _format_with_gemini(text: str, intent: str, agent_id: str) -> dict | None:
    """Use Gemini to structured a messy text response into narrative, columns, and rows."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here":
        return None

    try:
        import google.generativeai as genai
        import re
        import json

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"""You are a data extraction specialist.
Convert the following messy Oracle ERP agent response into a clean, structured JSON format.

RULES:
1. Extract the main explanation into "narrative".
2. If there is a table, extract it into "columns" (list of strings) and "rows" (list of lists of strings).
3. If there are key metrics (like Total Balance, Total Amount), extract them into "kpis" (list of objects with "label", "value", "trend").
4. Return ONLY valid JSON.

Response text:
{text}

JSON Format:
{{
  "narrative": "...",
  "columns": ["Col 1", "Col 2"],
  "rows": [["Val 1", "Val 2"]],
  "kpis": [{{"label": "...", "value": "...", "trend": "up|down|neutral"}}]
}}"""

        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip()
        
        # Strip code fences
        if "```" in raw_text:
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE)

        return json.loads(raw_text)
    except Exception as e:
        logger.error(f"Gemini formatting failed: {e}")
        return None


def _remove_table_from_narrative(narrative: str, cols: list[str]) -> str:
    """
    Remove the table section from the narrative text to avoid redundancy.
    """
    lines = narrative.split('\n')
    header_idx = -1
    for i, line in enumerate(lines):
        if all(col.lower() in line.lower() for col in cols[:2]): # Check first 2 cols
            header_idx = i
            break
    
    if header_idx == -1:
        return narrative
        
    # Keep lines before the table
    new_lines = lines[:header_idx]
    
    # Skip the table lines (lines that look like table rows)
    # A simple heuristic: stop skipping when we find a line that doesn't look like a row
    # or if we reach the end.
    for i in range(header_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        # If it's a very short line or doesn't have many spaces/pipes, it might be the end of the table
        if len(line.split()) < 2 and "|" not in line:
            new_lines.extend(lines[i:])
            break
    
    return "\n".join(new_lines).strip()


def _detect_and_parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    """
    Attempt to detect a table in plain text and parse it into columns and rows.
    Handles:
    1. Pipe-separated tables (| Col 1 | Col 2 |)
    2. Tab-separated tables
    3. Fixed-width/congested plain text tables
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) < 2:
        return None, None

    # Common table headers for AR/Finance
    table_headers = [
        "Invoice Number", "Entered Amount", "Balance Amount", "Due Date", "Status",
        "Customer Account", "Service Type", "Unbilled Amount", "Invoiced Amount",
        "Invoice", "Amount", "Balance", "Date", "Status", "Number", "Customer", 
        "Due", "Project", "Margin", "Variance", "PO", "Vendor", "Employee",
        "Unbilled"
    ]

    header_line_idx = -1
    is_pipe_table = False
    
    for i, line in enumerate(lines):
        # 1. Check for pipe-separated table header
        if line.count('|') >= 2:
            keywords_found = sum(1 for h in table_headers if h.lower() in line.lower())
            next_is_separator = i + 1 < len(lines) and (lines[i+1].strip().startswith('|---') or lines[i+1].strip().startswith('| :---'))
            
            if keywords_found >= 2 or next_is_separator:
                header_line_idx = i
                is_pipe_table = True
                break
        
        # 2. Check for plain text table header
        # Check for multiple keywords
        keywords_found = sum(1 for h in table_headers if h.lower() in line.lower())
        if keywords_found >= 3: 
            header_line_idx = i
            is_pipe_table = False
            break

    if header_line_idx == -1:
        return None, None

    header_line = lines[header_line_idx]
    cols = []

    if is_pipe_table:
        cols = [c.strip() for c in header_line.split('|') if c.strip()]
    else:
        import re
        temp_header = header_line
        # Sort keywords by length descending
        sorted_headers = sorted(table_headers, key=len, reverse=True)
        
        # Protect multi-word headers by temporary replacement
        protected_headers = []
        for h in sorted_headers:
            if " " in h and h.lower() in temp_header.lower():
                # Find the actual case-sensitive match
                match = re.search(h, temp_header, re.IGNORECASE)
                if match:
                    actual_h = match.group(0)
                    placeholder = f"__H{len(protected_headers)}__"
                    temp_header = temp_header.replace(actual_h, placeholder)
                    protected_headers.append((placeholder, actual_h))
        
        # Insert spaces before known single-word headers if they are preceded by a character
        for h in sorted_headers:
            if " " not in h:
                temp_header = re.sub(f"([^\\s|])({h})", r"\1 \2", temp_header, flags=re.IGNORECASE)
        
        # Split by 2+ spaces or tabs
        cols = [c.strip() for c in re.split(r'\s{2,}|\t', temp_header) if c.strip()]
        
        # If still only 1 column, try splitting by camelCase transitions or known keyword boundaries
        if len(cols) < 2:
            cols = [c.strip() for c in re.split(r'(?<=[a-z])(?=[A-Z])', temp_header) if c.strip()]
            
        # Restore protected headers
        for placeholder, actual_h in protected_headers:
            cols = [c.replace(placeholder, actual_h) for c in cols]
            
        # Final cleanup for very short columns that might be accidental splits
        if len(cols) < 2:
            cols = [c.strip() for c in temp_header.split(' ') if c.strip()]

    parsed_rows = []
    # Process subsequent lines as rows
    for line in lines[header_line_idx + 1:]:
        # Skip markdown separator lines
        if line.strip().startswith('|---') or line.strip().startswith('| :---'):
            continue
            
        row_cells = []
        if is_pipe_table:
            if line.count('|') >= 2:
                row_cells = [c.strip() for c in line.split('|') if c.strip()]
        else:
            # Fix congested data in rows
            import re
            row_text = line
            # 1. Date fix: Insert spaces between numbers and numeric dates (e.g. 630.0005/06/2026)
            row_text = re.sub(r'(\d+\.\d{2})(\d{2}/\d{2}/\d{4})', r'\1 \2', row_text)
            # 2. Text-Date fix: Insert spaces between numbers and text dates (e.g. 630.00May 6, 2026)
            row_text = re.sub(r'(\d+\.\d{2})((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4})', r'\1 \2', row_text, flags=re.IGNORECASE)
            # 3. Status fix: Insert spaces between dates and statuses (e.g. 2026Complete)
            row_text = re.sub(r'(\d{4})([A-Z][a-z]+)', r'\1 \2', row_text)
            
            # Split by 2+ spaces or tabs
            row_cells = [c.strip() for c in re.split(r'\s{2,}|\t', row_text) if c.strip()]
            if len(row_cells) < len(cols) - 1:
                # Fallback to single space split but try to keep common multi-word patterns together
                row_cells = [c.strip() for c in row_text.split(' ') if c.strip()]
        
        # Special handling for "Total" lines
        if "total" in line.lower() and len(row_cells) >= 2:
            # Pad it to match columns
            padded_row = [""] * len(cols)
            padded_row[0] = row_cells[0] # Usually "Total"
            padded_row[-1] = row_cells[-1] # Usually the total value
            parsed_rows.append(padded_row)
            continue

        if row_cells and len(row_cells) >= len(cols) - 1:
            # Pad or trim to match col count
            if len(row_cells) < len(cols):
                row_cells += [""] * (len(cols) - len(row_cells))
            parsed_rows.append(row_cells[:len(cols)])

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
