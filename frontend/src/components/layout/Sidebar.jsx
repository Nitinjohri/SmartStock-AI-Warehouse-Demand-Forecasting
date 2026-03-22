import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import { api } from "../../services/api";

const links = [
  { to: "/",          icon: "◈", label: "Overview"   },
  { to: "/forecast",  icon: "◎", label: "Forecast"   },
  { to: "/inventory", icon: "▦", label: "Inventory"  },
  { to: "/orders",    icon: "◉", label: "Orders"     },
];

export default function Sidebar() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    const checkHealth = () => {
      api.health()
        .then(() => setIsOnline(true))
        .catch(() => setIsOnline(false));
    };

    checkHealth(); // Initial check
    const timer = setInterval(checkHealth, 10000);
    return () => clearInterval(timer);
  }, []);

  return (
    <aside style={{
      width: 220, minHeight: "100vh",
      background: "var(--bg-panel)",
      borderRight: "1px solid var(--border)",
      display: "flex", flexDirection: "column",
      position: "fixed", top: 0, left: 0, bottom: 0,
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{
        padding: "28px 24px 20px",
        borderBottom: "1px solid var(--border)",
      }}>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--green-mid)",
          letterSpacing: 3,
          marginBottom: 4,
        }}>SYSTEM ONLINE</div>
        <div style={{
          fontFamily: "var(--font-display)",
          fontSize: 22,
          fontWeight: 700,
          color: "var(--green-bright)",
          letterSpacing: 1,
        }}>SmartStock</div>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: "var(--text-muted)",
          letterSpacing: 2,
        }}>AI · WAREHOUSE · v1.0</div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "16px 12px", flex: 1 }}>
        {links.map(({ to, icon, label }) => (
          <NavLink key={to} to={to} end={to === "/"}
            style={({ isActive }) => ({
              display: "flex", alignItems: "center", gap: 12,
              padding: "11px 14px",
              marginBottom: 4,
              borderRadius: 6,
              textDecoration: "none",
              fontFamily: "var(--font-display)",
              fontWeight: 600,
              fontSize: 15,
              letterSpacing: 1,
              background: isActive ? "var(--bg-hover)" : "transparent",
              color: isActive ? "var(--green-glow)" : "var(--text-secondary)",
              borderLeft: isActive ? "2px solid var(--green-bright)" : "2px solid transparent",
              transition: "all 0.2s",
            })}>
            <span style={{ fontSize: 16 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status indicator */}
      <div style={{
        padding: "16px 24px",
        borderTop: "1px solid var(--border)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
      }}>
        <div style={{ 
          display: "flex", 
          alignItems: "center", 
          gap: 8, 
          color: isOnline ? "var(--green-bright)" : "var(--red)" 
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: isOnline ? "var(--green-bright)" : "var(--red)",
            animation: "pulse-glow 2s infinite",
            display: "inline-block",
          }}/>
          {isOnline ? "API CONNECTED" : "API DISCONNECTED"}
        </div>
        <div style={{ color: "var(--text-muted)", marginTop: 4 }}>
          {process.env.REACT_APP_API_URL || "localhost:8000"}
        </div>
      </div>
    </aside>
  );
}