import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const from = (location.state as any)?.from?.pathname || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "64px auto", padding: 16 }}>
      <h1 className="pageTitle" style={{ textAlign: "center", marginBottom: 32 }}>Connexion</h1>
      
      <div className="card">
        <form onSubmit={handleSubmit}>
          {error && (
            <div style={{
              padding: 12,
              marginBottom: 16,
              borderRadius: 8,
              background: "#fee2e2",
              color: "#dc2626",
              fontSize: 13,
            }}>
              {error}
            </div>
          )}
          
          <label style={{ display: "grid", gap: 6, marginBottom: 16 }}>
            <span className="muted">Nom d'utilisateur</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{ 
                padding: 10, 
                borderRadius: 10, 
                border: "1px solid #374151",
                background: "#1f2937",
                color: "white",
                fontSize: 14,
              }}
            />
          </label>
          
          <label style={{ display: "grid", gap: 6, marginBottom: 20 }}>
            <span className="muted">Mot de passe</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ 
                padding: 10, 
                borderRadius: 10, 
                border: "1px solid #374151",
                background: "#1f2937",
                color: "white",
                fontSize: 14,
              }}
            />
          </label>
          
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: 10,
              border: "none",
              background: loading ? "#6366f1" : "#818cf8",
              color: "white",
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
      
      <div className="muted" style={{ marginTop: 16, textAlign: "center", fontSize: 13 }}>
        <Link to="/" style={{ color: "#818cf8" }}>Retour au tableau de bord</Link>
      </div>
    </div>
  );
}
