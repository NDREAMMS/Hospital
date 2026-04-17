import { useEffect, useMemo, useState } from "react";
import type { ApiError } from "../types";
import { toApiError } from "../api/toApiError";
import { getMeta } from "../api/meta";
import { createStaff, deleteStaff, listStaff, updateStaff, type StaffRow } from "../api/staff";
import { ErrorAlert } from "../components/ErrorAlert";

type MetaState = {
  roles: { id: number; name: string }[];
  services: { id: number; name: string }[];
};

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "?";
  const last = parts.length > 1 ? parts[parts.length - 1]?.[0] : "";
  return (first + last).toUpperCase();
}

function roleColor(role: string | null) {
  const key = (role ?? "unknown").toLowerCase();
  if (key.includes("infirm")) return "#22c55e";
  if (key.includes("médec") || key.includes("medec")) return "#3b82f6";
  if (key.includes("aide")) return "#f97316";
  return "#a78bfa";
}

export function SoignantsPage() {
  const [rows, setRows] = useState<StaffRow[]>([]);
  const [meta, setMeta] = useState<MetaState>({ roles: [], services: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<StaffRow | null>(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    is_active: true,
    role_id: null as number | null,
    service_id: null as number | null,
  });

  const counts = useMemo(() => {
    const active = rows.filter((r) => r.is_active).length;
    return { total: rows.length, active, inactive: rows.length - active };
  }, [rows]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [staff, m] = await Promise.all([listStaff(), getMeta()]);
      setRows(staff);
      setMeta(m);
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load staff"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  function openCreate() {
    setEditing(null);
    setForm({
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      is_active: true,
      role_id: null,
      service_id: null,
    });
    setModalOpen(true);
  }

  function openEdit(row: StaffRow) {
    setEditing(row);
    const [first_name, ...rest] = row.fullName.split(" ");
    setForm({
      first_name: first_name || "",
      last_name: rest.join(" "),
      email: row.email,
      phone: row.phone ?? "",
      is_active: row.is_active,
      role_id:
        meta.roles.find((r) => r.name === row.role)?.id ?? null,
      service_id:
        meta.services.find((s) => s.name === row.service)?.id ?? null,
    });
    setModalOpen(true);
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      if (editing) {
        await updateStaff(editing.id, form);
      } else {
        await createStaff(form);
      }
      setModalOpen(false);
      setEditing(null);
      await refresh();
    } catch (caught: unknown) {
      setError(toApiError(caught, "Save failed"));
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: number) {
    if (!window.confirm("Supprimer ce soignant ?")) return;
    setLoading(true);
    setError(null);
    try {
      await deleteStaff(id);
      await refresh();
    } catch (caught: unknown) {
      setError(toApiError(caught, "Delete failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="pageTitle">Soignants</h1>
      {error ? <ErrorAlert error={error} /> : null}

      <div className="grid" style={{ marginBottom: 12 }}>
        <div className="card">
          <div style={{ fontWeight: 700 }}>Total</div>
          <div className="muted">{counts.total}</div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700 }}>Actifs</div>
          <div className="muted">{counts.active}</div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700 }}>Inactifs</div>
          <div className="muted">{counts.inactive}</div>
        </div>
        <div className="card" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button className="calendarNavBtn" type="button" onClick={openCreate}>
            + Ajouter
          </button>
          <button className="calendarNavBtn" type="button" onClick={refresh} disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr className="muted" style={{ textAlign: "left", fontSize: 12 }}>
              <th style={{ padding: "10px 8px" }}>Soignant</th>
              <th style={{ padding: "10px 8px" }}>Rôle</th>
              <th style={{ padding: "10px 8px" }}>Service</th>
              <th style={{ padding: "10px 8px" }}>Statut</th>
              <th style={{ padding: "10px 8px" }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                <td style={{ padding: "10px 8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: 999,
                        display: "grid",
                        placeItems: "center",
                        background: "rgba(255,255,255,0.06)",
                        border: `1px solid ${roleColor(r.role)}55`,
                        color: roleColor(r.role),
                        fontWeight: 700,
                        fontSize: 12,
                      }}
                    >
                      {initials(r.fullName)}
                    </div>
                    <div>
                      <div style={{ fontWeight: 650 }}>{r.fullName}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {r.email}
                      </div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: "10px 8px" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: 999,
                      background: `${roleColor(r.role)}22`,
                      border: `1px solid ${roleColor(r.role)}55`,
                      color: roleColor(r.role),
                      fontSize: 12,
                      fontWeight: 650,
                    }}
                  >
                    {r.role ?? "—"}
                  </span>
                </td>
                <td style={{ padding: "10px 8px" }}>{r.service ?? "—"}</td>
                <td style={{ padding: "10px 8px" }}>
                  <span className="muted">{r.status}</span>
                </td>
                <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>
                  <button className="calendarNavBtn" type="button" onClick={() => openEdit(r)}>
                    Modifier
                  </button>{" "}
                  <button className="calendarNavBtn" type="button" onClick={() => remove(r.id)}>
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={5} style={{ padding: 12 }} className="muted">
                  Aucun soignant.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {modalOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "grid",
            placeItems: "center",
            padding: 16,
          }}
          onClick={() => {
            setModalOpen(false);
            setEditing(null);
          }}
        >
          <div className="card" style={{ width: "min(720px, 100%)" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
              <div style={{ fontWeight: 800 }}>{editing ? "Modifier soignant" : "Ajouter soignant"}</div>
              <button
                className="calendarNavBtn"
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setEditing(null);
                }}
              >
                Fermer
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Prénom</span>
                <input
                  value={form.first_name}
                  onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))}
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Nom</span>
                <input
                  value={form.last_name}
                  onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))}
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Email</span>
                <input
                  value={form.email}
                  onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Téléphone</span>
                <input
                  value={form.phone}
                  onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Rôle</span>
                <select
                  value={form.role_id ?? ""}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      role_id: e.target.value ? Number(e.target.value) : null,
                    }))
                  }
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                >
                  <option value="">—</option>
                  {meta.roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span className="muted">Service</span>
                <select
                  value={form.service_id ?? ""}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      service_id: e.target.value ? Number(e.target.value) : null,
                    }))
                  }
                  style={{ padding: 10, borderRadius: 10, border: "1px solid #253047" }}
                >
                  <option value="">—</option>
                  {meta.services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
                />
                <span>Actif</span>
              </label>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
              <button
                className="calendarNavBtn"
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setEditing(null);
                }}
              >
                Annuler
              </button>
              <button className="calendarNavBtn" type="button" onClick={submit} disabled={loading}>
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
