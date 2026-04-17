import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const { staff, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!staff) return null;

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.1)",
          background: "rgba(255,255,255,0.05)",
          color: "white",
          cursor: "pointer",
          fontSize: 13,
        }}
      >
        <div style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: "#6366f1",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 600,
        }}>
          {staff.fullName.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)}
        </div>
        <span>{staff.fullName}</span>
      </button>

      {isOpen && (
        <div style={{
          position: "absolute",
          top: "100%",
          right: 0,
          marginTop: 8,
          minWidth: 200,
          background: "#1f2937",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 8,
          padding: 8,
          zIndex: 100,
          boxShadow: "0 10px 25px rgba(0,0,0,0.3)",
        }}>
          <div style={{
            padding: "8px 12px",
            borderBottom: "1px solid rgba(255,255,255,0.1)",
            marginBottom: 8,
          }}>
            <div style={{ fontWeight: 600 }}>{staff.fullName}</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>{staff.email}</div>
          </div>
          
          <button
            onClick={handleLogout}
            style={{
              width: "100%",
              padding: "8px 12px",
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: "#f87171",
              cursor: "pointer",
              fontSize: 13,
              textAlign: "left",
            }}
          >
            Deconnexion
          </button>
        </div>
      )}
    </div>
  );
}
