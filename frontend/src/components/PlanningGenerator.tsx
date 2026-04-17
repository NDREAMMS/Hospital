import { useState } from "react";
import {
  generatePlanning,
  previewPlanning,
} from "../api/planning";
import type {
  PlanningGenerateRequest,
  PlanningPreviewResponse,
  PenaltyBreakdown,
} from "../api/planning";

interface PlanningGeneratorProps {
  services: Array<{ id: number; name: string }>;
  onGenerationComplete?: () => void;
}

interface PenaltyDisplayProps {
  breakdown: PenaltyBreakdown;
  score: number;
}

function PenaltyDisplay({ breakdown, score }: PenaltyDisplayProps) {
  const items = [
    { key: "consecutive_nights", label: "Nuites consecutives", value: breakdown.consecutive_nights },
    { key: "preference_violation", label: "Preferences violees", value: breakdown.preference_violation },
    { key: "workload_imbalance", label: "Desequilibre charge", value: breakdown.workload_imbalance },
    { key: "service_change", label: "Changements service", value: breakdown.service_change },
    { key: "weekend_ratio", label: "Ratio week-end", value: breakdown.weekend_ratio },
    { key: "new_service_without_adaptation", label: "Service sans adaptation", value: breakdown.new_service_without_adaptation },
    { key: "lack_of_continuity", label: "Manque continuite", value: breakdown.lack_of_continuity },
  ];

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        Score global: <span style={{ color: score > 0 ? "#f97316" : "#22c55e" }}>{score.toFixed(2)}</span>
      </div>
      <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
        {items.map((item) => (
          <div key={item.key} style={{ display: "flex", justifyContent: "space-between" }}>
            <span className="muted">{item.label}</span>
            <span style={{ fontWeight: item.value > 0 ? 600 : 400, color: item.value > 0 ? "#f97316" : "#22c55e" }}>
              {item.value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PlanningGenerator({ services, onGenerationComplete }: PlanningGeneratorProps) {
  const today = new Date();
  const nextWeek = new Date(today);
  nextWeek.setDate(today.getDate() + 7);

  const formatDate = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [periodStart, setPeriodStart] = useState(formatDate(today));
  const [periodEnd, setPeriodEnd] = useState(formatDate(nextWeek));
  const [selectedServices, setSelectedServices] = useState<number[]>([]);
  const [useOptimization, setUseOptimization] = useState(true);
  const [maxIterations, setMaxIterations] = useState(100);

  const [preview, setPreview] = useState<PlanningPreviewResponse | null>(null);
  const [result, setResult] = useState<{
    assignments: any[];
    unassigned: any[];
    score: number;
    penalty_breakdown: PenaltyBreakdown;
    iterations: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePreview = async () => {
    console.log('handlePreview called');
    setLoading(true);
    setError(null);
    setPreview(null);

    try {
      const data: PlanningGenerateRequest = {
        period_start: String(periodStart),
        period_end: String(periodEnd),
        service_ids: selectedServices.length > 0 ? selectedServices : undefined,
      };
      console.log('Sending preview request with data:', JSON.stringify(data, null, 2));
      const previewData = await previewPlanning(data);
      console.log('Preview response:', previewData);
      setPreview(previewData);
      console.log('Preview set, loading will be false');
    } catch (err: any) {
      console.error('Preview error:', err);
      setError(err.response?.data?.detail || err.message || "Erreur lors de la preview");
    } finally {
      console.log('Finally: setting loading to false');
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    console.log('handleGenerate called, dates:', periodStart, 'to', periodEnd);
    setLoading(true);
    setError(null);

    try {
      const data: PlanningGenerateRequest = {
        period_start: String(periodStart),
        period_end: String(periodEnd),
        service_ids: selectedServices.length > 0 ? selectedServices : undefined,
        use_optimization: useOptimization,
        max_iterations: maxIterations,
      };
      console.log('Sending request with data:', JSON.stringify(data, null, 2));
      const response = await generatePlanning(data);
      console.log('Response:', response);
      setResult({
        assignments: response.assignments,
        unassigned: response.unassigned_shifts,
        score: response.score,
        penalty_breakdown: response.penalty_breakdown,
        iterations: response.iterations,
      });
      setPreview(null);
      if (onGenerationComplete) {
        onGenerationComplete();
      }
    } catch (err: any) {
      console.error('Generate error:', err);
      let errorMsg = "Erreur lors de la generation";
      if (err.response?.data) {
        errorMsg = JSON.stringify(err.response.data);
      } else if (err.message) {
        errorMsg = err.message;
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const toggleService = (id: number) => {
    setSelectedServices((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <div style={{ padding: 16 }}>
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Generateur de Planning</h2>

        <div style={{ display: "grid", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Date de debut</label>
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="input"
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Date de fin</label>
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="input"
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 8 }}>Services (optionnel)</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {services.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  onClick={() => toggleService(service.id)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 999,
                    border: selectedServices.includes(service.id) ? "2px solid #3b82f6" : "1px solid #ccc",
                    background: selectedServices.includes(service.id) ? "#3b82f6" : "transparent",
                    color: selectedServices.includes(service.id) ? "white" : "inherit",
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  {service.name}
                </button>
              ))}
              {selectedServices.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedServices([])}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 999,
                    border: "1px dashed #ccc",
                    background: "transparent",
                    color: "#666",
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  Effacer
                </button>
              )}
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              Aucun service selectionne = tous les services
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 8 }}>Niveau d'optimisation</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              <button
                type="button"
                onClick={() => { setUseOptimization(false); }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 8,
                  border: !useOptimization ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                  background: !useOptimization ? "#eff6ff" : "white",
                  color: !useOptimization ? "#2563eb" : "#374151",
                  cursor: "pointer",
                  fontWeight: !useOptimization ? 600 : 400,
                  fontSize: 13,
                }}
              >
                <div style={{ fontWeight: 600 }}>Rapide</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>Glouton uniquement</div>
              </button>
              <button
                type="button"
                onClick={() => { setUseOptimization(true); setMaxIterations(500); }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 8,
                  border: useOptimization && maxIterations <= 500 && maxIterations >= 400 ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                  background: useOptimization && maxIterations <= 500 && maxIterations >= 400 ? "#eff6ff" : "white",
                  color: useOptimization && maxIterations <= 500 && maxIterations >= 400 ? "#2563eb" : "#374151",
                  cursor: "pointer",
                  fontWeight: useOptimization && maxIterations <= 500 && maxIterations >= 400 ? 600 : 400,
                  fontSize: 13,
                }}
              >
                <div style={{ fontWeight: 600 }}>Normal</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>500 iterations</div>
              </button>
              <button
                type="button"
                onClick={() => { setUseOptimization(true); setMaxIterations(1000); }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 8,
                  border: useOptimization && maxIterations > 500 ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                  background: useOptimization && maxIterations > 500 ? "#eff6ff" : "white",
                  color: useOptimization && maxIterations > 500 ? "#2563eb" : "#374151",
                  cursor: "pointer",
                  fontWeight: useOptimization && maxIterations > 500 ? 600 : 400,
                  fontSize: 13,
                }}
              >
                <div style={{ fontWeight: 600 }}>Complet</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>1000 iterations</div>
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              onClick={handlePreview}
              disabled={loading}
              className="btn btn-secondary"
              style={{ flex: 1 }}
            >
              {loading ? "Chargement..." : "Previsualiser"}
            </button>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="btn btn-primary"
              style={{ flex: 2 }}
            >
              {loading ? "Generation en cours..." : "Generer le Planning"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 8,
            background: "#fee2e2",
            color: "#dc2626",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {preview && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Previsualisation</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 12 }}>
            <div className="card" style={{ textAlign: "center", padding: 12 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#374151" }}>{preview.total_shifts}</div>
              <div style={{ fontSize: 11, color: "#6b7280" }}>Total creneaux</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: 12, background: "#dcfce7", color: "#1f2937" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#16a34a" }}>{preview.already_covered}</div>
              <div style={{ fontSize: 11, color: "#166534" }}>Couvert</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: 12, background: preview.needs_coverage > 0 ? "#fee2e2" : "#dcfce7", color: "#1f2937" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: preview.needs_coverage > 0 ? "#dc2626" : "#16a34a" }}>
                {preview.needs_coverage}
              </div>
              <div style={{ fontSize: 11, color: preview.needs_coverage > 0 ? "#991b1b" : "#166534" }}>Sous-effectif</div>
            </div>
            <div className="card" style={{ textAlign: "center", padding: 12, background: "#eff6ff", color: "#1f2937" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#2563eb" }}>
                {preview.total_shifts > 0 ? Math.round((preview.already_covered / preview.total_shifts) * 100) : 0}%
              </div>
              <div style={{ fontSize: 11, color: "#1e40af" }}>Couverture</div>
            </div>
          </div>

          {preview.total_shifts > 0 && preview.service_stats && preview.service_stats.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Besoins par service</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
                {preview.service_stats.map((service) => {
                  const coverage = service.min_staff_needed > 0 
                    ? Math.round((service.current_staff / service.min_staff_needed) * 100) 
                    : 100;
                  const isOk = service.shortage === 0;
                  return (
                    <div
                      key={service.id}
                      className="card"
                      style={{
                        padding: 12,
                        background: isOk ? '#dcfce7' : '#fee2e2',
                        borderLeft: `4px solid ${isOk ? '#16a34a' : '#dc2626'}`,
                        color: '#1f2937',
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{service.name}</div>
                      <div style={{ fontSize: 12, display: 'grid', gap: 3 }}>
                        <div><strong>Lits:</strong> {service.bed_capacity}</div>
                        <div><strong>Creneaux:</strong> {service.total_shifts}</div>
                        <div><strong>Personnel actuel:</strong> {service.current_staff}</div>
                        <div><strong>Personnel requis:</strong> {service.min_staff_needed}</div>
                        <div style={{ 
                          fontWeight: 600, 
                          color: isOk ? '#16a34a' : '#dc2626',
                          fontSize: 13,
                        }}>
                          Couverture: {coverage}%
                        </div>
                        <div style={{ 
                          fontWeight: 600, 
                          color: isOk ? '#16a34a' : '#dc2626',
                          fontSize: 13,
                        }}>
                          {isOk ? '✓ Satisfait' : `Manque: ${service.shortage}`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {preview.total_shifts > 0 && (
            <div style={{ overflowX: "auto" }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Liste des creneaux</h4>
              <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#f3f4f6" }}>
                    <th style={{ padding: 8, textAlign: "left" }}>Service</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Unite</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Date/Heure</th>
                    <th style={{ padding: 8, textAlign: "center" }}>Effectif</th>
                    <th style={{ padding: 8, textAlign: "center" }}>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.all_shifts.map((shift) => (
                    <tr key={shift.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                      <td style={{ padding: 8 }}>{shift.service}</td>
                      <td style={{ padding: 8 }}>{shift.unit}</td>
                      <td style={{ padding: 8 }}>{shift.shift_type}</td>
                      <td style={{ padding: 8 }}>
                        {new Date(shift.start).toLocaleDateString()} {new Date(shift.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </td>
                      <td style={{ padding: 8, textAlign: "center" }}>
                        {shift.current_staff}/{shift.min_staff}
                      </td>
                      <td style={{ padding: 8, textAlign: "center" }}>
                        <span style={{
                          padding: "2px 8px",
                          borderRadius: 999,
                          fontSize: 11,
                          background: shift.status === 'covered' ? '#dcfce7' : '#fef3c7',
                          color: shift.status === 'covered' ? '#16a34a' : '#d97706',
                        }}>
                          {shift.status === 'covered' ? 'Couvert' : 'Sous-effectif'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {preview.total_shifts > 30 && (
                <div className="muted" style={{ padding: 8, textAlign: "center" }}>
                  +{preview.total_shifts - 30} autres...
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Resultat</h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 16 }}>
            <div className="card" style={{ padding: 12 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#3b82f6" }}>
                {result.assignments.length}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>Affectations creees</div>
            </div>
            <div className="card" style={{ padding: 12, background: result.unassigned.length > 0 ? "#fef3c7" : "#dcfce7" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: result.unassigned.length > 0 ? "#d97706" : "#16a34a" }}>
                {result.unassigned.length}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>Creneaux non pourvus</div>
            </div>
          </div>

          <PenaltyDisplay breakdown={result.penalty_breakdown} score={result.score} />

          {result.iterations > 0 && (
            <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              Optimisation: {result.iterations} iterations
            </div>
          )}

          {result.assignments.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Dernieres affectations</div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#f3f4f6" }}>
                      <th style={{ padding: 8, textAlign: "left" }}>Soignant</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Service</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.assignments.slice(0, 15).map((a) => (
                      <tr key={a.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                        <td style={{ padding: 8 }}>{a.staff_name}</td>
                        <td style={{ padding: 8 }}>{a.service}</td>
                        <td style={{ padding: 8 }}>{a.shift_type}</td>
                        <td style={{ padding: 8 }}>{new Date(a.start).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.unassigned.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: "#d97706" }}>
                Creneaux non pourvus ({result.unassigned.length})
              </div>
              <div style={{ background: "#fef3c7", padding: 12, borderRadius: 8 }}>
                {result.unassigned.map((u) => (
                  <div key={u.shift_id} style={{ fontSize: 12, marginBottom: 4 }}>
                    {u.shift} - Manque {u.needed} soignant(s)
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
