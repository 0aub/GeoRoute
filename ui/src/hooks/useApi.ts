import { useMutation, useQuery } from '@tanstack/react-query';
import { getApiUrl } from '@/config/env';
import type {
  HealthStatus,
  TacticalPlanRequest,
  TacticalPlanResponse,
  Bounds,
} from '@/types';
import type {
  DrawnWaypoint,
  UnitComposition,
  RouteEvaluationResult,
  SimEnemy,
  SimFriendly,
  TacticalSimulationResult,
} from './useMission';

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
    const error = await response.json().catch(() => ({}));
    // FastAPI returns { detail: "..." }, other APIs may return { message: "..." }
    const message = error.detail || error.message || `Request failed with status ${response.status}`;
    throw new Error(message);
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

// ============================================================================
// Route Evaluation API
// ============================================================================

export interface RouteEvaluationRequest {
  request_id?: string;
  waypoints: DrawnWaypoint[];
  units: {
    squad_size: number;
    riflemen: number;
    snipers: number;
    support: number;
    medics: number;
  };
  bounds: Bounds;
}

export const useEvaluateRoute = () => {
  return useMutation<RouteEvaluationResult, Error, RouteEvaluationRequest>({
    mutationFn: (request) =>
      fetchWithError('/api/evaluate-route', {
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

// ============================================================================
// Tactical Simulation API
// ============================================================================

export interface TacticalSimulationRequest {
  request_id?: string;
  enemies: Array<{
    id: string;
    type: string;
    lat: number;
    lng: number;
    facing: number;
  }>;
  friendlies: Array<{
    id: string;
    type: string;
    lat: number;
    lng: number;
  }>;
  route_waypoints: DrawnWaypoint[];
  bounds: Bounds;
}

export const useAnalyzeTacticalSimulation = () => {
  return useMutation<TacticalSimulationResult, Error, TacticalSimulationRequest>({
    mutationFn: (request) =>
      fetchWithError('/api/analyze-tactical-simulation', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
  });
};
