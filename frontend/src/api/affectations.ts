import { apiClient } from "./client";

export type AffectationCreatePayload = { staff_id: number; shift_id: number };
export type AffectationCreateResponse = {
  id: number;
  staffId: number;
  shiftId: number;
  assignedAt: string;
};

export type AffectationCheckResponse = {
  eligible: boolean;
  reasons: string[];
  requiredCertifications: string[];
  missingCertifications: string[];
  expiredCertifications: string[];
};

export async function createAffectation(
  payload: AffectationCreatePayload,
): Promise<AffectationCreateResponse> {
  const response = await apiClient.post<AffectationCreateResponse>(
    "/assignments/",
    payload,
  );
  return response.data;
}

export async function checkAffectation(
  payload: AffectationCreatePayload,
): Promise<AffectationCheckResponse> {
  const response = await apiClient.post<AffectationCheckResponse>(
    "/assignments/check/",
    payload,
  );
  return response.data;
}
