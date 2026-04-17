import { useCallback, useMemo, useState } from "react";
import type { Shift } from "../types";

type Stored = {
  shift: Shift;
  selectedAt: string;
};

const STORAGE_KEY = "selectedShift.v1";

function readStored(): Stored | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Stored;
  } catch {
    return null;
  }
}

function writeStored(value: Stored | null) {
  try {
    if (!value) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // ignore storage errors
  }
}

export function useSelectedShift() {
  const [stored, setStored] = useState<Stored | null>(() => readStored());

  const setSelectedShift = useCallback((shift: Shift | null) => {
    const next = shift ? { shift, selectedAt: new Date().toISOString() } : null;
    writeStored(next);
    setStored(next);
  }, []);

  const selectedShift = stored?.shift ?? null;
  const selectedAt = stored?.selectedAt ?? null;

  return useMemo(
    () => ({ selectedShift, selectedAt, setSelectedShift }),
    [selectedShift, selectedAt, setSelectedShift],
  );
}

