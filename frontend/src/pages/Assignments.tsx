import { ErrorAlert } from "../components/ErrorAlert";
import { useAssignments } from "../hooks/useAssignments";

export function AssignmentsPage() {
  const { assignments, loading, error } = useAssignments();

  return (
    <>
      <h1 className="pageTitle">Assignments</h1>
      {loading ? <div className="muted">Loading…</div> : null}
      {error ? <ErrorAlert error={error} /> : null}
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 600 }}>Total</div>
        <div className="muted">{assignments.length}</div>
      </div>
    </>
  );
}
