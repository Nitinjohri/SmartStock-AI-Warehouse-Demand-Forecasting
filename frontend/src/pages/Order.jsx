// src/pages/Orders.jsx
import { useEffect, useState } from "react";
import { api } from "../services/api";
import RiskBadge from "../components/cards/Riskbadge";

export default function Orders() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getOrders()
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const orders = data?.orders || [];

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", letterSpacing: 3, marginBottom: 6 }}>
          AUTO-REPLENISHMENT
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, color: "var(--green-glow)", textShadow: "0 0 24px rgba(74,222,128,0.3)" }}>
          Purchase Orders
        </h1>
      </div>

      {/* Summary row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 28 }}>
        <SummaryPill label="Total Orders"    value={data?.total_orders ?? 0}    color="var(--green-bright)" />
        <SummaryPill label="Critical"        value={data?.critical_orders ?? 0} color="var(--red)"   />
      </div>

      {loading ? <Loading /> : orders.length === 0 ? (
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: 8, padding: "48px",
          textAlign: "center", fontFamily: "var(--font-mono)",
          color: "var(--green-mid)", letterSpacing: 3, fontSize: 13,
        }}>
          ✓ ALL STOCK LEVELS HEALTHY — NO ORDERS NEEDED
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {orders.map((order, i) => (
            <OrderCard key={order.sku_id} order={order} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function OrderCard({ order, index }) {
  const [approved, setApproved] = useState(false);

  return (
    <div style={{
      background: "var(--bg-card)",
      border: `1px solid ${order.priority === "critical" ? "var(--red)" : "var(--border)"}`,
      borderRadius: 8, padding: "20px 24px",
      animation: `slide-in 0.3s ease ${index * 0.07}s both`,
      boxShadow: order.priority === "critical" ? "0 0 20px rgba(239,68,68,0.1)" : "none",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        {/* Left: product info */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
              {order.sku_name}
            </span>
            <RiskBadge level={order.priority} />
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
            {order.sku_id}
          </div>
        </div>

        {/* Right: order qty + approve */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2 }}>ORDER QTY</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 700, color: "var(--green-glow)", lineHeight: 1 }}>
              {order.order_qty}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>units</div>
          </div>
          <button
            onClick={() => setApproved(true)}
            disabled={approved}
            style={{
              padding: "10px 20px", borderRadius: 6,
              border: `1px solid ${approved ? "var(--green-dim)" : "var(--green-bright)"}`,
              background: approved ? "var(--green-dim)" : "transparent",
              color: approved ? "var(--text-muted)" : "var(--green-glow)",
              fontFamily: "var(--font-mono)", fontSize: 12,
              cursor: approved ? "default" : "pointer",
              letterSpacing: 1, transition: "all 0.2s",
              boxShadow: approved ? "none" : "0 0 12px rgba(34,197,94,0.2)",
            }}>
            {approved ? "✓ APPROVED" : "APPROVE PO"}
          </button>
        </div>
      </div>

      {/* Metrics row */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
        gap: 16, marginTop: 16,
        paddingTop: 16, borderTop: "1px solid var(--border)",
      }}>
        <Metric label="Current Stock"    value={order.current_stock}       />
        <Metric label="Reorder Point"    value={order.reorder_point}       />
        <Metric label="30d Forecast"     value={order.forecast_30d}        />
        <Metric label="Days Until Stockout" value={order.days_until_stockout != null ? `${order.days_until_stockout}d` : "—"} color={order.days_until_stockout <= 3 ? "var(--red)" : "var(--amber)"} />
      </div>
    </div>
  );
}

function Metric({ label, value, color = "var(--text-secondary)" }) {
  return (
    <div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2, marginBottom: 2 }}>{label}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, color, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function SummaryPill({ label, value, color }) {
  return (
    <div style={{
      background: "var(--bg-card)", border: `1px solid ${color}33`,
      borderRadius: 6, padding: "10px 20px",
      display: "flex", alignItems: "center", gap: 12,
    }}>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color }}>{value}</span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", letterSpacing: 1 }}>{label.toUpperCase()}</span>
    </div>
  );
}

function Loading() {
  return (
    <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", color: "var(--text-muted)", letterSpacing: 3 }}>
      GENERATING PURCHASE ORDERS...
    </div>
  );
}