// src/pages/Overview.jsx
import { useEffect, useState } from "react";
import { api } from "../services/api";
import StatCard from "../components/cards/StatCard";
import RiskBadge from "../components/cards/Riskbadge";

export default function Overview() {
  const [inventory, setInventory] = useState(null);
  const [orders, setOrders]       = useState(null);
  const [status, setStatus]       = useState(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([
      api.getInventory(),
      api.getOrders(),
      api.pipelineStatus(),
    ]).then(([inv, ord, st]) => {
      setInventory(inv.data);
      setOrders(ord.data);
      setStatus(st.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingScreen />;

  const critical = inventory?.items?.filter(i => i.stockout_risk === "critical") || [];
  const high     = inventory?.items?.filter(i => i.stockout_risk === "high") || [];

  return (
    <div style={{ padding: "32px 36px" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 11,
          color: "var(--text-muted)", letterSpacing: 3, marginBottom: 6,
        }}>WAREHOUSE CONTROL CENTER</div>
        <h1 style={{
          fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700,
          color: "var(--green-glow)", textShadow: "0 0 24px rgba(74,222,128,0.3)",
        }}>System Overview</h1>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
          {new Date().toLocaleString()} · Pipeline MAPE: {status?.avg_mape ? `${status.avg_mape}%` : "—"}
        </div>
      </div>

      {/* Stat cards */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
        gap: 16, marginBottom: 32,
      }}>
        <StatCard label="Total SKUs"       value={inventory?.total_skus ?? "—"}   sub="active products" />
        <StatCard label="Critical Alerts"  value={inventory?.critical_count ?? 0} sub="immediate action needed" accent="var(--red)"   alert={inventory?.critical_count > 0} />
        <StatCard label="High Risk"        value={inventory?.high_count ?? 0}     sub="order within 7 days"     accent="var(--amber)" />
        <StatCard label="Purchase Orders"  value={orders?.total_orders ?? 0}      sub="auto-generated today"    accent="var(--blue)"  />
      </div>

      {/* Critical alerts */}
      {critical.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="Critical Stockout Alerts" count={critical.length} color="var(--red)" />
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {critical.map(item => (
              <AlertRow key={item.sku_id} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* High risk */}
      {high.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="High Risk Items" count={high.length} color="var(--amber)" />
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {high.map(item => (
              <AlertRow key={item.sku_id} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Pipeline status */}
      <div style={{ marginTop: 32 }}>
        <SectionHeader title="Pipeline Status" />
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: 8, padding: "20px 24px",
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24,
        }}>
          <Metric label="STATUS"        value={status?.status?.toUpperCase() ?? "—"}  color="var(--green-bright)" />
          <Metric label="SKUS TRAINED"  value={status?.skus_trained ?? "—"}           color="var(--green-text)" />
          <Metric label="AVG MAPE"      value={status?.avg_mape ? `${status.avg_mape}%` : "—"} color={status?.avg_mape < 20 ? "var(--green-bright)" : "var(--amber)"} />
        </div>
      </div>
    </div>
  );
}

function AlertRow({ item }) {
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: 8, padding: "14px 20px",
      display: "flex", alignItems: "center", justifyContent: "space-between",
      animation: "slide-in 0.3s ease forwards",
    }}>
      <div>
        <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text-primary)", marginBottom: 2 }}>
          {item.sku_name}
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
          {item.sku_id} · stock: {item.current_stock} · reorder at: {item.reorder_point}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--red)" }}>
            {item.days_until_stockout != null ? `${item.days_until_stockout}d left` : "—"}
          </div>
        </div>
        <RiskBadge level={item.stockout_risk} />
      </div>
    </div>
  );
}

function SectionHeader({ title, count, color = "var(--green-bright)" }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      marginBottom: 12,
    }}>
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: 12,
        color, letterSpacing: 2, textTransform: "uppercase",
      }}>{title}</div>
      {count != null && (
        <span style={{
          background: color + "22", color,
          border: `1px solid ${color}44`,
          borderRadius: 4, padding: "1px 8px",
          fontFamily: "var(--font-mono)", fontSize: 11,
        }}>{count}</span>
      )}
    </div>
  );
}

function Metric({ label, value, color }) {
  return (
    <div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2, marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, color, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div style={{
      height: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "var(--font-mono)", color: "var(--green-mid)", fontSize: 14, letterSpacing: 3,
    }}>
      LOADING SYSTEM DATA...
    </div>
  );
}