import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { checkAffectation, createAffectation } from "../api/affectations";
import { listPostes, type Poste } from "../api/postes";
import { getStaffProfile, listStaff, type StaffProfile, type StaffRow } from "../api/staff";
import { ErrorAlert } from "../components/ErrorAlert";
import { dispatchDataChanged } from "../lib/dataEvents";
import { toApiError } from "../api/toApiError";
import type { ApiError } from "../types";

type Eligibility = {
  eligible: boolean;
  reasons: string[];
  requiredCertifications: string[];
  missingCertifications: string[];
  expiredCertifications: string[];
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString();
}

function fmtDate(iso: string | null) {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString();
}

export function AffectationPage() {
  const [staff, setStaff] = useState<StaffRow[]>([]);
  const [postes, setPostes] = useState<Poste[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<number | "">("");
  const [selectedPosteId, setSelectedPosteId] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [staffProfile, setStaffProfile] = useState<StaffProfile | null>(null);
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [s, p] = await Promise.all([listStaff(), listPostes()]);
      setStaff(s.filter((row) => row.is_active));
      setPostes(p.filter((row) => row.status === "Disponible"));
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load data"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!selectedStaffId) {
      setStaffProfile(null);
      return;
    }
    void (async () => {
      try {
        const profile = await getStaffProfile(selectedStaffId);
        setStaffProfile(profile);
      } catch (caught: unknown) {
        setError(toApiError(caught, "Failed to load staff profile"));
      }
    })();
  }, [selectedStaffId]);

  useEffect(() => {
    if (!selectedStaffId || !selectedPosteId) {
      setEligibility(null);
      return;
    }
    setChecking(true);
    void (async () => {
      try {
        const result = await checkAffectation({
          staff_id: selectedStaffId,
          shift_id: selectedPosteId,
        });
        setEligibility(result);
      } catch (caught: unknown) {
        setError(toApiError(caught, "Failed to check constraints"));
      } finally {
        setChecking(false);
      }
    })();
  }, [selectedStaffId, selectedPosteId]);

  const staffSelected = useMemo(
    () => staff.find((row) => row.id === selectedStaffId) ?? null,
    [staff, selectedStaffId],
  );
  const posteSelected = useMemo(
    () => postes.find((row) => row.id === selectedPosteId) ?? null,
    [postes, selectedPosteId],
  );

  const canAssign =
    !!selectedStaffId && !!selectedPosteId && !checking && (eligibility?.eligible ?? true);

  return (
    <>
      <h1 className="pageTitle">Affectation</h1>
      {error ? <ErrorAlert error={error} /> : null}
      {success ? (
        <div
          style={{
            border: "1px solid rgba(16, 185, 129, 0.4)",
            background: "rgba(16, 185, 129, 0.12)",
            padding: 12,
            borderRadius: 10,
            marginTop: 12,
          }}
        >
          {success}
        </div>
      ) : null}

      <div className="planningLayout" style={{ marginTop: 12 }}>
        <div className="card">
          <div style={{ fontWeight: 800, marginBottom: 10 }}>Choisir le soignant</div>
          <select
            value={selectedStaffId}
            onChange={(event) => {
              setSelectedStaffId(event.target.value ? Number(event.target.value) : "");
              setError(null);
              setSuccess(null);
              setEligibility(null);
            }}
            style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #253047" }}
          >
            <option value="">-- Soignants actifs --</option>
            {staff.map((row) => (
              <option key={row.id} value={row.id}>
                {row.fullName} ({row.role ?? "-"})
              </option>
            ))}
          </select>

          {staffSelected ? (
            <div className="card" style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 700 }}>{staffSelected.fullName}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                Role: {staffSelected.role ?? "-"}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                Service: {staffSelected.service ?? "-"}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                Email: {staffSelected.email}
              </div>
            </div>
          ) : null}

          {staffProfile ? (
            <>
              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>Certifications du soignant</div>
                {staffProfile.certifications.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                    Aucune certification enregistree.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {staffProfile.certifications.map((cert) => {
                      const expired =
                        cert.expirationDate && new Date(cert.expirationDate) < new Date();
                      return (
                        <div key={`${cert.name}-${cert.obtainedDate}`} className="muted" style={{ fontSize: 13 }}>
                          - {cert.name} (obt: {fmtDate(cert.obtainedDate)}, exp: {fmtDate(cert.expirationDate)})
                          {expired ? " [expiree]" : ""}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>Historique recent</div>
                {staffProfile.shiftHistory.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                    Aucun shift dans l'historique.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {staffProfile.shiftHistory.slice(0, 8).map((row) => (
                      <div key={row.assignmentId} className="muted" style={{ fontSize: 13 }}>
                        - {row.service}/{row.unit} {row.shiftType} ({fmt(row.start)}{" -> "}
                        {fmt(row.end)})
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>Contrats</div>
                {staffProfile.contracts.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                    Aucun contrat enregistre.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {staffProfile.contracts.map((contract) => (
                      <div
                        key={`${contract.type}-${contract.startDate}`}
                        className="muted"
                        style={{ fontSize: 13 }}
                      >
                        - {contract.type} ({fmtDate(contract.startDate)} au{" "}
                        {fmtDate(contract.endDate)}) • {contract.workloadPercent}% • max{" "}
                        {contract.maxHoursPerWeek}h/sem • nuit{" "}
                        {contract.nightShiftAllowed ? "autorisee" : "interdite"}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>Absences</div>
                {staffProfile.absences.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                    Aucune absence recente.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {staffProfile.absences.map((absence, index) => (
                      <div
                        key={`${absence.type}-${absence.startDate}-${index}`}
                        className="muted"
                        style={{ fontSize: 13 }}
                      >
                        - {absence.type} ({fmtDate(absence.startDate)} au{" "}
                        {fmtDate(absence.actualEndDate ?? absence.expectedEndDate)})
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>Contraintes visibles</div>
                {staffProfile.constraints.hardPreferences.length === 0 &&
                staffProfile.constraints.globalRules.length === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                    Aucune contrainte explicite.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {staffProfile.constraints.hardPreferences.map((item, index) => (
                      <div key={`pref-${index}`} className="muted" style={{ fontSize: 13 }}>
                        - Preference dure: {item}
                      </div>
                    ))}
                    {staffProfile.constraints.globalRules.map((rule, index) => (
                      <div
                        key={`rule-${rule.rule_type}-${index}`}
                        className="muted"
                        style={{ fontSize: 13 }}
                      >
                        - Regle: {rule.rule_type} = {rule.value} {rule.unit}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        <div className="card">
          <div style={{ fontWeight: 800, marginBottom: 10 }}>Choisir le poste</div>
          <select
            value={selectedPosteId}
            onChange={(event) => {
              setSelectedPosteId(event.target.value ? Number(event.target.value) : "");
              setError(null);
              setSuccess(null);
              setEligibility(null);
            }}
            style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #253047" }}
          >
            <option value="">-- Postes disponibles --</option>
            {postes.map((row) => (
              <option key={row.id} value={row.id}>
                {row.service} / {row.unit} - {row.shiftType} ({fmt(row.start)})
              </option>
            ))}
          </select>

          {posteSelected ? (
            <div className="card" style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 700 }}>
                {posteSelected.service} / {posteSelected.unit}
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                Type: {posteSelected.shiftType}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                {fmt(posteSelected.start)}
                {" -> "}
                {fmt(posteSelected.end)}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                Statut: {posteSelected.status}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                Staffing: {posteSelected.assignmentsCount}/{posteSelected.maxStaff ?? "-"} (min{" "}
                {posteSelected.minStaff ?? "-"})
              </div>

              <div style={{ marginTop: 8 }}>
                <div style={{ fontWeight: 600 }}>Certifications requises</div>
                {(posteSelected.requiredCertifications?.length ?? 0) === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    Aucune
                  </div>
                ) : (
                  <div style={{ marginTop: 4, display: "grid", gap: 3 }}>
                    {posteSelected.requiredCertifications?.map((cert) => (
                      <div key={cert} className="muted" style={{ fontSize: 13 }}>
                        - {cert}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {checking ? <div className="muted" style={{ marginTop: 12 }}>Verification des contraintes...</div> : null}
          {eligibility ? (
            <div
              className="card"
              style={{
                marginTop: 12,
                borderColor: eligibility.eligible
                  ? "rgba(16,185,129,0.45)"
                  : "rgba(239,68,68,0.45)",
                background: eligibility.eligible
                  ? "rgba(16,185,129,0.10)"
                  : "rgba(239,68,68,0.10)",
              }}
            >
              <div style={{ fontWeight: 700 }}>
                {eligibility.eligible ? "Affectation possible" : "Affectation bloquee"}
              </div>
              {!eligibility.eligible ? (
                <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                  {eligibility.reasons.map((reason, index) => (
                    <div key={`${index}-${reason}`} className="muted" style={{ fontSize: 13 }}>
                      - {reason}
                    </div>
                  ))}
                </div>
              ) : null}
              {(eligibility.missingCertifications.length > 0 ||
                eligibility.expiredCertifications.length > 0) ? (
                <div style={{ marginTop: 8 }}>
                  {eligibility.missingCertifications.length > 0 ? (
                    <div className="muted" style={{ fontSize: 13 }}>
                      Missing certs: {eligibility.missingCertifications.join(", ")}
                    </div>
                  ) : null}
                  {eligibility.expiredCertifications.length > 0 ? (
                    <div className="muted" style={{ fontSize: 13 }}>
                      Expired certs: {eligibility.expiredCertifications.join(", ")}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
            <button className="calendarNavBtn" type="button" onClick={refresh} disabled={loading}>
              Rafraichir
            </button>
            <button
              className="calendarNavBtn"
              type="button"
              disabled={loading || !canAssign}
              onClick={async () => {
                if (!selectedStaffId || !selectedPosteId) return;
                setLoading(true);
                setError(null);
                setSuccess(null);
                try {
                  await createAffectation({ staff_id: selectedStaffId, shift_id: selectedPosteId });
                  setSuccess("Affectation creee. Le poste est maintenant affecte.");
                  dispatchDataChanged();
                  await refresh();
                  setSelectedPosteId("");
                  setEligibility(null);
                } catch (caught: unknown) {
                  if (axios.isAxiosError(caught) && caught.response?.status === 400) {
                    const detail =
                      typeof caught.response.data?.detail === "string"
                        ? caught.response.data.detail
                        : null;
                    setError({
                      message: "Ce creneau ne peut pas etre selectionne pour ce soignant.",
                      status: 400,
                      details: detail ?? caught.response?.data,
                    });
                  } else {
                    setError(toApiError(caught, "Contrainte dure violee"));
                  }
                } finally {
                  setLoading(false);
                }
              }}
            >
              Affecter
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
