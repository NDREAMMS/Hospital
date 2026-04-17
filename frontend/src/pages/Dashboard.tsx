import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { getMeta } from "../api/meta";

interface ServiceStat {
  id: number;
  name: string;
  bed_capacity: number;
  total_shifts: number;
  min_staff_needed: number;
  current_staff: number;
  shortage: number;
  uncovered_shifts: number;
}

export function DashboardPage() {
  const location = useLocation();
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalShifts: 0,
    coveredShifts: 0,
    uncoveredShifts: 0,
    totalStaff: 0,
    coverage: 0,
  });

  const fetchData = () => {
    setLoading(true);
    getMeta()
      .then(async (meta) => {
        setServices(meta.services || []);
        
        const today = new Date();
        const monday = new Date(today);
        monday.setDate(today.getDate() - today.getDay() + 1);
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        
        const formatDate = (d: Date) => d.toISOString().split("T")[0];
        
        try {
          const response = await fetch(`/api/plannings/preview/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              period_start: formatDate(monday),
              period_end: formatDate(sunday),
            }),
          });
          const data = await response.json();
          
          const totalShifts = data.total_shifts || 0;
          const coveredShifts = data.already_covered || 0;
          const uncoveredShifts = data.needs_coverage || 0;
          const serviceStats: ServiceStat[] = data.service_stats || [];
          
          setStats({
            totalShifts,
            coveredShifts,
            uncoveredShifts,
            totalStaff: serviceStats.reduce((sum: number, s: ServiceStat) => sum + s.current_staff, 0),
            coverage: totalShifts > 0 ? Math.round((coveredShifts / totalShifts) * 100) : 100,
          });
        } catch (e) {
          console.error("Error fetching preview:", e);
        }
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchData();
  }, [location.key]);

  return (
    <>
      <h1 className="pageTitle">Tableau de Bord</h1>
      
      {loading ? (
        <div className="muted">Chargement...</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
            <div className="card" style={{ padding: 16, background: "#eff6ff", textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#2563eb" }}>{stats.totalShifts}</div>
              <div style={{ fontSize: 12, color: "#1e40af" }}>Creneaux semaine</div>
            </div>
            <div className="card" style={{ padding: 16, background: "#dcfce7", textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#16a34a" }}>{stats.coveredShifts}</div>
              <div style={{ fontSize: 12, color: "#166534" }}>Couverts</div>
            </div>
            <div className="card" style={{ padding: 16, background: "#fee2e2", textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#dc2626" }}>{stats.uncoveredShifts}</div>
              <div style={{ fontSize: 12, color: "#991b1b" }}>Sous-effectif</div>
            </div>
            <div className="card" style={{ padding: 16, background: stats.coverage >= 80 ? "#dcfce7" : "#fef3c7", textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: stats.coverage >= 80 ? "#16a34a" : "#d97706" }}>{stats.coverage}%</div>
              <div style={{ fontSize: 12, color: stats.coverage >= 80 ? "#166534" : "#92400e" }}>Couverture</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Actions rapides</div>
              <div style={{ display: "grid", gap: 8 }}>
                <Link to="/generator" className="btn btn-primary" style={{ textAlign: "center", textDecoration: "none" }}>
                  Generer Planning
                </Link>
                <Link to="/planning" className="btn btn-secondary" style={{ textAlign: "center", textDecoration: "none" }}>
                  Voir Planning
                </Link>
                <Link to="/affectation" className="btn btn-secondary" style={{ textAlign: "center", textDecoration: "none" }}>
                  Affectations
                </Link>
              </div>
            </div>

            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14, color: "#2563eb" }}>Services ({services.length})</div>
              <div style={{ maxHeight: 200, overflow: "auto" }}>
                {services.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13 }}>Aucun service configure</div>
                ) : (
                  <div style={{ display: "grid", gap: 4 }}>
                    {services.slice(0, 8).map((service) => (
                      <div key={service.id} style={{ 
                        padding: "6px 8px", 
                        background: "#f3f4f6", 
                        borderRadius: 4,
                        fontSize: 13,
                        display: "flex",
                        justifyContent: "space-between"
                      }}>
                        <span style={{ color: "#1d4ed8" }}>{service.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Statut de la semaine</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ flex: 1, height: 20, background: "#e5e7eb", borderRadius: 10, overflow: "hidden" }}>
                <div style={{ 
                  width: `${stats.coverage}%`, 
                  height: "100%", 
                  background: stats.coverage >= 80 ? "#22c55e" : stats.coverage >= 50 ? "#eab308" : "#ef4444",
                  transition: "width 0.3s"
                }} />
              </div>
              <span style={{ fontWeight: 600, minWidth: 50 }}>{stats.coverage}%</span>
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              {stats.coverage >= 80 ? "Bonne couverture" : stats.coverage >= 50 ? "Couverture insuffisante" : "Sous-effectif critique"}
            </div>
          </div>
        </>
      )}
    </>
  );
}
