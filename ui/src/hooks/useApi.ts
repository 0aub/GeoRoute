import { useMutation, useQuery } from '@tanstack/react-query';
import { getApiUrl } from '@/config/env';
import type {
  PlanRouteRequest,
  QuickAssessRequest,
  RouteResult,
  VehicleProfile,
  HealthStatus,
  TacticalPlanRequest,
  TacticalPlanResponse,
  BacklogEntry,
  BacklogListResponse,
} from '@/types';

const apiUrl = getApiUrl();

const fetchWithError = async <T>(url: string, options?: RequestInit): Promise<T> => {
  if (!apiUrl) {
    throw new Error('API URL not configured');
  }

  const response = await fetch(`${apiUrl}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return response.json();
};

export const useVehicles = () => {
  return useQuery<VehicleProfile[]>({
    queryKey: ['vehicles'],
    queryFn: () => fetchWithError('/api/vehicles'),
    enabled: !!apiUrl,
    staleTime: Infinity,
  });
};

export const useHealth = () => {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => fetchWithError('/api/health'),
    enabled: !!apiUrl,
    refetchInterval: 30000,
  });
};

export const usePlanRoute = () => {
  return useMutation<RouteResult, Error, PlanRouteRequest>({
    mutationFn: (request) =>
      fetchWithError('/api/plan-route', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
  });
};

export const useQuickAssess = () => {
  return useMutation<any, Error, QuickAssessRequest>({
    mutationFn: (request) =>
      fetchWithError('/api/quick-assess', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
  });
};

// ============================================================================
// Tactical Planning API Hooks
// ============================================================================

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
}

export const usePlanTacticalAttack = () => {
  return useMutation<TacticalPlanResponse, Error, TacticalPlanRequest>({
    mutationFn: (request) =>
      fetchWithError('/api/plan-tactical-attack', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
  });
};

/**
 * Subscribe to real-time progress updates via SSE
 */
export const subscribeToProgress = (
  requestId: string,
  onProgress: (update: ProgressUpdate) => void,
  onError?: (error: Error) => void
): (() => void) => {
  if (!apiUrl) {
    onError?.(new Error('API URL not configured'));
    return () => {};
  }

  const eventSource = new EventSource(`${apiUrl}/api/progress/${requestId}`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as ProgressUpdate;
      onProgress(data);

      // Close connection when complete or error
      if (data.stage === 'complete' || data.stage === 'error') {
        eventSource.close();
      }
    } catch (e) {
      console.error('Failed to parse progress update:', e);
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    onError?.(new Error('Progress stream disconnected'));
  };

  // Return cleanup function
  return () => {
    eventSource.close();
  };
};

export const useBacklogList = (limit = 50, offset = 0, since?: string) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (since) {
    params.append('since', since);
  }

  return useQuery<BacklogListResponse>({
    queryKey: ['backlog', limit, offset, since],
    queryFn: () => fetchWithError(`/api/backlog?${params.toString()}`),
    enabled: !!apiUrl,
  });
};

export const useBacklogEntry = (requestId: string | null) => {
  return useQuery<BacklogEntry>({
    queryKey: ['backlog', requestId],
    queryFn: () => fetchWithError(`/api/backlog/${requestId}`),
    enabled: !!apiUrl && !!requestId,
  });
};

export const useBacklogImages = (requestId: string | null) => {
  return useQuery<{ satellite_image?: string; terrain_image?: string }>({
    queryKey: ['backlog', requestId, 'images'],
    queryFn: () => fetchWithError(`/api/backlog/${requestId}/images`),
    enabled: !!apiUrl && !!requestId,
  });
};
