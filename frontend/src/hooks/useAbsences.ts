import { useCallback, useEffect, useState } from "react";
import { listAbsences } from "../api/absences";
import { toApiError } from "../api/toApiError";
import type { Absence, ApiError } from "../types";

export function useAbsences() {
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAbsences();
      setAbsences(data);
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load absences"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { absences, loading, error, refresh };
}
