import { apiClient } from "./client";

export type Poste = {
  id: number;
  title?: string;
  service: string;
  unit: string;
  shiftType: string;
  start: string;
  end: string;
  status: "Disponible" | "Affecte";
  assignmentsCount: number;
  minStaff?: number;
  maxStaff?: number;
  assignedStaff?: Array<{ id: number; fullName: string; role?: string | null }>;
  requiredCertifications?: string[];
};

export async function listPostes(): Promise<Poste[]> {
  const response = await apiClient.get<Poste[]>("/shifts/");
  return response.data;
}
