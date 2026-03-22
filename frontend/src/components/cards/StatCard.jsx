// src/components/cards/StatCard.jsx

export default function StatCard({ label, value, sub, accent = "var(--green-bright)", alert = false }) {
  return (
    <div style={{
      background: "var(--bg-card)",
      border: `1px solid ${alert ? "var(--red)" : "var(--border)"}`,
      borderRadius: 8,
      padding: "20px 24px",
      animation: "slide-in 0.4s ease forwards",
      boxShadow: alert ? "0 0 16px rgba(239,68,68,0.2)" : "none",
      transition: "border 0.2s",
    }}>
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--text-muted)",
        letterSpacing: 2,
        marginBottom: 8,
        textTransform: "uppercase",
      }}>{label}</div>
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 36,
        fontWeight: 700,
        color: accent,
        textShadow: `0 0 16px ${accent}60`,
        animation: "count-up 0.5s ease forwards",
        lineHeight: 1,
      }}>{value}</div>
      {sub && (
        <div style={{
          fontFamily: "var(--font-display)",
          fontSize: 12,
          color: "var(--text-muted)",
          marginTop: 6,
        }}>{sub}</div>
      )}
    </div>
  );
}