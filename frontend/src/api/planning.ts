import { apiClient } from "./client";

export interface PlanningGenerateRequest {
  period_start: string;
  period_end: string;
  service_ids?: number[];
  use_optimization?: boolean;
  max_iterations?: number;
}

export interface PenaltyBreakdown {
  consecutive_nights: number;
  preference_violation: number;
  workload_imbalance: number;
  service_change: number;
  weekend_ratio: number;
  new_service_without_adaptation: number;
  lack_of_continuity: number;
}

export interface AssignmentResult {
  id: number;
  staff_id: number;
  staff_name: string;
  shift_id: number;
  shift: string;
  start: string;
  end: string;
  service: string;
  unit: string;
  shift_type: string;
}

export interface UnassignedShift {
  shift_id: number;
  shift: string;
  needed: number;
  available: number;
}

export interface PlanningGenerateResponse {
  success: boolean;
  assignments: AssignmentResult[];
  unassigned_shifts: UnassignedShift[];
  score: number;
  penalty_breakdown: PenaltyBreakdown;
  iterations: number;
  message: string;
}

export interface PlanningPreviewRequest {
  period_start: string;
  period_end: string;
  service_ids?: number[];
}

export interface ShiftToCover {
  id: number;
  service: string;
  service_id: number;
  unit: string;
  shift_type: string;
  start: string;
  end: string;
  current_staff: number;
  min_staff: number;
  max_staff: number;
  status: string;
}

export interface PlanningPreviewResponse {
  shifts_to_cover: ShiftToCover[];
  all_shifts: ShiftToCover[];
  total_shifts: number;
  already_covered: number;
  needs_coverage: number;
  services: string[];
  service_stats: ServiceStat[];
}

export interface ServiceStat {
  id: number;
  name: string;
  bed_capacity: number;
  total_shifts: number;
  min_staff_needed: number;
  current_staff: number;
  shortage: number;
  uncovered_shifts: number;
}

export interface ValidateEditRequest {
  staff_id: number;
  shift_id: number;
}

export interface ValidateEditResponse {
  valid: boolean;
  violations: string[];
}

export interface PlanningScoreResponse {
  score: number;
  penalty_breakdown: PenaltyBreakdown;
  total_assignments: number;
  unassigned_shifts: UnassignedShift[];
}

export interface PenaltyWeight {
  rule_type: string;
  value: number;
  description: string;
}

export interface PenaltyWeightsResponse {
  weights: PenaltyWeight[];
}

export async function generatePlanning(data: PlanningGenerateRequest): Promise<PlanningGenerateResponse> {
  const response = await apiClient.post<PlanningGenerateResponse>("/plannings/generate/", data);
  return response.data;
}

export async function previewPlanning(data: PlanningPreviewRequest): Promise<PlanningPreviewResponse> {
  const response = await apiClient.post<PlanningPreviewResponse>("/plannings/preview/", data);
  return response.data;
}

export async function validateEdit(data: ValidateEditRequest): Promise<ValidateEditResponse> {
  const response = await apiClient.post<ValidateEditResponse>("/plannings/validate-edit/", data);
  return response.data;
}

export async function getPlanningScore(
  periodStart: string,
  periodEnd: string,
  serviceIds?: number[]
): Promise<PlanningScoreResponse> {
  const params = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
  });
  if (serviceIds && serviceIds.length > 0) {
    params.append("service_ids", serviceIds.join(","));
  }
  const response = await apiClient.get<PlanningScoreResponse>(`/plannings/score/?${params}`);
  return response.data;
}

export async function getPenaltyWeights(): Promise<PenaltyWeightsResponse> {
  const response = await apiClient.get<PenaltyWeightsResponse>("/plannings/penalty-weights/");
  return response.data;
}

export async function updatePenaltyWeight(
  ruleType: string,
  value: number,
  description?: string
): Promise<{ success: boolean; rule_type: string; value: number }> {
  const response = await apiClient.patch("/plannings/penalty-weights/", {
    rule_type: ruleType,
    value,
    description,
  });
  return response.data;
}
