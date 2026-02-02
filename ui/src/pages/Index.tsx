import { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Sidebar } from '@/components/sidebar/Sidebar';
import { TacticalMap } from '@/components/map/TacticalMap';
import { ConfigError } from '@/components/ConfigError';
import { PlanningLoader } from '@/components/tactical/PlanningLoader';
import { isConfigured } from '@/config/env';
import { useMission } from '@/hooks/useMission';
import {
  usePlanTacticalAttack,
  useEvaluateRoute,
  useHealth,
  subscribeToProgress,
  type ProgressUpdate,
} from '@/hooks/useApi';
import { useToast } from '@/hooks/use-toast';
import type { TacticalUnit, Bounds } from '@/types';

const RoutePlanner = () => {
  const { toast } = useToast();
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const {
    isPlanning,
    setIsPlanning,
    soldiers,
    enemies,
    setTacticalRoutes,
    currentZoom,
    advancedAnalytics,
    // Route evaluation
    drawnWaypoints,
    unitComposition,
    setRouteEvaluation,
    setIsEvaluating,
    isEvaluating,
  } = useMission();

  const { data: health, isError } = useHealth();
  const planTacticalAttack = usePlanTacticalAttack();
  const evaluateRoute = useEvaluateRoute();

  // Update connection status based on health check
  useEffect(() => {
    if (isError) {
      setIsConnected(false);
    } else if (health) {
      setIsConnected(health.status === 'ok');
    }
  }, [health, isError]);

  // Cleanup SSE subscription on unmount
  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  // Helper: Calculate bounds from units with zoom-aware padding
  const calculateBounds = (units: TacticalUnit[]): Bounds => {
    if (units.length === 0) {
      return { north: 0, south: 0, east: 0, west: 0 };
    }

    const lats = units.map((u) => u.lat);
    const lons = units.map((u) => u.lon);

    // Calculate distance between units to determine appropriate padding
    const latSpan = Math.max(...lats) - Math.min(...lats);
    const lonSpan = Math.max(...lons) - Math.min(...lons);
    const maxSpan = Math.max(latSpan, lonSpan);

    // Padding should be proportional to the unit spread, with a minimum
    // At high zoom (close), use small padding. At low zoom, allow more.
    const minPadding = 0.001; // ~100m minimum
    const padding = Math.max(minPadding, maxSpan * 0.3); // 30% of span

    return {
      north: Math.max(...lats) + padding,
      south: Math.min(...lats) - padding,
      east: Math.max(...lons) + padding,
      west: Math.min(...lons) - padding,
    };
  };

  // Handle tactical attack planning
  const handlePlanTacticalAttack = async () => {
    // Only use UNASSIGNED units for new route generation
    // Units that already have a plan_id are part of previous plans
    const unassignedSoldiers = soldiers.filter(s => s.plan_id === undefined);
    const unassignedEnemies = enemies.filter(e => e.plan_id === undefined);

    // Check if there are unassigned units to plan for
    if (unassignedSoldiers.length === 0 || unassignedEnemies.length === 0) {
      // If no unassigned units, check if there are ANY units
      if (soldiers.length === 0 || enemies.length === 0) {
        toast({
          title: 'Missing Units',
          description: 'Please place at least 1 friendly and 1 enemy unit on the map.',
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'No New Units',
          description: 'Place new friendly AND enemy units to generate a new plan. Current units already have assigned plans.',
          variant: 'destructive',
        });
      }
      return;
    }

    // Generate unique request ID for progress tracking
    const requestId = uuidv4();

    setIsPlanning(true);
    setProgress(null);

    // Subscribe to progress updates BEFORE calling API
    unsubscribeRef.current = subscribeToProgress(
      requestId,
      (update) => {
        setProgress(update);
      },
      (error) => {
        console.error('[TacticalPlan] Progress stream error:', error);
      }
    );

    try {
      // Only calculate bounds and send unassigned units
      const unassignedUnits = [...unassignedSoldiers, ...unassignedEnemies];
      const bounds = calculateBounds(unassignedUnits);

      const result = await planTacticalAttack.mutateAsync({
        request_id: requestId,
        soldiers: unassignedSoldiers,
        enemies: unassignedEnemies,
        bounds,
        zoom: currentZoom,
        advanced_analytics: advancedAnalytics,
      });

      if (result && result.routes && Array.isArray(result.routes)) {
        setTacticalRoutes(result.routes, result.detection_debug, result.tactical_analysis_report);
        toast({
          title: 'Tactical Plan Generated',
          description: `Created ${result.routes.length} tactical routes. Review classifications in the sidebar.`,
        });
      } else {
        console.error('[TacticalPlan] Invalid response format:', result);
        throw new Error('Invalid response format from server');
      }
    } catch (error: any) {
      console.error('[TacticalPlan] Error:', error);
      toast({
        title: 'Planning Failed',
        description: error.message || 'Failed to generate tactical plan. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsPlanning(false);
      setProgress(null);

      // Cleanup SSE subscription
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    }
  };

  // Handle route evaluation (manual draw mode)
  const handleEvaluateRoute = async () => {
    if (drawnWaypoints.length < 2) {
      toast({
        title: 'Insufficient Waypoints',
        description: 'Please draw at least 2 waypoints to evaluate a route.',
        variant: 'destructive',
      });
      return;
    }

    // Generate unique request ID for progress tracking
    const requestId = uuidv4();

    setIsEvaluating(true);
    setProgress(null);

    // Subscribe to progress updates
    unsubscribeRef.current = subscribeToProgress(
      requestId,
      (update) => {
        setProgress(update);
      },
      (error) => {
        console.error('[RouteEvaluation] Progress stream error:', error);
      }
    );

    try {
      // Calculate bounds from waypoints
      const lats = drawnWaypoints.map((wp) => wp.lat);
      const lngs = drawnWaypoints.map((wp) => wp.lng);
      const padding = 0.002; // ~200m padding

      const bounds: Bounds = {
        north: Math.max(...lats) + padding,
        south: Math.min(...lats) - padding,
        east: Math.max(...lngs) + padding,
        west: Math.min(...lngs) - padding,
      };

      const result = await evaluateRoute.mutateAsync({
        request_id: requestId,
        waypoints: drawnWaypoints,
        units: {
          squad_size: unitComposition.squadSize,
          riflemen: unitComposition.riflemen,
          snipers: unitComposition.snipers,
          support: unitComposition.support,
          medics: unitComposition.medics,
        },
        bounds,
      });

      if (result) {
        setRouteEvaluation(result);
        toast({
          title: 'Route Evaluated',
          description: `Found ${result.positions.length} tactical positions. Check the sidebar for details.`,
        });
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (error: any) {
      console.error('[RouteEvaluation] Error:', error);
      toast({
        title: 'Evaluation Failed',
        description: error.message || 'Failed to evaluate route. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsEvaluating(false);
      setProgress(null);

      // Cleanup SSE subscription
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    }
  };

  return (
    <div className="h-screen w-screen flex bg-background-deep overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar
        onPlanTacticalAttack={handlePlanTacticalAttack}
        onEvaluateRoute={handleEvaluateRoute}
        isLoading={isPlanning || isEvaluating}
        isConnected={isConnected}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Map */}
        <div className="flex-1 relative">
          <TacticalMap />
        </div>
      </div>

      {/* Loading Animation - Full Screen Overlay with REAL progress */}
      {(isPlanning || isEvaluating) && <PlanningLoader progress={progress} advancedAnalytics={advancedAnalytics} />}
    </div>
  );
};

const Index = () => {
  if (!isConfigured()) {
    return <ConfigError />;
  }

  return <RoutePlanner />;
};

export default Index;
