import { useMutation, useQuery } from '@tanstack/react-query';
import { getApiUrl } from '@/config/env';
import type {
  HealthStatus,
  TacticalPlanRequest,
  TacticalPlanResponse,
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
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return response.json();
};

export const useHealth = () => {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => fetchWithError('/api/health'),
    enabled: !!apiUrl,
    refetchInterval: 30000,
  });
};

// ============================================================================
// Tactical Planning API
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

  return () => {
    eventSource.close();
  };
};
