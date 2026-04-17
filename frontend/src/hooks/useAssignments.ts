import { useCallback, useEffect, useState } from "react";
import { listAssignments } from "../api/assignments";
import { toApiError } from "../api/toApiError";
import type { ApiError, Assignment } from "../types";

export function useAssignments() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAssignments();
      setAssignments(data);
    } catch (caught: unknown) {
      setError(toApiError(caught, "Failed to load assignments"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { assignments, loading, error, refresh };
}
