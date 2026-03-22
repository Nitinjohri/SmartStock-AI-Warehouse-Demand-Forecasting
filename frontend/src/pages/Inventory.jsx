// src/pages/Inventory.jsx
import { useEffect, useState } from "react";
import { api } from "../services/api";
import RiskBadge from "../components/cards/Riskbadge";

export default function Inventory() {
  const [data, setData]       = useState(null);
  const [filter, setFilter]   = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getInventory()
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const items = data?.items?.filter(i =>
    filter === "all" ? true : i.stockout_risk === filter
  ) || [];

  const filters = ["all", "critical", "high", "medium", "low"];

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", letterSpacing: 3, marginBottom: 6 }}>
          STOCK INTELLIGENCE
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, color: "var(--green-glow)", textShadow: "0 0 24px rgba(74,222,128,0.3)" }}>
          Inventory Status
        </h1>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{
              padding: "6px 16px", borderRadius: 4,
              border: `1px solid ${filter === f ? "var(--green-bright)" : "var(--border)"}`,
              background: filter === f ? "var(--bg-hover)" : "var(--bg-card)",
              color: filter === f ? "var(--green-glow)" : "var(--text-muted)",
              fontFamily: "var(--font-mono)", fontSize: 11,
              cursor: "pointer", letterSpacing: 1,
              textTransform: "uppercase", transition: "all 0.2s",
            }}>
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <Loading />
      ) : (
        <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["SKU", "Product", "Stock", "Reorder Point", "Safety Stock", "Avg Daily", "Days Left", "30d Forecast", "Risk"].map(h => (
                  <th key={h} style={{
                    padding: "12px 16px", textAlign: "left",
                    fontFamily: "var(--font-mono)", fontSize: 10,
                    color: "var(--text-muted)", letterSpacing: 2,
                    fontWeight: 400, textTransform: "uppercase",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={item.sku_id}
                  style={{
                    borderBottom: "1px solid var(--border)",
                    background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
                    transition: "background 0.15s",
                    animation: `slide-in 0.3s ease ${i * 0.05}s both`,
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "var(--bg-hover)"}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)"}
                >
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--green-mid)" }}>{item.sku_id}</td>
                  <td style={{ padding: "14px 16px", fontWeight: 600, color: "var(--text-primary)", fontSize: 14 }}>{item.sku_name}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: item.current_stock <= item.reorder_point ? "var(--red)" : "var(--green-bright)" }}>
                    {item.current_stock}
                  </td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-secondary)" }}>{item.reorder_point}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-muted)" }}>{item.safety_stock}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-secondary)" }}>{item.avg_daily_demand}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: item.days_until_stockout <= 7 ? "var(--red)" : "var(--amber)" }}>
                    {item.days_until_stockout != null ? `${item.days_until_stockout}d` : "—"}
                  </td>
                  <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--blue)" }}>{item.forecast_30d}</td>
                  <td style={{ padding: "14px 16px" }}><RiskBadge level={item.stockout_risk} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", color: "var(--text-muted)", letterSpacing: 3 }}>
      SCANNING INVENTORY...
    </div>
  );
}