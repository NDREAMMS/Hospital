import { useMemo, useState } from "react";
import { ErrorAlert } from "../components/ErrorAlert";
import { CalendarMonth } from "../components/CalendarMonth";
import { ShiftCard } from "../components/ShiftCard";
import { useShifts } from "../hooks/useShifts";
import { useSelectedShift } from "../hooks/useSelectedShift";

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function dateKeyLocalFromIso(iso: string) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function dateKeyTodayLocal() {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString();
}

function statusColor(status?: string) {
  if (!status) return "rgba(255,255,255,0.7)";
  const value = status.toLowerCase();
  if (value.includes("dispon")) return "#22c55e";
  if (value.includes("affect")) return "#f97316";
  return "rgba(255,255,255,0.7)";
}

export function PlanningPage() {
  const { shifts, loading, error } = useShifts();
  const { setSelectedShift } = useSelectedShift();
  const [selectedDateKey, setSelectedDateKey] = useState(dateKeyTodayLocal());
  const [monthCursor, setMonthCursor] = useState(() => new Date());
  const [selectedShiftId, setSelectedShiftId] = useState<number | null>(null);

  const shiftsByDay = new Map<string, typeof shifts>();
  for (const shift of shifts) {
    const key = dateKeyLocalFromIso(shift.start);
    const arr = shiftsByDay.get(key) ?? [];
    arr.push(shift);
    shiftsByDay.set(key, arr);
  }

  const markedDates = new Set(shiftsByDay.keys());
  const dayShifts = shiftsByDay.get(selectedDateKey) ?? [];

  const selectedShift = useMemo(
    () => dayShifts.find((row) => row.id === selectedShiftId) ?? null,
    [dayShifts, selectedShiftId],
  );

  return (
    <>
      <h1 className="pageTitle">Planning</h1>
      {loading ? <div className="muted">Loading...</div> : null}
      {error ? <ErrorAlert error={error} /> : null}
      {!loading && !error && shifts.length === 0 ? (
        <div className="card" style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 600 }}>No shifts yet</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Start Django, create some shifts, then refresh.
          </div>
        </div>
      ) : null}

      <div className="planningLayout" style={{ marginTop: 12 }}>
        <div>
          <div className="calendarNav">
            <button
              type="button"
              className="calendarNavBtn"
              onClick={() =>
                setMonthCursor(
                  (prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1),
                )
              }
            >
              {"<-"}
            </button>
            <button
              type="button"
              className="calendarNavBtn"
              onClick={() =>
                setMonthCursor(
                  (prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1),
                )
              }
            >
              {"->"}
            </button>
            <button
              type="button"
              className="calendarNavBtn"
              onClick={() => setMonthCursor(new Date())}
            >
              Today
            </button>
          </div>

          <CalendarMonth
            month={monthCursor}
            selectedDateKey={selectedDateKey}
            markedDates={markedDates}
            onSelectDateKey={(key) => {
              setSelectedDateKey(key);
              setSelectedShiftId(null);
            }}
          />
        </div>

        <div>
          <div className="card">
            <div style={{ fontWeight: 600 }}>Selected day</div>
            <div className="muted" style={{ marginTop: 4 }}>
              {selectedDateKey}
            </div>
          </div>

          <div style={{ marginTop: 12 }} className="grid">
            {dayShifts.map((shift) => (
              <ShiftCard
                key={shift.id}
                shift={shift}
                selected={selectedShiftId === shift.id}
                onClick={() => {
                  setSelectedShiftId(shift.id);
                  setSelectedShift(shift);
                }}
              />
            ))}
          </div>

          {selectedShift ? (
            <div className="card" style={{ marginTop: 12 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  alignItems: "center",
                }}
              >
                <div style={{ fontWeight: 700 }}>{selectedShift.title}</div>
                <span
                  style={{
                    color: statusColor(selectedShift.status),
                    border: `1px solid ${statusColor(selectedShift.status)}66`,
                    background: `${statusColor(selectedShift.status)}22`,
                    borderRadius: 999,
                    padding: "3px 8px",
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {selectedShift.status ?? "Statut inconnu"}
                </span>
              </div>

              <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>
                {formatDateTime(selectedShift.start)} {"->"}{" "}
                {formatDateTime(selectedShift.end)}
              </div>

              <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                <div>
                  <strong>Service:</strong> {selectedShift.service ?? "-"} /{" "}
                  {selectedShift.unit ?? "-"}
                </div>
                <div>
                  <strong>Type de garde:</strong> {selectedShift.shiftType ?? "-"}
                </div>
                <div>
                  <strong>Affectation:</strong>{" "}
                  {(selectedShift.assignmentsCount ?? selectedShift.staffCount ?? 0)} /{" "}
                  {selectedShift.maxStaff ?? "-"} (minimum: {selectedShift.minStaff ?? "-"})
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600 }}>Affecte a</div>
                {(selectedShift.assignedStaff?.length ?? 0) === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    Personne pour le moment.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {selectedShift.assignedStaff?.map((person) => (
                      <div key={person.id} className="muted" style={{ fontSize: 13 }}>
                        - {person.fullName}
                        {person.role ? ` (${person.role})` : ""}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600 }}>Certifications requises</div>
                {(selectedShift.requiredCertifications?.length ?? 0) === 0 ? (
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    Aucune certification obligatoire.
                  </div>
                ) : (
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {selectedShift.requiredCertifications?.map((cert) => (
                      <div key={cert} className="muted" style={{ fontSize: 13 }}>
                        - {cert}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {!loading && !error && dayShifts.length === 0 ? (
            <div className="card" style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 600 }}>No shifts on this day</div>
              <div className="muted" style={{ marginTop: 6 }}>
                Pick another date on the calendar.
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}

