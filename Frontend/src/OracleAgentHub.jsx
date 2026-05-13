import { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "./auth/AuthContext";

// ─── Design Tokens ────────────────────────────────────────────────────────────
const THEME_PRESETS = {
  light: {
    oracle: "#C74634",
    oracleDark: "#9E2B1C",
    oracleLight: "#F9EAE7",
    navy: "#1A2B4A",
    navyMid: "#243860",
    navyLight: "#EEF2F8",
    slate: "#4A5568",
    muted: "#718096",
    border: "#E2E8F0",
    borderDark: "#CBD5E0",
    bg: "#F7F9FC",
    white: "#FFFFFF",
    success: "#276749",
    successBg: "#E6F4EC",
    warning: "#7B4F12",
    warningBg: "#FEF3CD",
    danger: "#9E2B1C",
    dangerBg: "#FDECEA",
    info: "#1A5C99",
    infoBg: "#E8F1FB",
  },
  red: {
    oracle: "#B8322A",
    oracleDark: "#8C201A",
    oracleLight: "#FCE8E6",
    navy: "#6B1D1B",
    navyMid: "#7E2A27",
    navyLight: "#F9E9E8",
    slate: "#5A4545",
    muted: "#7D6666",
    border: "#E9D2D2",
    borderDark: "#DDBABA",
    bg: "#FFF6F6",
    white: "#FFFFFF",
    success: "#2F855A",
    successBg: "#E6F7EE",
    warning: "#9C4221",
    warningBg: "#FFF1E6",
    danger: "#B8322A",
    dangerBg: "#FDE8E8",
    info: "#9B2C2C",
    infoBg: "#FDECEC",
  },
  dark: {
    oracle: "#E05B4A",
    oracleDark: "#C74634",
    oracleLight: "#43201C",
    navy: "#0F172A",
    navyMid: "#1E293B",
    navyLight: "#1F2A3B",
    slate: "#CBD5E1",
    muted: "#94A3B8",
    border: "#334155",
    borderDark: "#475569",
    bg: "#0B1220",
    white: "#111827",
    success: "#34D399",
    successBg: "#113327",
    warning: "#FBBF24",
    warningBg: "#3A2D10",
    danger: "#F87171",
    dangerBg: "#3F1D1D",
    info: "#60A5FA",
    infoBg: "#1B2A42",
  },
  forest: {
    oracle: "#2F855A",
    oracleDark: "#276749",
    oracleLight: "#E6F4EC",
    navy: "#1B4332",
    navyMid: "#2D6A4F",
    navyLight: "#EAF4EF",
    slate: "#3D5A4B",
    muted: "#5F7A6B",
    border: "#D6E6DC",
    borderDark: "#BDD5C6",
    bg: "#F4FAF6",
    white: "#FFFFFF",
    success: "#2F855A",
    successBg: "#E6F4EC",
    warning: "#9C6B1F",
    warningBg: "#FFF4DA",
    danger: "#B8322A",
    dangerBg: "#FDECEA",
    info: "#2C7A7B",
    infoBg: "#E6F7F8",
  },
};

const THEME_OPTIONS = [
  { value: "light", label: "Light" },
  { value: "red", label: "Red" },
  { value: "dark", label: "Dark" },
  { value: "forest", label: "Forest" },
];

const T = {
  oracle: "var(--theme-oracle)",
  oracleDark: "var(--theme-oracle-dark)",
  oracleLight: "var(--theme-oracle-light)",
  navy: "var(--theme-navy)",
  navyMid: "var(--theme-navy-mid)",
  navyLight: "var(--theme-navy-light)",
  slate: "var(--theme-slate)",
  muted: "var(--theme-muted)",
  border: "var(--theme-border)",
  borderDark: "var(--theme-border-dark)",
  bg: "var(--theme-bg)",
  white: "var(--theme-white)",
  success: "var(--theme-success)",
  successBg: "var(--theme-success-bg)",
  warning: "var(--theme-warning)",
  warningBg: "var(--theme-warning-bg)",
  danger: "var(--theme-danger)",
  dangerBg: "var(--theme-danger-bg)",
  info: "var(--theme-info)",
  infoBg: "var(--theme-info-bg)",
  shadow: "0 1px 3px rgba(26,43,74,0.08), 0 4px 12px rgba(26,43,74,0.06)",
  shadowMd: "0 4px 16px rgba(26,43,74,0.10), 0 1px 4px rgba(26,43,74,0.06)",
  radius: "6px",
  radiusMd: "10px",
  radiusLg: "14px",
};

// ─── Agent Configuration ──────────────────────────────────────────────────────
const AGENTS = [
  {
    id: "ar",
    name: "AR Credit Management",
    shortName: "AR Credit",
    icon: "💳",
    color: "#1A5C99",
    bg: "#E8F1FB",
    intents: ["AR_CREDIT_QUERY", "AR_AGING_REPORT"],
    description: "Accounts receivable, invoices, credit limits, ageing reports",
    endpoint: "/api/agents/ar-credit",
  },
  {
    id: "ppm",
    name: "PPM Margin Risk",
    shortName: "PPM Margin",
    icon: "📊",
    color: "#276749",
    bg: "#E6F4EC",
    intents: ["PPM_MARGIN_RISK", "PPM_REVENUE"],
    description: "Project margin analysis, revenue forecasting, risk assessment",
    endpoint: "/api/agents/ppm-margin",
  },
  {
    id: "finance",
    name: "Finance Close",
    shortName: "Finance",
    icon: "📅",
    color: "#7B4F12",
    bg: "#FEF3CD",
    intents: ["FINANCE_CLOSE"],
    description: "Month-end close, journal approvals, period management",
    endpoint: "/api/agents/finance-close",
  },
  {
    id: "procurement",
    name: "Procurement",
    shortName: "Procurement",
    icon: "🛒",
    color: "#553C9A",
    bg: "#EDE9F8",
    intents: ["PROCUREMENT_QUERY"],
    description: "Purchase orders, vendor management, approvals",
    endpoint: "/api/agents/procurement",
  },
  {
    id: "hcm",
    name: "HCM / Payroll",
    shortName: "HCM",
    icon: "👥",
    color: "#9E2B1C",
    bg: "#FDECEA",
    intents: ["HCM_LEAVE", "HCM_PAYROLL"],
    description: "Leave requests, payroll, employee data, team management",
    endpoint: "/api/agents/hcm",
  },
];

const AGENT_QUICK_PROMPTS = {
  ar: [
    "Show unpaid invoices for Siemens",
    "Generate ageing report for Q1 receivables",
    "Show credit limit history for Siemens",
  ],
  ppm: [
    "Which projects are at margin risk this quarter?",
    "Show revenue forecast for Project Alpha",
    "Compare Q1 vs Q2 margins",
  ],
  finance: [
    "Why is the month-end close delayed?",
    "Show full close checklist",
    "Who owns the accruals review?",
  ],
  procurement: [
    "List open purchase orders above $50,000",
    "Show vendor spend YTD",
    "List POs expiring this month",
  ],
  hcm: [
    "Pending leave requests for my team",
    "Show payroll calendar for May",
    "Team availability report this quarter",
  ],
};

// ─── Mock Router API ──────────────────────────────────────────────────────────
const INTENT_PATTERNS = [
  { pattern: /invoice|unpaid|receivable|ar|credit|ageing|aging|siemens|dunning|overdue|outstanding/i, intent: "AR_CREDIT_QUERY", agent: "ar", conf: 0.96 },
  { pattern: /margin|project.risk|ppm|at risk|margin risk/i, intent: "PPM_MARGIN_RISK", agent: "ppm", conf: 0.94 },
  { pattern: /revenue|forecast|actuals|ppm revenue/i, intent: "PPM_REVENUE", agent: "ppm", conf: 0.91 },
  { pattern: /close|month.end|period|delayed|journal|finance close/i, intent: "FINANCE_CLOSE", agent: "finance", conf: 0.93 },
  { pattern: /purchase.order|po |procurement|vendor|supplier|open order/i, intent: "PROCUREMENT_QUERY", agent: "procurement", conf: 0.95 },
  { pattern: /leave|payroll|hcm|employee|team|headcount|salary|attendance/i, intent: "HCM_LEAVE", agent: "hcm", conf: 0.90 },
  { pattern: /aging report|ageing report|q[0-9]|quarter.*receiv/i, intent: "AR_AGING_REPORT", agent: "ar", conf: 0.88 },
];

const MOCK_RESPONSES = {
  ar: {
    narrative: "Found 3 unpaid invoices for Siemens totalling **$48,200**. Two invoices are overdue by more than 14 days. Credit utilisation is at 64% of the approved limit.",
    kpis: [
      { label: "Total Outstanding", value: "$48,200", trend: "+12%", up: false },
      { label: "Overdue Amount", value: "$31,000", trend: "14+ days", up: false },
      { label: "Credit Limit", value: "$75,000", trend: "64% used", up: true },
      { label: "Open Invoices", value: "3", trend: "This month", up: null },
    ],
    columns: ["Invoice No", "Amount", "Due Date", "Days Overdue", "Status"],
    rows: [
      ["INV-2024-118", "$18,000", "01 Mar 2024", "47 days", "Overdue"],
      ["INV-2024-134", "$13,000", "15 Mar 2024", "33 days", "Overdue"],
      ["INV-2024-201", "$17,200", "10 Apr 2024", "—", "Pending"],
    ],
    followUps: ["Show credit limit history for Siemens", "Generate ageing report for Q1", "Draft dunning letter for Siemens"],
  },
  ppm: {
    narrative: "Identified **2 of 3 active projects** below the 20% margin threshold this quarter. Project Alpha requires immediate attention with only 11% actual margin against 22% planned.",
    kpis: [
      { label: "At-Risk Projects", value: "2 / 3", trend: "This quarter", up: false },
      { label: "Portfolio Margin", value: "14.2%", trend: "vs 20% target", up: false },
      { label: "Revenue Variance", value: "-$218K", trend: "vs forecast", up: false },
      { label: "Projects on Track", value: "1", trend: "Project Delta", up: true },
    ],
    columns: ["Project", "Planned Margin", "Actual Margin", "Variance", "Status"],
    rows: [
      ["Project Alpha", "22%", "11%", "-$142K", "At Risk"],
      ["Project Delta", "18%", "16%", "-$18K", "On Track"],
      ["Project Zeta", "25%", "8%", "-$58K", "At Risk"],
    ],
    followUps: ["Show revenue forecast for Project Alpha", "Drill into Project Zeta cost breakdown", "Compare Q1 vs Q2 margins"],
  },
  finance: {
    narrative: "Month-end close is delayed by **2 days** due to 3 pending journal approvals. The FX Revaluation entry is the most critical blocker — it was due yesterday.",
    kpis: [
      { label: "Journals Pending", value: "3", trend: "Blocking close", up: false },
      { label: "Close Delay", value: "2 days", trend: "Target: Apr 20", up: false },
      { label: "Completed Steps", value: "18 / 24", trend: "75% done", up: true },
      { label: "Critical Blockers", value: "1", trend: "FX Revaluation", up: false },
    ],
    columns: ["Blocker", "Owner", "Due Date", "Priority", "Status"],
    rows: [
      ["FX Revaluation JE", "Treasury Team", "17 Apr 2024", "Critical", "Overdue"],
      ["Accruals Review", "Controller", "18 Apr 2024", "High", "Pending"],
      ["Prepaid Amortisation", "Finance Ops", "18 Apr 2024", "Medium", "Pending"],
    ],
    followUps: ["Escalate FX Revaluation to Treasury", "Show full close checklist", "Who owns the accruals review?"],
  },
  procurement: {
    narrative: "Found **4 open purchase orders** above $50,000 totalling $342,500. Two are pending approval — PO-2024-0891 (Dell, $120K) has been waiting 5 business days.",
    kpis: [
      { label: "Open POs > $50K", value: "4", trend: "This period", up: null },
      { label: "Total Value", value: "$342,500", trend: "Committed spend", up: null },
      { label: "Pending Approval", value: "2", trend: "$215,000 held", up: false },
      { label: "Avg Processing", value: "4.2 days", trend: "vs 3 day SLA", up: false },
    ],
    columns: ["PO Number", "Vendor", "Amount", "Raised By", "Status"],
    rows: [
      ["PO-2024-0891", "Dell Technologies", "$120,000", "IT Dept", "Pending Approval"],
      ["PO-2024-0902", "Accenture LLP", "$95,000", "PMO", "Approved"],
      ["PO-2024-0915", "SAP SE", "$75,500", "Finance", "Pending Approval"],
      ["PO-2024-0920", "Infosys Ltd", "$52,000", "Delivery", "Approved"],
    ],
    followUps: ["Approve PO-2024-0891", "Show vendor spend YTD", "List POs expiring this month"],
  },
  hcm: {
    narrative: "Your team has **5 pending leave requests** this week. 2 employees have overlapping leave on April 23rd — you may want to stagger approvals to maintain coverage.",
    kpis: [
      { label: "Pending Requests", value: "5", trend: "Needs action", up: false },
      { label: "Approved This Month", value: "8", trend: "Total", up: true },
      { label: "Team Available", value: "19 / 24", trend: "Apr 23rd", up: null },
      { label: "Overlap Risk", value: "Apr 23", trend: "2 clashing", up: false },
    ],
    columns: ["Employee", "Leave Type", "From", "To", "Status"],
    rows: [
      ["Arun Mehta", "Annual Leave", "22 Apr 2024", "25 Apr 2024", "Pending"],
      ["Priya Nair", "Sick Leave", "18 Apr 2024", "19 Apr 2024", "Pending"],
      ["Ravi Kumar", "Casual Leave", "23 Apr 2024", "23 Apr 2024", "Pending"],
      ["Sneha Rao", "Annual Leave", "23 Apr 2024", "26 Apr 2024", "Pending"],
      ["Kiran Shah", "Paternity Leave", "29 Apr 2024", "10 May 2024", "Pending"],
    ],
    followUps: ["Approve all non-conflicting requests", "Show payroll calendar for May", "Team availability report this quarter"],
  },
};

// ─── Backend API call ─────────────────────────────────────────────────────────
const BACKEND_URL = "http://localhost:8000";

// ── New Async API Flow ──────────────────────────────────────────────────────────
// POST /api/chat returns {job_id, status: "QUEUED"}
// GET /api/chat/{job_id} returns {job_id, status, result} when complete

async function submitChatJob(queryText, sessionId, history = [], bearerToken = "", jwtToken = "") {
  // Step 1: Submit the query and get a job_id.
  // Returns {job_id, status} or throws error.
  try {
    const headers = { "Content-Type": "application/json" };
    if (jwtToken) {
      headers["Authorization"] = `Bearer ${jwtToken}`;
    }

    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: queryText,
        session_id: sessionId,
        history: history.slice(-6).map(m => ({
          role: m.role,
          text: m.text || m.narrative || "",
        })),
        bearer_token: bearerToken,  // Required for real Oracle auth
      }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(error.detail || `Backend error: HTTP ${res.status}`);
    }

    const data = await res.json();
    return {
      job_id: data.job_id,
      status: data.status,  // "QUEUED"
      message: data.message,
    };
  } catch (err) {
    console.error("Failed to submit query:", err);
    throw err;
  }
}

async function pollChatJob(jobId, jwtToken = "", maxWaitMs = 300000) {
  // Step 2: Poll for job completion.
  // Returns result when status == "COMPLETE", throws error on timeout or ERROR status.
  const startTime = Date.now();
  const pollInterval = 1000;  // Poll every 1 second

  while (Date.now() - startTime < maxWaitMs) {
    try {
      const headers = { "Content-Type": "application/json" };
      if (jwtToken) {
        headers["Authorization"] = `Bearer ${jwtToken}`;
      }

      const res = await fetch(`${BACKEND_URL}/api/chat/${jobId}`, {
        method: "GET",
        headers,
      });

      if (!res.ok) {
        throw new Error(`Poll failed: HTTP ${res.status}`);
      }

      const data = await res.json();
      console.log(`[${jobId}] Poll status: ${data.status}`);

      if (data.status === "COMPLETE" && data.result) {
        // Map snake_case to camelCase
        const result = data.result;
        return {
          success: result.success,
          fallback: result.fallback || false,
          message: result.message,
          intent: result.intent,
          confidence: result.confidence,
          agentId: result.agent_id,
          agentName: result.agent_name,
          narrative: result.narrative,
          html: result.html,
          kpis: result.kpis,
          columns: result.columns,
          rows: result.rows,
          charts: result.charts,
          followUps: result.follow_ups,
        };
      }

      if (data.status === "ERROR") {
        throw new Error(`Job failed: ${data.error || "Unknown error"}`);
      }

      // Still processing, wait and retry
      await new Promise(r => setTimeout(r, pollInterval));

    } catch (err) {
      if (err.message.startsWith("Job failed")) throw err;
      console.warn(`Poll attempt failed: ${err.message}`);
      await new Promise(r => setTimeout(r, pollInterval));
    }
  }

  throw new Error(`Job polling timed out after ${maxWaitMs / 1000} seconds`);
}

async function callRouterAPI(queryText, sessionId, history = [], bearerToken = "", jwtToken = "") {
  // Complete async flow: submit job, then poll until complete.
  try {
    // Step 1: Submit job
    const submitResp = await submitChatJob(queryText, sessionId, history, bearerToken, jwtToken);
    console.log(`Job submitted: ${submitResp.job_id}`);

    // Step 2: Poll for result
    const result = await pollChatJob(submitResp.job_id, jwtToken);
    return result;

  } catch (err) {
    console.error("Backend call failed:", err);
    
    // Distinguish between Oracle agent errors and connection errors
    let userMessage;
    if (err.message.startsWith("Job failed:")) {
      // This is an Oracle agent error — show the agent's message directly
      userMessage = err.message.replace("Job failed: ", "");
    } else if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
      userMessage = `Cannot reach the backend server at ${BACKEND_URL}. Please make sure it is running.`;
    } else {
      userMessage = `${err.message}. Make sure the backend is running at ${BACKEND_URL} and you provided a valid bearer token.`;
    }
    
    return {
      success: false,
      fallback: true,
      message: userMessage,
    };
  }
}

// ── Commented out: Old sync API ────────────────────────────────────────────────
/*
async function callRouterAPI(queryText, sessionId, history = []) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: queryText,
        session_id: sessionId,
        history: history.slice(-6).map(m => ({
          role: m.role,
          text: m.text || m.narrative || "",
        })),
      }),
    });

    if (!res.ok) {
      throw new Error(`Backend error: HTTP ${res.status}`);
    }

    const data = await res.json();

    // Map snake_case backend fields to camelCase for the frontend
    return {
      success: data.success,
      fallback: data.fallback || false,
      message: data.message,
      intent: data.intent,
      confidence: data.confidence,
      agentId: data.agent_id,
      agentName: data.agent_name,
      narrative: data.narrative,
      html: data.html,
      kpis: data.kpis,
      columns: data.columns,
      rows: data.rows,
      charts: data.charts,
      followUps: data.follow_ups,
    };
  } catch (err) {
    console.error("Backend call failed:", err);
    return {
      success: false,
      fallback: true,
      message: `Could not reach the backend server. Make sure it's running at ${BACKEND_URL}. Error: ${err.message}`,
    };
  }
}
*/

// ─── Utility Helpers ──────────────────────────────────────────────────────────
function statusMeta(val) {
  const v = (val || "").toLowerCase();
  if (v.includes("overdue") || v.includes("at risk") || v.includes("critical"))
    return { bg: T.dangerBg, color: T.danger };
  if (v.includes("pending") || v.includes("waiting"))
    return { bg: T.warningBg, color: T.warning };
  if (v.includes("approved") || v.includes("on track") || v.includes("paid") || v.includes("completed"))
    return { bg: T.successBg, color: T.success };
  return { bg: T.navyLight, color: T.navyMid };
}

function uuid() {
  return Math.random().toString(36).slice(2, 10);
}

function formatTime(d) {
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// ─── Chart Component (SVG-based) ─────────────────────────────────────────────
const CHART_COLORS = ["#1A5C99", "#276749", "#9E2B1C", "#7B4F12", "#553C9A", "#0D7680"];

function InlineChart({ chart }) {
  if (!chart || !chart.labels || !chart.datasets?.length) return null;
  const { chart_type, title, labels, datasets } = chart;

  if (chart_type === "bar") {
    const W = 320, H = 160, pad = { top: 28, right: 12, bottom: 48, left: 44 };
    const innerW = W - pad.left - pad.right;
    const innerH = H - pad.top - pad.bottom;
    const allVals = datasets.flatMap(d => d.data);
    const maxVal = Math.max(...allVals, 1);
    const nGroups = labels.length;
    const nSeries = datasets.length;
    const groupW = innerW / nGroups;
    const barW = Math.min((groupW / nSeries) * 0.75, 32);

    return (
      <div style={{ marginBottom: "12px" }}>
        <div style={{ fontSize: "11px", fontWeight: 600, color: T.navyMid, marginBottom: "6px" }}>{title}</div>
        <svg width={W} height={H} style={{ overflow: "visible" }}>
          {/* Y-axis gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map(f => {
            const y = pad.top + innerH * (1 - f);
            return (
              <g key={f}>
                <line x1={pad.left} x2={pad.left + innerW} y1={y} y2={y} stroke={T.border} strokeWidth="1" />
                <text x={pad.left - 4} y={y + 3} textAnchor="end" fontSize="8" fill={T.muted}>
                  {f === 1 ? (maxVal >= 1000 ? `${(maxVal/1000).toFixed(0)}k` : maxVal) : ""}
                </text>
              </g>
            );
          })}
          {/* Bars */}
          {labels.map((lbl, gi) => (
            datasets.map((ds, si) => {
              const val = ds.data[gi] ?? 0;
              const bh = Math.max((val / maxVal) * innerH, 2);
              const x = pad.left + gi * groupW + (groupW - nSeries * barW) / 2 + si * barW;
              const y = pad.top + innerH - bh;
              const color = ds.color || CHART_COLORS[si % CHART_COLORS.length];
              return (
                <g key={`${gi}-${si}`}>
                  <rect x={x} y={y} width={barW - 2} height={bh} fill={color} rx="2" opacity="0.88" />
                  {bh > 14 && (
                    <text x={x + (barW - 2) / 2} y={y - 3} textAnchor="middle" fontSize="7" fill={T.slate}>
                      {val >= 1000 ? `${(val/1000).toFixed(0)}k` : val}
                    </text>
                  )}
                </g>
              );
            })
          ))}
          {/* X labels */}
          {labels.map((lbl, gi) => (
            <text key={gi} x={pad.left + gi * groupW + groupW / 2} y={pad.top + innerH + 14}
              textAnchor="middle" fontSize="8" fill={T.slate}>
              {lbl.length > 10 ? lbl.slice(0, 9) + "…" : lbl}
            </text>
          ))}
          {/* Legend */}
          {nSeries > 1 && datasets.map((ds, si) => (
            <g key={si} transform={`translate(${pad.left + si * 80}, ${H - 10})`}>
              <rect width="8" height="8" fill={ds.color || CHART_COLORS[si]} rx="1" />
              <text x="11" y="7" fontSize="8" fill={T.slate}>{ds.label}</text>
            </g>
          ))}
        </svg>
      </div>
    );
  }

  if (chart_type === "pie" || chart_type === "doughnut") {
    const cx = 70, cy = 70, r = 55, ir = chart_type === "doughnut" ? 28 : 0;
    const total = datasets[0]?.data.reduce((a, b) => a + b, 0) || 1;
    let startAngle = -Math.PI / 2;
    const slices = labels.map((lbl, i) => {
      const val = datasets[0]?.data[i] ?? 0;
      const angle = (val / total) * Math.PI * 2;
      const endAngle = startAngle + angle;
      const x1 = cx + r * Math.cos(startAngle), y1 = cy + r * Math.sin(startAngle);
      const x2 = cx + r * Math.cos(endAngle), y2 = cy + r * Math.sin(endAngle);
      const xi1 = cx + ir * Math.cos(startAngle), yi1 = cy + ir * Math.sin(startAngle);
      const xi2 = cx + ir * Math.cos(endAngle), yi2 = cy + ir * Math.sin(endAngle);
      const lg = angle > Math.PI ? 1 : 0;
      const color = CHART_COLORS[i % CHART_COLORS.length];
      const path = ir > 0
        ? `M${xi1},${yi1} L${x1},${y1} A${r},${r} 0 ${lg},1 ${x2},${y2} L${xi2},${yi2} A${ir},${ir} 0 ${lg},0 ${xi1},${yi1} Z`
        : `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${lg},1 ${x2},${y2} Z`;
      const slice = { lbl, val, path, color, pct: Math.round(val / total * 100) };
      startAngle = endAngle;
      return slice;
    });

    return (
      <div style={{ marginBottom: "12px" }}>
        <div style={{ fontSize: "11px", fontWeight: 600, color: T.navyMid, marginBottom: "6px" }}>{title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <svg width={140} height={140}>
            {slices.map((s, i) => <path key={i} d={s.path} fill={s.color} stroke={T.white} strokeWidth="1.5" />)}
            {chart_type === "doughnut" && (
              <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill={T.navy}>
                {slices[0]?.pct}%
              </text>
            )}
          </svg>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {slices.map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <div style={{ width: "10px", height: "10px", borderRadius: "2px", background: s.color, flexShrink: 0 }} />
                <span style={{ fontSize: "10px", color: T.slate }}>{s.lbl}</span>
                <span style={{ fontSize: "10px", fontWeight: 600, color: T.navy, marginLeft: "auto" }}>{s.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return null;
}

// ─── Sub-Components ───────────────────────────────────────────────────────────

function KPIGrid({ kpis }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "8px", marginBottom: "14px" }}>
      {kpis.map((k, i) => (
        <div key={i} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: T.radius, padding: "10px 12px" }}>
          <div style={{ fontSize: "10px", color: T.muted, fontWeight: 500, marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{k.label}</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: T.navy, letterSpacing: "-0.02em" }}>{k.value}</div>
          {k.trend && (
            <div style={{ fontSize: "10px", color: k.up === false ? T.danger : k.up === true ? T.success : T.muted, marginTop: "2px" }}>
              {k.up === false ? "▼ " : k.up === true ? "▲ " : ""}{k.trend}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function DataTable({ columns, rows }) {
  return (
    <div style={{ overflowX: "auto", borderRadius: T.radius, border: `1px solid ${T.border}`, marginBottom: "12px" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
        <thead>
          <tr style={{ background: T.navyLight }}>
            {columns.map((c, i) => (
              <th key={i} style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, color: T.navyMid, fontSize: "11px", letterSpacing: "0.04em", borderBottom: `1px solid ${T.border}`, whiteSpace: "nowrap" }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: ri < rows.length - 1 ? `1px solid ${T.border}` : "none", background: ri % 2 === 0 ? T.white : T.bg }}>
              {row.map((cell, ci) => {
                const sm = statusMeta(cell);
                const isStatus = /overdue|pending|approved|on track|at risk|critical|completed|waiting/i.test(cell);
                return (
                  <td key={ci} style={{ padding: "8px 12px", color: T.slate, verticalAlign: "middle" }}>
                    {isStatus ? (
                      <span style={{ background: sm.bg, color: sm.color, borderRadius: "20px", padding: "3px 9px", fontSize: "10px", fontWeight: 600, whiteSpace: "nowrap" }}>{cell}</span>
                    ) : cell}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NarrativeText({ text }) {
  if (!text) return null;
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return (
    <div style={{ fontSize: "13px", color: T.slate, lineHeight: 1.65, marginBottom: "12px", whiteSpace: "pre-wrap" }}>
      {parts.map((p, i) => i % 2 === 1 ? <strong key={i} style={{ color: T.navy, fontWeight: 600 }}>{p}</strong> : p)}
    </div>
  );
}

function FollowUpChips({ items, onSelect }) {
  return (
    <div>
      <div style={{ fontSize: "10px", color: T.muted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" }}>Suggested follow-ups</div>
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {items.map((f, i) => (
          <button key={i} onClick={() => onSelect(f)} style={{ fontSize: "11px", padding: "5px 12px", borderRadius: "20px", border: `1px solid ${T.borderDark}`, background: T.white, color: T.navyMid, cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s" }}
            onMouseEnter={e => { e.target.style.background = T.navyLight; e.target.style.borderColor = T.navy; }}
            onMouseLeave={e => { e.target.style.background = T.white; e.target.style.borderColor = T.borderDark; }}>
            {f} ↗
          </button>
        ))}
      </div>
    </div>
  );
}

function AgentBadge({ agent }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "5px", padding: "3px 10px 3px 7px", borderRadius: "20px", background: agent.bg, marginBottom: "8px", border: `1px solid ${agent.color}22` }}>
      <span style={{ fontSize: "12px" }}>{agent.icon}</span>
      <span style={{ fontSize: "10px", fontWeight: 700, color: agent.color, textTransform: "uppercase", letterSpacing: "0.08em" }}>{agent.shortName} Agent</span>
    </div>
  );
}

function ConfidenceMeter({ value }) {
  const pct = Math.round(value * 100);
  const color = pct >= 85 ? T.success : pct >= 65 ? T.warning : T.danger;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div style={{ width: "50px", height: "4px", background: T.border, borderRadius: "2px", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "2px", transition: "width 0.5s ease" }} />
      </div>
      <span style={{ fontSize: "10px", color, fontWeight: 600 }}>{pct}%</span>
    </div>
  );
}

function RouterPipeline({ stage }) {
  const steps = [
    { id: 0, label: "Input" },
    { id: 1, label: "Classify" },
    { id: 2, label: "Registry" },
    { id: 3, label: "Agent Call" },
    { id: 4, label: "Render" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0", padding: "0 16px" }}>
      {steps.map((s, i) => {
        const done = stage > s.id;
        const active = stage === s.id;
        return (
          <div key={s.id} style={{ display: "flex", alignItems: "center", flex: i < steps.length - 1 ? 1 : 0 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
              <div style={{ width: "20px", height: "20px", borderRadius: "50%", background: done ? T.success : active ? T.oracle : T.border, display: "flex", alignItems: "center", justifyContent: "center", transition: "background 0.3s", fontSize: "9px", color: done || active ? T.white : T.muted, fontWeight: 700 }}>
                {done ? "✓" : s.id + 1}
              </div>
              <span style={{ fontSize: "9px", color: done ? T.success : active ? T.oracle : T.muted, fontWeight: active || done ? 600 : 400, whiteSpace: "nowrap" }}>{s.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div style={{ flex: 1, height: "1px", background: done ? T.success : T.border, margin: "0 3px", marginBottom: "14px", transition: "background 0.3s" }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: "4px", padding: "6px 2px", alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{ width: "6px", height: "6px", borderRadius: "50%", background: T.muted, animation: `pulse 1.2s ${i * 0.2}s infinite` }} />
      ))}
    </div>
  );
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg, agents, onFollowUp }) {
  const agent = agents.find(a => a.id === msg.agentId);

  if (msg.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "14px", gap: "10px", alignItems: "flex-start" }}>
        <div style={{ maxWidth: "70%" }}>
          <div style={{ background: T.navy, color: T.white, borderRadius: `${T.radiusMd} ${T.radiusMd} 2px ${T.radiusMd}`, padding: "10px 14px", fontSize: "13px", lineHeight: 1.55 }}>{msg.text}</div>
          <div style={{ textAlign: "right", fontSize: "10px", color: T.muted, marginTop: "4px" }}>{formatTime(msg.time)}</div>
        </div>
        <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: T.navyMid, color: T.white, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700, flexShrink: 0, marginTop: "2px" }}>
          {msg.userName ? msg.userName.slice(0, 1).toUpperCase() : "U"}
        </div>
      </div>
    );
  }

  if (msg.role === "system" && msg.fallback) {
    return (
      <div style={{ display: "flex", gap: "10px", marginBottom: "14px", alignItems: "flex-start" }}>
        <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: T.oracleLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", flexShrink: 0 }}>🤖</div>
        <div style={{ maxWidth: "75%" }}>
          <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: `2px ${T.radiusMd} ${T.radiusMd} ${T.radiusMd}`, padding: "12px 14px", boxShadow: T.shadow }}>
            <p style={{ fontSize: "13px", color: T.slate, lineHeight: 1.6, margin: 0 }}>{msg.text}</p>
          </div>
          <div style={{ fontSize: "10px", color: T.muted, marginTop: "4px" }}>{formatTime(msg.time)}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", gap: "10px", marginBottom: "18px", alignItems: "flex-start" }}>
      <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: agent?.bg || T.oracleLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", flexShrink: 0, marginTop: "2px" }}>
        {agent?.icon || "🤖"}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: `2px ${T.radiusMd} ${T.radiusMd} ${T.radiusMd}`, padding: "14px 16px", boxShadow: T.shadow }}>
          {agent && <AgentBadge agent={agent} />}
          {msg.intent && (
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "10px", padding: "6px 10px", background: T.bg, borderRadius: T.radius, border: `1px solid ${T.border}` }}>
              <span style={{ fontSize: "10px", color: T.muted }}>Intent:</span>
              <span style={{ fontSize: "10px", fontFamily: "monospace", fontWeight: 700, color: T.navyMid }}>{msg.intent}</span>
              <ConfidenceMeter value={msg.confidence} />
            </div>
          )}
          {msg.html && (
            <div style={{ fontSize: '13px', color: T.slate, lineHeight: 1.65, marginBottom: '12px' }} dangerouslySetInnerHTML={{ __html: msg.html }} />
          )}
          {msg.narrative && (
            <NarrativeText text={msg.narrative} />
          )}
          {msg.kpis && <KPIGrid kpis={msg.kpis} />}
          {msg.columns && msg.rows && <DataTable columns={msg.columns} rows={msg.rows} />}
          {msg.charts && msg.charts.length > 0 && (
            <div style={{ marginTop: "4px" }}>
              {msg.charts.map((chart, ci) => <InlineChart key={ci} chart={chart} />)}
            </div>
          )}
          {msg.followUps && <FollowUpChips items={msg.followUps} onSelect={onFollowUp} />}
        </div>
        <div style={{ fontSize: "10px", color: T.muted, marginTop: "4px" }}>
          {agent?.name} Agent · {formatTime(msg.time)}
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar: Agent Panel ─────────────────────────────────────────────────────
function AgentPanel({ agents, activeAgentId, stats, onSelectAgent }) {
  return (
    <div style={{ width: "220px", flexShrink: 0, borderRight: `1px solid ${T.border}`, background: T.white, display: "flex", flexDirection: "column", overflowY: "auto" }}>
      <div style={{ padding: "14px 16px 10px", borderBottom: `1px solid ${T.border}` }}>
        <div style={{ fontSize: "10px", fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.08em" }}>Active Agents</div>
        <div style={{ fontSize: "11px", color: T.muted, marginTop: "2px" }}>
          {activeAgentId ? "1 agent selected" : `${agents.length} agents online`}
        </div>
      </div>
      <div style={{ padding: "8px", flex: 1 }}>
        {agents.map(a => (
          <button
            key={a.id}
            type="button"
            onClick={() => onSelectAgent(a.id)}
            aria-pressed={a.id === activeAgentId}
            title={a.description}
            style={{ width: "100%", borderRadius: T.radius, padding: "9px 10px", marginBottom: "3px", border: `1px solid ${a.id === activeAgentId ? a.color + "44" : "transparent"}`, background: a.id === activeAgentId ? a.bg : "transparent", transition: "all 0.2s", textAlign: "left", cursor: "pointer", fontFamily: "inherit" }}
            onMouseEnter={e => {
              if (a.id !== activeAgentId) {
                e.currentTarget.style.background = T.bg;
                e.currentTarget.style.borderColor = T.border;
              }
            }}
            onMouseLeave={e => {
              if (a.id !== activeAgentId) {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.borderColor = "transparent";
              }
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "16px" }}>{a.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "12px", fontWeight: a.id === activeAgentId ? 600 : 400, color: a.id === activeAgentId ? a.color : T.navy, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.shortName}</div>
                <div style={{ fontSize: "9px", color: T.muted, marginTop: "1px" }}>{a.intents.length} intent{a.intents.length > 1 ? "s" : ""}</div>
              </div>
              <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: T.success, flexShrink: 0 }} title="Online" />
            </div>
            {a.id === activeAgentId && (
              <div style={{ marginTop: "6px", fontSize: "10px", color: a.color, fontStyle: "italic", paddingLeft: "24px" }}>Selected - click again to clear</div>
            )}
          </button>
        ))}
      </div>
      <div style={{ padding: "12px 16px", borderTop: `1px solid ${T.border}`, background: T.bg }}>
        <div style={{ fontSize: "10px", fontWeight: 600, color: T.muted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>Session Stats</div>
        {[["Queries", stats.queries], ["Agents used", stats.agentsUsed], ["Avg confidence", stats.avgConf + "%"]].map(([label, val]) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ fontSize: "11px", color: T.muted }}>{label}</span>
            <span style={{ fontSize: "11px", fontWeight: 600, color: T.navy }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Query Input Bar ──────────────────────────────────────────────────────────
function QueryInputBar({ onSubmit, disabled, suggestions }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  const handleSubmit = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSubmit(t);
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "40px";
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const handleChange = (e) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = "40px";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <div style={{ borderTop: `1px solid ${T.border}`, background: T.white }}>
      {suggestions.length > 0 && (
        <div style={{ padding: "8px 16px 0", display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => { setText(s); textareaRef.current?.focus(); }}
              style={{ fontSize: "11px", padding: "4px 11px", borderRadius: "20px", border: `1px solid ${T.border}`, background: T.bg, color: T.slate, cursor: "pointer", fontFamily: "inherit" }}>
              {s}
            </button>
          ))}
        </div>
      )}
      <div style={{ display: "flex", gap: "10px", padding: "12px 16px", alignItems: "flex-end" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <textarea ref={textareaRef} value={text} onChange={handleChange} onKeyDown={handleKey} disabled={disabled}
            placeholder="Ask anything — invoices, project margins, payroll, purchase orders…"
            style={{ width: "100%", padding: "10px 14px", fontSize: "13px", border: `1px solid ${disabled ? T.border : T.borderDark}`, borderRadius: T.radiusMd, background: disabled ? T.bg : T.white, color: T.navy, fontFamily: "inherit", resize: "none", lineHeight: 1.5, height: "40px", minHeight: "40px", maxHeight: "120px", outline: "none", transition: "border-color 0.15s", boxSizing: "border-box" }}
            onFocus={e => { e.target.style.borderColor = T.oracle; }}
            onBlur={e => { e.target.style.borderColor = T.borderDark; }}
          />
        </div>
        <button onClick={handleSubmit} disabled={disabled || !text.trim()}
          style={{ width: "40px", height: "40px", borderRadius: "50%", border: "none", background: disabled || !text.trim() ? T.border : T.oracle, color: T.white, cursor: disabled || !text.trim() ? "not-allowed" : "pointer", fontSize: "16px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background 0.2s" }}>
          ↑
        </button>
      </div>
      <div style={{ padding: "0 16px 10px", fontSize: "10px", color: T.muted }}>
        Press <kbd style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: "3px", padding: "1px 5px", fontSize: "10px" }}>Enter</kbd> to send · <kbd style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: "3px", padding: "1px 5px", fontSize: "10px" }}>Shift+Enter</kbd> for new line
      </div>
    </div>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────
function Header({ user, onSignOut, themeKey, onThemeChange }) {
  return (
    <div style={{ height: "54px", background: T.navy, display: "flex", alignItems: "center", padding: "0 20px", gap: "12px", flexShrink: 0, borderBottom: `3px solid ${T.oracle}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1 }}>
        <div style={{ width: "28px", height: "28px", borderRadius: "6px", background: T.oracle, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ color: T.white, fontSize: "14px", fontWeight: 800 }}>O</span>
        </div>
        <div>
          <div style={{ color: T.white, fontWeight: 700, fontSize: "13px", letterSpacing: "0.01em" }}>Oracle Agent Hub</div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "10px" }}>Multi-Agent Router Platform · SPLCG Infotech</div>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.72)", fontWeight: 600 }}>Theme</span>
          <select
            value={themeKey}
            onChange={(e) => onThemeChange(e.target.value)}
            style={{
              padding: "5px 8px",
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.25)",
              background: "rgba(255,255,255,0.1)",
              color: "#fff",
              fontSize: "11px",
              fontWeight: 600,
              outline: "none",
              cursor: "pointer",
            }}
          >
            {THEME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} style={{ color: "#111827" }}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#48BB78" }} />
          <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)" }}>All systems operational</span>
        </div>
        <div style={{ width: "1px", height: "20px", background: "rgba(255,255,255,0.15)" }} />
        <div style={{ display: "flex", alignItems: "center", gap: "7px", cursor: "pointer" }}>
          <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: T.navyMid, border: `1px solid rgba(255,255,255,0.2)`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700, color: T.white }}>
            {user.initials}
          </div>
          <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.75)", fontWeight: 500 }}>{user.name}</span>
        </div>
        <button
          onClick={onSignOut}
          style={{ padding: "8px 12px", borderRadius: "999px", border: "1px solid rgba(255,255,255,0.22)", background: "rgba(255,255,255,0.08)", color: "#fff", cursor: "pointer", fontSize: "11px", fontWeight: 700 }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

// ─── Router Status Bar ────────────────────────────────────────────────────────
function RouterStatusBar({ stage, intent, agentName, confidence, isIdle }) {
  return (
    <div style={{ background: T.bg, borderBottom: `1px solid ${T.border}`, padding: "10px 20px", display: "flex", alignItems: "center", gap: "20px", flexShrink: 0 }}>
      <div style={{ flex: 1 }}>
        <RouterPipeline stage={isIdle ? -1 : stage} />
      </div>
      {!isIdle && intent && (
        <div style={{ display: "flex", gap: "16px", alignItems: "center", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: "9px", color: T.muted, fontWeight: 600, textTransform: "uppercase" }}>Last Intent</div>
            <div style={{ fontSize: "11px", fontFamily: "monospace", fontWeight: 700, color: T.navyMid }}>{intent}</div>
          </div>
          <div>
            <div style={{ fontSize: "9px", color: T.muted, fontWeight: 600, textTransform: "uppercase" }}>Agent</div>
            <div style={{ fontSize: "11px", fontWeight: 600, color: T.navy }}>{agentName}</div>
          </div>
          <div>
            <div style={{ fontSize: "9px", color: T.muted, fontWeight: 600, textTransform: "uppercase" }}>Confidence</div>
            <ConfidenceMeter value={confidence} />
          </div>
        </div>
      )}
      {isIdle && <span style={{ fontSize: "11px", color: T.muted, flexShrink: 0 }}>Router ready — awaiting query</span>}
    </div>
  );
}

// ─── Welcome Screen ───────────────────────────────────────────────────────────
function WelcomeScreen({ onExampleClick }) {
  const examples = [
    { text: "Show unpaid invoices for Siemens", icon: "💳", agent: "AR Credit" },
    { text: "Which projects are at margin risk this quarter?", icon: "📊", agent: "PPM Margin" },
    { text: "Why is the month-end close delayed?", icon: "📅", agent: "Finance Close" },
    { text: "List open purchase orders above $50,000", icon: "🛒", agent: "Procurement" },
    { text: "Pending leave requests for my team", icon: "👥", agent: "HCM / Payroll" },
    { text: "Generate ageing report for Q1 receivables", icon: "📋", agent: "AR Credit" },
  ];
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 24px", overflowY: "auto" }}>
      <div style={{ maxWidth: "560px", width: "100%", textAlign: "center" }}>
        <div style={{ width: "56px", height: "56px", borderRadius: "14px", background: T.oracleLight, border: `2px solid ${T.oracle}22`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: "26px" }}>🤖</div>
        <h2 style={{ fontSize: "20px", fontWeight: 700, color: T.navy, margin: "0 0 8px", letterSpacing: "-0.02em" }}>How can I help you today?</h2>
        <p style={{ fontSize: "13px", color: T.muted, lineHeight: 1.6, margin: "0 0 28px" }}>
          Ask a question in plain English. I'll automatically detect what you need and route it to the right Oracle agent — no need to know which system to use.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", textAlign: "left" }}>
          {examples.map((ex, i) => (
            <button key={i} onClick={() => onExampleClick(ex.text)}
              style={{ padding: "11px 13px", border: `1px solid ${T.border}`, borderRadius: T.radiusMd, background: T.white, cursor: "pointer", textAlign: "left", fontFamily: "inherit", transition: "all 0.15s", boxShadow: T.shadow }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = T.oracle; e.currentTarget.style.boxShadow = T.shadowMd; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.boxShadow = T.shadow; }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
                <span style={{ fontSize: "16px", flexShrink: 0 }}>{ex.icon}</span>
                <div>
                  <div style={{ fontSize: "12px", color: T.navy, lineHeight: 1.4, marginBottom: "3px" }}>{ex.text}</div>
                  <div style={{ fontSize: "10px", color: T.muted }}>→ {ex.agent}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function OracleAgentHub() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [routerStage, setRouterStage] = useState(-1);
  const [lastIntent, setLastIntent] = useState(null);
  const [lastAgent, setLastAgent] = useState(null);
  const [lastConf, setLastConf] = useState(0);
  const [activeAgentId, setActiveAgentId] = useState(null);
  const [sessionId] = useState(() => "sess_" + uuid());
  const [confList, setConfList] = useState([]);
  const [bearerToken, setBearerToken] = useState(sessionStorage.getItem("bearerToken") || "");  // Session-scoped token persistence
  const [themeKey, setThemeKey] = useState(() => localStorage.getItem("hubTheme") || "light");
  const chatRef = useRef(null);
  const { token, user: authUser, signOut } = useAuth();

  const user = authUser || { name: "Guest", initials: "G", id: "guest" };
  const selectedAgent = AGENTS.find(agent => agent.id === activeAgentId) || null;

  const scrollToBottom = useCallback(() => {
    setTimeout(() => { chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" }); }, 80);
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, loading]);

  useEffect(() => {
    const selectedTheme = THEME_PRESETS[themeKey] || THEME_PRESETS.light;
    const root = document.documentElement;
    root.style.setProperty("--theme-oracle", selectedTheme.oracle);
    root.style.setProperty("--theme-oracle-dark", selectedTheme.oracleDark);
    root.style.setProperty("--theme-oracle-light", selectedTheme.oracleLight);
    root.style.setProperty("--theme-navy", selectedTheme.navy);
    root.style.setProperty("--theme-navy-mid", selectedTheme.navyMid);
    root.style.setProperty("--theme-navy-light", selectedTheme.navyLight);
    root.style.setProperty("--theme-slate", selectedTheme.slate);
    root.style.setProperty("--theme-muted", selectedTheme.muted);
    root.style.setProperty("--theme-border", selectedTheme.border);
    root.style.setProperty("--theme-border-dark", selectedTheme.borderDark);
    root.style.setProperty("--theme-bg", selectedTheme.bg);
    root.style.setProperty("--theme-white", selectedTheme.white);
    root.style.setProperty("--theme-success", selectedTheme.success);
    root.style.setProperty("--theme-success-bg", selectedTheme.successBg);
    root.style.setProperty("--theme-warning", selectedTheme.warning);
    root.style.setProperty("--theme-warning-bg", selectedTheme.warningBg);
    root.style.setProperty("--theme-danger", selectedTheme.danger);
    root.style.setProperty("--theme-danger-bg", selectedTheme.dangerBg);
    root.style.setProperty("--theme-info", selectedTheme.info);
    root.style.setProperty("--theme-info-bg", selectedTheme.infoBg);
    localStorage.setItem("hubTheme", themeKey);
  }, [themeKey]);

  const sessionStats = {
    queries: messages.filter(m => m.role === "user").length,
    agentsUsed: new Set(messages.filter(m => m.agentId).map(m => m.agentId)).size,
    avgConf: confList.length ? Math.round(confList.reduce((a, b) => a + b, 0) / confList.length * 100) : "—",
  };

  const suggestions = selectedAgent
    ? AGENT_QUICK_PROMPTS[selectedAgent.id].slice(0, 3)
    : messages.length === 0 ? [] : [
        "Show credit limit for Siemens",
        "Generate ageing report Q1",
        "Compare Q1 vs Q2 margins",
      ].slice(0, 2);

  function handleAgentSelect(agentId) {
    setActiveAgentId(prev => (prev === agentId ? null : agentId));
  }

  async function handleQuery(queryText) {
    if (loading) return;

    const userMsg = { id: uuid(), role: "user", text: queryText, time: new Date(), userName: user.name };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setRouterStage(0);

    await new Promise(r => setTimeout(r, 300));
    setRouterStage(1);
    await new Promise(r => setTimeout(r, 400));
    setRouterStage(2);

    // NEW: Pass bearerToken and auth token to callRouterAPI
    const result = await callRouterAPI(queryText, sessionId, messages.slice(-6), bearerToken, token);

    setRouterStage(3);
    await new Promise(r => setTimeout(r, 250));
    setRouterStage(4);

    if (result.success) {
      setLastIntent(result.intent);
      setLastAgent(result.agentName);
      setLastConf(result.confidence);
      setActiveAgentId(result.agentId);
      setConfList(prev => [...prev, result.confidence]);
      setMessages(prev => [...prev, {
        id: uuid(), role: "system", time: new Date(),
        agentId: result.agentId, intent: result.intent, confidence: result.confidence,
        narrative: result.narrative, html: result.html, kpis: result.kpis,
        columns: result.columns, rows: result.rows,
        charts: result.charts,
        followUps: result.followUps,
      }]);
    } else {
      setMessages(prev => [...prev, {
        id: uuid(), role: "system", fallback: true, time: new Date(),
        text: result.message,
      }]);
      setActiveAgentId(null);
    }

    setLoading(false);
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'DM Sans', sans-serif; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #CBD5E0; border-radius: 10px; }
        @keyframes pulse { 0%,80%,100%{opacity:0.25;transform:scale(0.8)} 40%{opacity:1;transform:scale(1)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "'DM Sans', sans-serif", background: T.bg, minHeight: "500px" }}>
        <Header user={user} onSignOut={signOut} themeKey={themeKey} onThemeChange={setThemeKey} />
        <RouterStatusBar stage={routerStage} intent={lastIntent} agentName={lastAgent} confidence={lastConf} isIdle={messages.length === 0 && !loading} />
        
        {/* NEW: Bearer Token Input Section */}
        <div style={{ background: T.white, borderBottom: `1px solid ${T.border}`, padding: "12px 20px", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: T.muted, textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
            🔐 Oracle Bearer Token (Optional)
          </label>
              <input
                type="password"
                placeholder="Paste your Oracle Fusion bearer token here..."
                value={bearerToken}
                onChange={(e) => {
                  setBearerToken(e.target.value);
                  sessionStorage.setItem("bearerToken", e.target.value);  // Persist only for current tab session
                }}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  fontSize: "12px",
                  border: `1px solid ${bearerToken ? T.success : T.warning}`,
                  borderRadius: T.radius,
                  fontFamily: "monospace",
                  background: bearerToken ? "#F0FDF4" : "#FFFBEB",
                  color: T.navy,
                  transition: "all 0.2s",
                }}
              />
              <div style={{ fontSize: "10px", color: T.muted, marginTop: "4px" }}>
                {bearerToken ? "✓ Token loaded" : "Oracle mode: token optional if OAuth/basic auth is configured"}
              </div>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          <AgentPanel agents={AGENTS} activeAgentId={activeAgentId} stats={sessionStats} onSelectAgent={handleAgentSelect} />

          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: T.bg }}>
            {messages.length === 0 && !loading ? (
              <WelcomeScreen onExampleClick={handleQuery} />
            ) : (
              <div ref={chatRef} style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
                {messages.map(msg => (
                  <div key={msg.id} style={{ animation: "fadeIn 0.25s ease" }}>
                    <MessageBubble msg={msg} agents={AGENTS} onFollowUp={handleQuery} />
                  </div>
                ))}
                {loading && (
                  <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", animation: "fadeIn 0.2s ease" }}>
                    <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: T.oracleLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", flexShrink: 0 }}>🤖</div>
                    <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: `2px ${T.radiusMd} ${T.radiusMd} ${T.radiusMd}`, padding: "12px 16px", boxShadow: T.shadow }}>
                      <TypingIndicator />
                    </div>
                  </div>
                )}
              </div>
            )}
            <QueryInputBar onSubmit={handleQuery} disabled={loading} suggestions={suggestions} />
          </div>
        </div>
      </div>
    </>
  );
}
