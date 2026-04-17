import { apiClient } from "./client";

export type MetaRole = { id: number; name: string };
export type MetaService = { id: number; name: string };
export type MetaResponse = { roles: MetaRole[]; services: MetaService[] };

export async function getMeta(): Promise<MetaResponse> {
  const response = await apiClient.get<MetaResponse>("/meta/");
  return response.data;
}

