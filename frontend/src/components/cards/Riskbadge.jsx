// src/components/cards/RiskBadge.jsx

const RISK = {
  critical: { bg: "#3f0f0f", color: "#ef4444", border: "#7f1d1d", label: "CRITICAL" },
  high:     { bg: "#3f2a0a", color: "#f59e0b", border: "#78350f", label: "HIGH"     },
  medium:   { bg: "#1a2a0a", color: "#84cc16", border: "#3f6212", label: "MEDIUM"   },
  low:      { bg: "#0a1f0f", color: "#22c55e", border: "#14532d", label: "LOW"      },
};

export default function RiskBadge({ level }) {
  const r = RISK[level] || RISK.low;
  return (
    <span style={{
      background: r.bg,
      color: r.color,
      border: `1px solid ${r.border}`,
      borderRadius: 4,
      padding: "2px 10px",
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      letterSpacing: 1,
      fontWeight: 700,
      animation: level === "critical" ? "blink 1.5s infinite" : "none",
    }}>{r.label}</span>
  );
}