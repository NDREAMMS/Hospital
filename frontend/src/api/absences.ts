import { apiClient } from "./client";
import type { Absence } from "../types";

export async function listAbsences(): Promise<Absence[]> {
  const response = await apiClient.get<Absence[]>("/absences/");
  return response.data;
}
