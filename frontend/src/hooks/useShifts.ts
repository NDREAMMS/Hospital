import { useCallback, useEffect, useState } from "react";
import { listShifts } from "../api/shifts";
import { toApiError } from "../api/toApiError";
import type { ApiError, Shift } from "../types";

export function useShifts() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listShifts();
      setShifts(data);
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load shifts"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { shifts, loading, error, refresh };
}
