import { apiClient } from "./client";
import type { Shift } from "../types";

export async function listShifts(): Promise<Shift[]> {
  const response = await apiClient.get<Shift[]>("/shifts/");
  return response.data;
}
