import { useEffect, useMemo, useState } from "react";
import { getMeta } from "../api/meta";
import { listPostes, type Poste } from "../api/postes";
import { toApiError } from "../api/toApiError";
import type { ApiError } from "../types";
import { ErrorAlert } from "../components/ErrorAlert";
import { DATA_CHANGED_EVENT } from "../lib/dataEvents";

function badgeColor(label: string) {
  const key = label.toLowerCase();
  if (key.includes("nuit")) return "#a78bfa";
  if (key.includes("jour") || key.includes("day")) return "#22c55e";
  if (key.includes("astre")) return "#f97316";
  return "#60a5fa";
}

function statusColor(status: Poste["status"]) {
  return status === "Disponible" ? "#22c55e" : "#f97316";
}

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString();
}

export function PostesPage() {
  const [postes, setPostes] = useState<Poste[]>([]);
  const [services, setServices] = useState<string[]>([]);
  const [serviceFilter, setServiceFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [p, meta] = await Promise.all([listPostes(), getMeta()]);
      setPostes(p);
      setServices(meta.services.map((s) => s.name));
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load postes"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    const handler = () => void refresh();
    window.addEventListener(DATA_CHANGED_EVENT, handler);
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handler);
  }, []);

  const filtered = useMemo(() => {
    if (!serviceFilter) return postes;
    return postes.filter((p) => p.service === serviceFilter);
  }, [postes, serviceFilter]);

  return (
    <>
      <h1 className="pageTitle">Postes</h1>
      {error ? <ErrorAlert error={error} /> : null}

      <div className="card" style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <div className="muted" style={{ fontSize: 13 }}>
          Filtrer par service
        </div>
        <select
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
        >
          <option value="">Tous</option>
          {services.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <button className="calendarNavBtn" type="button" onClick={refresh} disabled={loading}>
          Rafraîchir
        </button>
        {loading ? <div className="muted">Loading…</div> : null}
      </div>

      <div style={{ marginTop: 12 }} className="card">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr className="muted" style={{ textAlign: "left", fontSize: 12 }}>
              <th style={{ padding: "10px 8px" }}>Service</th>
              <th style={{ padding: "10px 8px" }}>Unité</th>
              <th style={{ padding: "10px 8px" }}>Type</th>
              <th style={{ padding: "10px 8px" }}>Date</th>
              <th style={{ padding: "10px 8px" }}>Statut</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                <td style={{ padding: "10px 8px" }}>{p.service}</td>
                <td style={{ padding: "10px 8px" }}>{p.unit}</td>
                <td style={{ padding: "10px 8px" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: 999,
                      background: `${badgeColor(p.shiftType)}22`,
                      border: `1px solid ${badgeColor(p.shiftType)}55`,
                      color: badgeColor(p.shiftType),
                      fontSize: 12,
                      fontWeight: 650,
                    }}
                  >
                    {p.shiftType}
                  </span>
                </td>
                <td style={{ padding: "10px 8px" }} className="muted">
                  {fmt(p.start)} → {fmt(p.end)}
                </td>
                <td style={{ padding: "10px 8px" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: 999,
                      background: `${statusColor(p.status)}22`,
                      border: `1px solid ${statusColor(p.status)}55`,
                      color: statusColor(p.status),
                      fontSize: 12,
                      fontWeight: 650,
                    }}
                  >
                    {p.status}
                  </span>{" "}
                  <span className="muted" style={{ fontSize: 12 }}>
                    ({p.assignmentsCount})
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && !loading ? (
              <tr>
                <td colSpan={5} style={{ padding: 12 }} className="muted">
                  Aucun poste.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </>
  );
}

