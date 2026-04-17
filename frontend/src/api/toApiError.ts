import axios from "axios";
import type { ApiError } from "../types";

export function toApiError(caught: unknown, fallbackMessage: string): ApiError {
  if (axios.isAxiosError(caught)) {
    const status = caught.response?.status;
    const details = caught.response?.data ?? caught.message;
    return {
      message: status ? `${fallbackMessage} (HTTP ${status})` : fallbackMessage,
      status,
      details,
    };
  }

  return { message: fallbackMessage, details: caught };
}
