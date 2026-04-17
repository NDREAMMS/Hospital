import { apiClient } from "./client";
import type { Assignment } from "../types";

export async function listAssignments(): Promise<Assignment[]> {
  const response = await apiClient.get<Assignment[]>("/assignments/");
  return response.data;
}
