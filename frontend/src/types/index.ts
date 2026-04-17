export type ApiError = {
  message: string;
  status?: number;
  details?: unknown;
};

export type Staff = {
  id: number;
  fullName: string;
  role?: string;
};

export type Shift = {
  id: number;
  title: string;
  service?: string;
  unit?: string;
  shiftType?: string;
  start: string;
  end: string;
  staffCount?: number;
  assignmentsCount?: number;
  minStaff?: number;
  maxStaff?: number;
  status?: string;
  assignedStaff?: Array<{
    id: number;
    fullName: string;
    role?: string | null;
  }>;
  requiredCertifications?: string[];
  eligible?: boolean;
  eligibilityErrors?: string[];
};

export type Assignment = {
  id: number;
  shiftId: number;
  staffId: number;
  assignedAt?: string;
};

export type Absence = {
  id: number;
  staffId: number;
  start: string;
  end: string;
  reason?: string;
};
