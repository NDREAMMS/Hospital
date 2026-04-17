import { ErrorAlert } from "../components/ErrorAlert";
import { useAbsences } from "../hooks/useAbsences";

export function AbsencesPage() {
  const { absences, loading, error } = useAbsences();

  return (
    <>
      <h1 className="pageTitle">Absences</h1>
      {loading ? <div className="muted">Loading…</div> : null}
      {error ? <ErrorAlert error={error} /> : null}
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 600 }}>Total</div>
        <div className="muted">{absences.length}</div>
      </div>
    </>
  );
}
