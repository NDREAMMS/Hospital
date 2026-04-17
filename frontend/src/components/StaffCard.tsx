import type { Staff } from "../types";

export function StaffCard({ staff }: { staff: Staff }) {
  return (
    <div className="card">
      <div style={{ fontWeight: 600 }}>{staff.fullName}</div>
      <div className="muted" style={{ fontSize: 13 }}>
        {staff.role ?? "Staff"}
      </div>
    </div>
  );
}
