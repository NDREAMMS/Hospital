import { useState, useEffect } from "react";
import { PlanningGenerator } from "../components/PlanningGenerator";
import { getMeta } from "../api/meta";

export function GeneratorPage() {
  const [services, setServices] = useState<Array<{ id: number; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getMeta()
      .then((data) => {
        setServices(data.services || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Erreur de chargement");
        setLoading(false);
      });
  }, []);

  const handleGenerationComplete = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <div key={refreshKey}>
      <h1 className="pageTitle">Generateur de Planning</h1>
      {loading ? <div className="muted">Chargement...</div> : null}
      {error ? <div className="error">{error}</div> : null}
      {!loading && !error && (
        <PlanningGenerator
          services={services}
          onGenerationComplete={handleGenerationComplete}
        />
      )}
    </div>
  );
}
