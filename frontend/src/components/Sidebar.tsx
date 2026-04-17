import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";

const linkStyle: CSSProperties = {
  display: "block",
  padding: "10px 12px",
  borderRadius: 10,
  textDecoration: "none",
  color: "rgba(255,255,255,0.85)",
};

export function Sidebar() {
  return (
    <aside
      style={{
        padding: 16,
        borderRight: "1px solid rgba(255,255,255,0.08)",
        background: "#0b1220",
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 14 }}>Hospital</div>
      <nav style={{ display: "grid", gap: 6 }}>
        <NavLink
          to="/"
          end
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/soignants"
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Soignants
        </NavLink>
        <NavLink
          to="/postes"
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Postes
        </NavLink>
        <NavLink
          to="/affectation"
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Affectation
        </NavLink>
        <NavLink
          to="/planning"
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Planning
        </NavLink>
        <NavLink
          to="/generator"
          style={({ isActive }) => ({
            ...linkStyle,
            background: isActive ? "rgba(99,102,241,0.16)" : "transparent",
          })}
        >
          Generateur
        </NavLink>
      </nav>
    </aside>
  );
}
