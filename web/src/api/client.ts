import type { Component, ComponentText, Manifest, Run, Turn } from '../types';
import { getToken } from './token';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message); this.name = 'ApiError'; this.status = status;
  }
}
export function apiBase(): string {
  return (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
}
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (res.status === 401) throw new ApiError(401, 'unauthorized');
  if (!res.ok) throw new ApiError(res.status, `request failed: ${res.status}`);
  return (await res.json()) as T;
}
export const getManifest = () => apiGet<Manifest>('/api/manifest');
export const getRuns = () => apiGet<Run[]>('/api/runs');
export const getTurns = () => apiGet<Turn[]>('/api/turns');
export const getComponents = () => apiGet<Component[]>('/api/components');
export const getTokenRates = () => apiGet<Record<string, number>>('/api/token-rates');
export const getComponentTexts = (runId: string, requestIndex?: number) =>
  apiGet<ComponentText[]>(
    `/api/component-texts?run_id=${encodeURIComponent(runId)}` +
      (requestIndex != null ? `&request_index=${requestIndex}` : ''),
  );
