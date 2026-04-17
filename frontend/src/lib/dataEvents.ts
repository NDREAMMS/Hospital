export const DATA_CHANGED_EVENT = "data:changed";

export function dispatchDataChanged() {
  window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
}

