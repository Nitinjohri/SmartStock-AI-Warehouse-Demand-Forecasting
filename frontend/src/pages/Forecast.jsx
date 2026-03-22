// src/pages/Forecast.jsx
import { useEffect, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api } from "../services/api";

export default function Forecast() {
  const [skus, setSkus]           = useState([]);
  const [selected, setSelected]   = useState(null);
  const [forecast, setForecast]   = useState(null);
  const [horizon, setHorizon]     = useState(30);
  const [loading, setLoading]     = useState(false);

  useEffect(() => {
    api.getSkus().then(r => {
      setSkus(r.data);
      if (r.data.length > 0) setSelected(r.data[0].sku_id);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    api.getForecastSku(selected, horizon)
      .then(r => { setForecast(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selected, horizon]);

  const chartData = forecast?.forecast?.map(p => ({
    date:  p.date.slice(5),   // MM-DD
    yhat:  Math.round(p.yhat),
    lower: Math.round(p.yhat_lower),
    upper: Math.round(p.yhat_upper),
  })) || [];

  return (
    <div style={{ padding: "32px 36px" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", letterSpacing: 3, marginBottom: 6 }}>
          DEMAND INTELLIGENCE
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, color: "var(--green-glow)", textShadow: "0 0 24px rgba(74,222,128,0.3)" }}>
          Forecast Engine
        </h1>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: 16, marginBottom: 28, alignItems: "center" }}>
        {/* SKU selector */}
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2, marginBottom: 6 }}>SELECT SKU</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {skus.map(s => (
              <button key={s.sku_id} onClick={() => setSelected(s.sku_id)}
                style={{
                  padding: "6px 14px",
                  borderRadius: 4,
                  border: `1px solid ${selected === s.sku_id ? "var(--green-bright)" : "var(--border)"}`,
                  background: selected === s.sku_id ? "var(--bg-hover)" : "var(--bg-card)",
                  color: selected === s.sku_id ? "var(--green-glow)" : "var(--text-secondary)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}>
                {s.sku_id}
              </button>
            ))}
          </div>
        </div>

        {/* Horizon selector */}
        <div style={{ marginLeft: "auto" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2, marginBottom: 6 }}>HORIZON</div>
          <div style={{ display: "flex", gap: 8 }}>
            {[7, 14, 30, 60].map(h => (
              <button key={h} onClick={() => setHorizon(h)}
                style={{
                  padding: "6px 14px", borderRadius: 4,
                  border: `1px solid ${horizon === h ? "var(--green-bright)" : "var(--border)"}`,
                  background: horizon === h ? "var(--bg-hover)" : "var(--bg-card)",
                  color: horizon === h ? "var(--green-glow)" : "var(--text-secondary)",
                  fontFamily: "var(--font-mono)", fontSize: 12,
                  cursor: "pointer", transition: "all 0.2s",
                }}>
                {h}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Forecast card */}
      {forecast && (
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: 8, padding: "24px",
          animation: "slide-in 0.4s ease forwards",
        }}>
          {/* SKU info */}
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24, alignItems: "flex-start" }}>
            <div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "var(--green-glow)" }}>
                {forecast.sku_name}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                {forecast.sku_id} · {horizon}-day forecast · model: ensemble
              </div>
            </div>
            {forecast.mape != null && (
              <div style={{
                background: "var(--bg-hover)", border: "1px solid var(--border)",
                borderRadius: 6, padding: "8px 16px", textAlign: "center",
              }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", letterSpacing: 2 }}>MAPE</div>
                <div style={{
                  fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 700,
                  color: forecast.mape < 15 ? "var(--green-bright)" : forecast.mape < 25 ? "var(--amber)" : "var(--red)",
                }}>
                  {forecast.mape}%
                </div>
              </div>
            )}
          </div>

          {/* Chart */}
          {loading ? (
            <div style={{ height: 320, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", color: "var(--text-muted)", letterSpacing: 3 }}>
              COMPUTING FORECAST...
            </div>
          ) : (
            chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="gradUpper" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02}/>
                    </linearGradient>
                    <linearGradient id="gradMain" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#0f4a2422" vertical={false}/>
                  <XAxis dataKey="date" tick={{ fill: "#2d7a4a", fontFamily: "var(--font-mono)", fontSize: 10 }} axisLine={false} tickLine={false} interval={Math.floor(chartData.length / 6)}/>
                  <YAxis tick={{ fill: "#2d7a4a", fontFamily: "var(--font-mono)", fontSize: 10 }} axisLine={false} tickLine={false} width={40}/>
                  <Tooltip
                    contentStyle={{ background: "#0a2214", border: "1px solid #0f4a24", borderRadius: 6, fontFamily: "var(--font-mono)", fontSize: 12 }}
                    labelStyle={{ color: "#6ee7a0" }}
                    itemStyle={{ color: "#22c55e" }}
                  />
                  <Area type="monotone" dataKey="upper" stroke="none" fill="url(#gradUpper)" name="Upper bound"/>
                  <Area type="monotone" dataKey="yhat"  stroke="#22c55e" strokeWidth={2} fill="url(#gradMain)" name="Forecast" dot={false}/>
                  <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg-card)" name="Lower bound"/>
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ 
                height: 320, 
                display: "flex", 
                flexDirection: "column",
                alignItems: "center", 
                justifyContent: "center", 
                fontFamily: "var(--font-mono)", 
                color: "var(--text-muted)", 
                background: "rgba(15, 74, 36, 0.05)", 
                borderRadius: 8,
                border: "1px dashed var(--border)"
              }}>
                <div style={{ fontSize: 14, letterSpacing: 2, marginBottom: 8 }}>NO FORECAST DATA</div>
                <div style={{ fontSize: 10, opacity: 0.6 }}>This SKU hasn't been trained in the current ML run.</div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}