import { useCallback, useRef } from "react";

export function useRefresh() {
  const refreshCount = useRef(0);

  const trigger = useCallback(() => {
    refreshCount.current += 1;
  }, []);

  const getRefreshKey = useCallback(() => {
    return refreshCount.current;
  }, []);

  return { trigger, getRefreshKey };
}
