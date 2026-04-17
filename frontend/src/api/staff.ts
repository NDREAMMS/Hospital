import { apiClient } from "./client";

export type StaffRow = {
  id: number;
  fullName: string;
  email: string;
  phone: string;
  is_active: boolean;
  role: string | null;
  service: string | null;
  status: string;
  certificationCount?: number;
  activeContract?: string | null;
};

export type StaffUpsert = {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  is_active?: boolean;
  role_id?: number | null;
  service_id?: number | null;
};

export async function listStaff(): Promise<StaffRow[]> {
  const response = await apiClient.get<StaffRow[]>("/staff/");
  return response.data;
}

export async function createStaff(payload: Required<Pick<StaffUpsert, "first_name" | "last_name" | "email">> &
  Omit<StaffUpsert, "first_name" | "last_name" | "email">): Promise<StaffRow> {
  const response = await apiClient.post<StaffRow>("/staff/", payload);
  return response.data;
}

export async function updateStaff(id: number, payload: StaffUpsert): Promise<StaffRow> {
  const response = await apiClient.patch<StaffRow>(`/staff/${id}/`, payload);
  return response.data;
}

export async function deleteStaff(id: number): Promise<void> {
  await apiClient.delete(`/staff/${id}/`);
}

export type StaffProfile = {
  staff: StaffRow;
  certifications: Array<{
    name: string;
    obtainedDate: string;
    expirationDate: string | null;
  }>;
  contracts: Array<{
    type: string;
    startDate: string;
    endDate: string | null;
    workloadPercent: number;
    nightShiftAllowed: boolean;
    maxHoursPerWeek: number;
  }>;
  shiftHistory: Array<{
    assignmentId: number;
    assignedAt: string;
    shiftId: number;
    service: string;
    unit: string;
    shiftType: string;
    start: string;
    end: string;
  }>;
  absences: Array<{
    type: string;
    startDate: string;
    expectedEndDate: string;
    actualEndDate: string | null;
  }>;
  constraints: {
    hardPreferences: string[];
    globalRules: Array<{ rule_type: string; value: string; unit: string }>;
  };
};

export async function getStaffProfile(id: number): Promise<StaffProfile> {
  const response = await apiClient.get<StaffProfile>(`/staff/${id}/profile/`);
  return response.data;
}
