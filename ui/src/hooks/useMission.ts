import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type {
  Coordinate,
  MapMode,
  TacticalUnit,
  TacticalRoute,
  Bounds,
} from '@/types';

// Helper function to get display name for a unit
export const getUnitDisplayName = (unit: TacticalUnit): string => {
  const type = unit.is_friendly ? 'Friendly' : 'Enemy';
  if (unit.plan_id !== undefined && unit.plan_unit_number !== undefined) {
    return `Plan ${unit.plan_id} ${type} #${unit.plan_unit_number}`;
  }
  return `${type} Unit`;
};

// Tactical report entry for history
export interface TacticalReportEntry {
  id: string;
  timestamp: Date;
  centerCoords: { lat: number; lon: number };
  report: {
    mission_summary?: string;
    recommended_approach?: { route?: string; reasoning?: string };
    timing_suggestions?: { optimal_time?: string; reasoning?: string };
    equipment_recommendations?: Array<{ item?: string; reason?: string }>;
    enemy_analysis?: { weakness?: string };
    risk_zones?: Array<{ location?: string; mitigation?: string }>;
  };
}

// Route drawing mode
export type RouteMode = 'ai-generate' | 'manual-draw';

// Drawn waypoint
export interface DrawnWaypoint {
  lat: number;
  lng: number;
}

// ============================================================================
// Tactical Simulation Types (Draw Mode)
// ============================================================================

// Enemy unit types with vision cone parameters
export type SimEnemyType = 'sniper' | 'rifleman' | 'observer';

// Vision cone specs per enemy type (in meters and degrees)
// Scaled for zoom 17 visibility - realistic tactical ranges
export const ENEMY_VISION_SPECS: Record<SimEnemyType, { distance: number; angle: number; color: string }> = {
  sniper: { distance: 250, angle: 25, color: '#ef4444' },    // Red - precision, narrow FOV
  rifleman: { distance: 75, angle: 60, color: '#ef4444' },   // Red - close combat range
  observer: { distance: 200, angle: 45, color: '#ef4444' },  // Red - observation range
};

// Simulation enemy unit
export interface SimEnemy {
  id: string;
  type: SimEnemyType;
  lat: number;
  lng: number;
  facing: number;  // Direction in degrees (0 = North, 90 = East, etc.)
}

// Friendly unit types
export type SimFriendlyType = 'rifleman' | 'sniper' | 'medic';

// Simulation friendly unit
export interface SimFriendly {
  id: string;
  type: SimFriendlyType;
  lat: number;
  lng: number;
}

// NEW: Segment cover analysis from AI
export interface SegmentCoverAnalysis {
  segment_index: number;
  in_vision_cone: boolean;
  cover_status: 'exposed' | 'covered' | 'partial' | 'clear';
  cover_type: string | null;  // "building", "vegetation", "terrain", or null
  exposure_percentage: number;
  blocking_feature: string | null;
  enemy_id: string | null;
  explanation: string;
}

// NEW: Tactical scores (0-100 each)
export interface TacticalScores {
  stealth: number;
  safety: number;
  terrain_usage: number;
  flanking: number;
  overall: number;
}

// NEW: Flanking analysis
export interface FlankingAnalysis {
  is_flanking: boolean;
  approach_angle: number;  // degrees from enemy facing
  bonus_awarded: number;   // 0-3 points
  description: string;
}

// NEW: Cover breakdown summary
export interface CoverBreakdown {
  total_segments: number;
  exposed_count: number;
  covered_count: number;
  partial_count: number;
  clear_count: number;
  overall_cover_percentage: number;
  cover_types_used: string[];
}

// Simulation history entry
export interface SimulationHistoryEntry {
  id: string;
  timestamp: Date;
  name: string;  // Auto-generated or user-provided
  result: TacticalSimulationResult;
  // Snapshot of scenario for context
  enemyCount: number;
  friendlyCount: number;
  waypointCount: number;
}

// Tactical simulation result from AI
export interface TacticalSimulationResult {
  request_id: string;
  annotated_image: string;  // Base64 image with annotations
  annotated_image_bounds: Bounds;
  strategy_rating: number;  // 0-10 score
  verdict?: string;  // "EXCELLENT", "GOOD", "ACCEPTABLE", "RISKY"

  // NEW: Enhanced analysis
  tactical_scores?: TacticalScores;
  flanking_analysis?: FlankingAnalysis;
  segment_cover_analysis?: SegmentCoverAnalysis[];
  cover_breakdown?: CoverBreakdown;

  // Strong points (good terrain usage)
  strong_points?: Array<{
    location: string;
    description: string;
    benefit: string;
  }>;

  weak_spots: Array<{
    location: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    recommendation: string;
  }>;
  exposure_analysis: Array<{
    segment_index: number;
    enemy_id: string;
    exposure_percentage: number;
    description: string;
  }>;
  terrain_assessment?: string;
  overall_assessment: string;
  recommendations: string[];
  route_distance_m: number;
  estimated_time_minutes: number;
}

// Unit composition for evaluation (legacy)
export interface UnitComposition {
  squadSize: number;
  riflemen: number;
  snipers: number;
  support: number;
  medics: number;
}

// Suggested position from AI
export interface SuggestedPosition {
  position_type: string;
  lat: number;
  lng: number;
  description: string;
  for_unit?: string;
  icon: string;
}

// Segment analysis from AI
export interface SegmentAnalysis {
  segment_index: number;
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
  risk_level: string;
  description: string;
  suggestions: string[];
}

// Route evaluation result
export interface RouteEvaluationResult {
  request_id: string;
  annotated_image: string;
  annotated_image_bounds: Bounds;
  positions: SuggestedPosition[];
  segment_analysis: SegmentAnalysis[];
  overall_assessment: string;
  route_distance_m: number;
  estimated_time_minutes: number;
}

interface MissionState {
  // Tactical Units
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];

  // Plan management - track which plan ID to assign next
  nextPlanId: number;

  // Tactical Routes (NEW)
  tacticalRoutes: TacticalRoute[];
  routeVisibility: Record<number, boolean>;
  selectedRouteId: number | null;

  // Obstacle/Route Visualization
  samVisualization: string | null;
  samVisualizationBounds: Bounds | null;
  // Multiple plan images - keyed by plan_id
  planImages: Record<number, { image: string; bounds: Bounds }>;
  // Legacy single image (for backward compatibility during transition)
  geminiRouteImage: string | null;
  geminiRouteImageBounds: Bounds | null;

  // Advanced Tactical Analysis Report
  tacticalAnalysisReport: Record<string, unknown> | null;
  tacticalReportHistory: TacticalReportEntry[];
  selectedReportId: string | null;
  reportModalOpen: boolean;

  // Route Drawing Mode
  routeMode: RouteMode;
  drawnWaypoints: DrawnWaypoint[];
  unitComposition: UnitComposition;
  routeEvaluation: RouteEvaluationResult | null;
  isEvaluating: boolean;

  // Tactical Simulation State (Draw Mode)
  simEnemies: SimEnemy[];
  simFriendlies: SimFriendly[];
  selectedSimEnemyType: SimEnemyType;
  selectedSimFriendlyType: SimFriendlyType;
  simulationResult: TacticalSimulationResult | null;
  simulationHistory: SimulationHistoryEntry[];
  selectedHistoryId: string | null;

  // Map mode
  mapMode: MapMode;

  // UI state
  isPlanning: boolean;
  advancedAnalytics: boolean;
  currentZoom: number;

  // Map & UI Actions
  setMapMode: (mode: MapMode) => void;
  setIsPlanning: (planning: boolean) => void;
  setAdvancedAnalytics: (enabled: boolean) => void;
  setCurrentZoom: (zoom: number) => void;
  clearAll: () => void;

  // Tactical Actions
  addSoldier: (unit: Omit<TacticalUnit, 'unit_id'>) => void;
  removeSoldier: (unitId: string) => void;
  updateSoldierPosition: (unitId: string, coord: Coordinate) => void;
  addEnemy: (unit: Omit<TacticalUnit, 'unit_id'>) => void;
  removeEnemy: (unitId: string) => void;
  updateEnemyPosition: (unitId: string, coord: Coordinate) => void;
  setTacticalRoutes: (routes: TacticalRoute[], detectionDebug?: {
    sam_visualization?: string;
    sam_visualization_bounds?: Bounds;
    gemini_route_image?: string;
    gemini_route_bounds?: Bounds;
  }, tacticalAnalysisReport?: Record<string, unknown> | null) => void;
  toggleRouteVisibility: (routeId: number) => void;
  setSelectedRoute: (routeId: number | null) => void;
  clearRoutes: () => void;  // Clear routes only, keep units
  resetForRegeneration: () => void;  // Reset units to regenerate routes

  // Report history actions
  addReportToHistory: (report: TacticalReportEntry) => void;
  removeReportFromHistory: (id: string) => void;
  selectReport: (id: string | null) => void;
  setReportModalOpen: (open: boolean) => void;

  // Route Drawing actions
  setRouteMode: (mode: RouteMode) => void;
  addDrawnWaypoint: (lat: number, lng: number) => void;
  updateDrawnWaypoint: (index: number, lat: number, lng: number) => void;
  removeDrawnWaypoint: (index: number) => void;
  clearDrawnWaypoints: () => void;
  setUnitComposition: (units: Partial<UnitComposition>) => void;
  setRouteEvaluation: (result: RouteEvaluationResult | null) => void;
  setIsEvaluating: (evaluating: boolean) => void;

  // Tactical Simulation actions
  addSimEnemy: (lat: number, lng: number) => void;
  removeSimEnemy: (id: string) => void;
  updateSimEnemyPosition: (id: string, lat: number, lng: number) => void;
  updateSimEnemyFacing: (id: string, facing: number) => void;
  setSelectedSimEnemyType: (type: SimEnemyType) => void;
  addSimFriendly: (lat: number, lng: number) => void;
  removeSimFriendly: (id: string) => void;
  updateSimFriendlyPosition: (id: string, lat: number, lng: number) => void;
  setSelectedSimFriendlyType: (type: SimFriendlyType) => void;
  setSimulationResult: (result: TacticalSimulationResult | null) => void;
  clearSimulation: () => void;

  // Simulation history actions
  saveToSimulationHistory: (result: TacticalSimulationResult, name?: string) => void;
  loadFromSimulationHistory: (id: string) => void;
  removeFromSimulationHistory: (id: string) => void;
  clearSimulationHistory: () => void;
  setSelectedHistoryId: (id: string | null) => void;
}

export const useMission = create<MissionState>((set, get) => ({
  // Tactical state
  soldiers: [],
  enemies: [],
  nextPlanId: 1,
  tacticalRoutes: [],
  routeVisibility: {},
  selectedRouteId: null,

  // Route/Obstacle Visualization
  samVisualization: null,
  samVisualizationBounds: null,
  planImages: {},  // Multiple plan images keyed by plan_id
  geminiRouteImage: null,
  geminiRouteImageBounds: null,

  // Advanced Tactical Analysis Report
  tacticalAnalysisReport: null,
  tacticalReportHistory: [],
  selectedReportId: null,
  reportModalOpen: false,

  // Route Drawing Mode
  routeMode: 'ai-generate',
  drawnWaypoints: [],
  unitComposition: {
    squadSize: 4,
    riflemen: 2,
    snipers: 1,
    support: 0,
    medics: 1,
  },
  routeEvaluation: null,
  isEvaluating: false,

  // Tactical Simulation State
  simEnemies: [],
  simFriendlies: [],
  selectedSimEnemyType: 'rifleman',
  selectedSimFriendlyType: 'rifleman',
  simulationResult: null,
  simulationHistory: [],
  selectedHistoryId: null,

  // UI state
  mapMode: 'idle',
  isPlanning: false,
  advancedAnalytics: false,
  currentZoom: 14,

  setMapMode: (mode) => set({ mapMode: mode }),
  setIsPlanning: (planning) => set({ isPlanning: planning }),
  setAdvancedAnalytics: (enabled) => set({ advancedAnalytics: enabled }),
  setCurrentZoom: (zoom) => set({ currentZoom: zoom }),

  // Tactical unit actions
  addSoldier: (unit) => {
    const { soldiers } = get();
    const newSoldier: TacticalUnit = {
      ...unit,
      unit_id: uuidv4(),
      is_friendly: true,
    };
    set({ soldiers: [...soldiers, newSoldier], mapMode: 'idle' });
  },

  removeSoldier: (unitId) => {
    const { soldiers } = get();
    set({ soldiers: soldiers.filter((s) => s.unit_id !== unitId) });
  },

  updateSoldierPosition: (unitId, coord) => {
    const { soldiers } = get();
    set({
      soldiers: soldiers.map((s) =>
        s.unit_id === unitId ? { ...s, lat: coord.lat, lon: coord.lon } : s
      ),
    });
  },

  addEnemy: (unit) => {
    const { enemies } = get();
    const newEnemy: TacticalUnit = {
      ...unit,
      unit_id: uuidv4(),
      is_friendly: false,
    };
    set({ enemies: [...enemies, newEnemy], mapMode: 'idle' });
  },

  removeEnemy: (unitId) => {
    const { enemies } = get();
    set({ enemies: enemies.filter((e) => e.unit_id !== unitId) });
  },

  updateEnemyPosition: (unitId, coord) => {
    const { enemies } = get();
    set({
      enemies: enemies.map((e) =>
        e.unit_id === unitId ? { ...e, lat: coord.lat, lon: coord.lon } : e
      ),
    });
  },

  // Tactical route actions
  setTacticalRoutes: (routes, detectionDebug?: {
    sam_visualization?: string;
    sam_visualization_bounds?: Bounds;
    gemini_route_image?: string;
    gemini_route_bounds?: Bounds;
  }, tacticalAnalysisReport?: Record<string, unknown> | null) => {
    const { soldiers, enemies, tacticalReportHistory, nextPlanId, planImages } = get();

    // Initialize route visibility to all true
    const visibility = routes.reduce(
      (acc, route) => ({ ...acc, [route.route_id]: true }),
      {} as Record<number, boolean>
    );

    // Assign unassigned units to the current plan
    let soldierCounter = 1;
    let enemyCounter = 1;
    const updatedSoldiers = soldiers.map((s) => {
      if (s.plan_id === undefined) {
        return { ...s, plan_id: nextPlanId, plan_unit_number: soldierCounter++ };
      }
      return s;
    });
    const updatedEnemies = enemies.map((e) => {
      if (e.plan_id === undefined) {
        return { ...e, plan_id: nextPlanId, plan_unit_number: enemyCounter++ };
      }
      return e;
    });

    // Calculate center coordinates from soldiers and enemies
    const allUnits = [...soldiers, ...enemies];
    const centerCoords = allUnits.length > 0
      ? {
          lat: allUnits.reduce((sum, u) => sum + u.lat, 0) / allUnits.length,
          lon: allUnits.reduce((sum, u) => sum + u.lon, 0) / allUnits.length,
        }
      : { lat: 0, lon: 0 };

    // Auto-save report to history if provided
    let updatedHistory = tacticalReportHistory;
    if (tacticalAnalysisReport) {
      const newEntry: TacticalReportEntry = {
        id: uuidv4(),
        timestamp: new Date(),
        centerCoords,
        report: tacticalAnalysisReport as TacticalReportEntry['report'],
      };
      updatedHistory = [newEntry, ...tacticalReportHistory];
    }

    // Store new plan image - REPLACE previous ones to avoid doubled routes
    // Only keep the latest plan image
    const updatedPlanImages: Record<number, { image: string; bounds: Bounds }> = {};
    if (detectionDebug?.gemini_route_image && detectionDebug?.gemini_route_bounds) {
      updatedPlanImages[nextPlanId] = {
        image: detectionDebug.gemini_route_image,
        bounds: detectionDebug.gemini_route_bounds,
      };
    }

    set({
      soldiers: updatedSoldiers,
      enemies: updatedEnemies,
      nextPlanId: nextPlanId + 1,
      tacticalRoutes: routes,
      routeVisibility: visibility,
      selectedRouteId: routes.length > 0 ? routes[0].route_id : null,
      samVisualization: detectionDebug?.sam_visualization || null,
      samVisualizationBounds: detectionDebug?.sam_visualization_bounds || null,
      planImages: updatedPlanImages,  // Store all plan images
      geminiRouteImage: detectionDebug?.gemini_route_image || null,
      geminiRouteImageBounds: detectionDebug?.gemini_route_bounds || null,
      tacticalAnalysisReport: tacticalAnalysisReport || null,
      tacticalReportHistory: updatedHistory,
    });
  },

  toggleRouteVisibility: (routeId) => {
    const { routeVisibility } = get();
    set({
      routeVisibility: {
        ...routeVisibility,
        [routeId]: !routeVisibility[routeId],
      },
    });
  },

  setSelectedRoute: (routeId) => set({ selectedRouteId: routeId }),

  // Clear routes and plan images (keep units only)
  clearRoutes: () =>
    set({
      tacticalRoutes: [],
      routeVisibility: {},
      selectedRouteId: null,
      samVisualization: null,
      samVisualizationBounds: null,
      planImages: {},  // Clear plan images to show unit markers again
      geminiRouteImage: null,
      geminiRouteImageBounds: null,
      geminiRouteImage: null,
      geminiRouteImageBounds: null,
      tacticalAnalysisReport: null,
    }),

  // Reset units for regeneration - clears plan_id so units can be reused
  resetForRegeneration: () => {
    const { soldiers, enemies } = get();
    // Reset plan_id on all units so they're treated as new
    const resetSoldiers = soldiers.map((s) => ({ ...s, plan_id: undefined, plan_unit_number: undefined }));
    const resetEnemies = enemies.map((e) => ({ ...e, plan_id: undefined, plan_unit_number: undefined }));
    set({
      soldiers: resetSoldiers,
      enemies: resetEnemies,
      tacticalRoutes: [],
      routeVisibility: {},
      selectedRouteId: null,
      samVisualization: null,
      samVisualizationBounds: null,
      geminiRouteImage: null,
      geminiRouteImageBounds: null,
      tacticalAnalysisReport: null,
    });
  },

  // Report history actions
  addReportToHistory: (report) => {
    const { tacticalReportHistory } = get();
    set({ tacticalReportHistory: [report, ...tacticalReportHistory] });
  },

  removeReportFromHistory: (id) => {
    const { tacticalReportHistory, selectedReportId } = get();
    const filtered = tacticalReportHistory.filter((r) => r.id !== id);
    set({
      tacticalReportHistory: filtered,
      selectedReportId: selectedReportId === id ? null : selectedReportId,
    });
  },

  // When selecting a tactical report, clear selectedHistoryId to avoid conflicts
  selectReport: (id) => set({ selectedReportId: id, selectedHistoryId: null }),

  setReportModalOpen: (open) => set({ reportModalOpen: open }),

  // Route Drawing actions
  setRouteMode: (mode) => set({ routeMode: mode, drawnWaypoints: [], routeEvaluation: null }),

  addDrawnWaypoint: (lat, lng) => {
    const { drawnWaypoints } = get();
    set({ drawnWaypoints: [...drawnWaypoints, { lat, lng }] });
  },

  updateDrawnWaypoint: (index, lat, lng) => {
    const { drawnWaypoints } = get();
    const updated = [...drawnWaypoints];
    if (index >= 0 && index < updated.length) {
      updated[index] = { lat, lng };
      set({ drawnWaypoints: updated });
    }
  },

  removeDrawnWaypoint: (index) => {
    const { drawnWaypoints } = get();
    set({ drawnWaypoints: drawnWaypoints.filter((_, i) => i !== index) });
  },

  clearDrawnWaypoints: () => set({ drawnWaypoints: [], routeEvaluation: null }),

  setUnitComposition: (units) => {
    const { unitComposition } = get();
    set({ unitComposition: { ...unitComposition, ...units } });
  },

  setRouteEvaluation: (result) => set({ routeEvaluation: result }),

  setIsEvaluating: (evaluating) => set({ isEvaluating: evaluating }),

  // Tactical Simulation actions
  addSimEnemy: (lat, lng) => {
    const { simEnemies, selectedSimEnemyType } = get();
    const newEnemy: SimEnemy = {
      id: uuidv4(),
      type: selectedSimEnemyType,
      lat,
      lng,
      facing: 0,  // Default facing North
    };
    set({ simEnemies: [...simEnemies, newEnemy], mapMode: 'idle' });
  },

  removeSimEnemy: (id) => {
    const { simEnemies } = get();
    set({ simEnemies: simEnemies.filter((e) => e.id !== id) });
  },

  updateSimEnemyPosition: (id, lat, lng) => {
    const { simEnemies } = get();
    set({
      simEnemies: simEnemies.map((e) =>
        e.id === id ? { ...e, lat, lng } : e
      ),
    });
  },

  updateSimEnemyFacing: (id, facing) => {
    const { simEnemies } = get();
    set({
      simEnemies: simEnemies.map((e) =>
        e.id === id ? { ...e, facing: facing % 360 } : e
      ),
    });
  },

  setSelectedSimEnemyType: (type) => set({ selectedSimEnemyType: type }),

  addSimFriendly: (lat, lng) => {
    const { simFriendlies, selectedSimFriendlyType } = get();
    const newFriendly: SimFriendly = {
      id: uuidv4(),
      type: selectedSimFriendlyType,
      lat,
      lng,
    };
    set({ simFriendlies: [...simFriendlies, newFriendly], mapMode: 'idle' });
  },

  removeSimFriendly: (id) => {
    const { simFriendlies } = get();
    set({ simFriendlies: simFriendlies.filter((f) => f.id !== id) });
  },

  updateSimFriendlyPosition: (id, lat, lng) => {
    const { simFriendlies } = get();
    set({
      simFriendlies: simFriendlies.map((f) =>
        f.id === id ? { ...f, lat, lng } : f
      ),
    });
  },

  setSelectedSimFriendlyType: (type) => set({ selectedSimFriendlyType: type }),

  setSimulationResult: (result) => {
    if (result) {
      // Auto-save to history when setting a new result
      const { simEnemies, simFriendlies, drawnWaypoints, simulationHistory } = get();
      const timestamp = new Date();
      const rating = result.strategy_rating?.toFixed(1) || '?';
      const verdict = result.verdict || 'N/A';
      const name = `Analysis ${timestamp.toLocaleTimeString('en-US', { timeZone: 'Asia/Riyadh' })} - ${verdict} (${rating}/10)`;

      const historyEntry: SimulationHistoryEntry = {
        id: uuidv4(),
        timestamp,
        name,
        result,
        enemyCount: simEnemies.length,
        friendlyCount: simFriendlies.length,
        waypointCount: drawnWaypoints.length,
      };

      set({
        simulationResult: result,
        simulationHistory: [historyEntry, ...simulationHistory].slice(0, 20), // Keep last 20
        selectedHistoryId: historyEntry.id,
      });
    } else {
      set({ simulationResult: result });
    }
  },

  // Simulation history actions
  saveToSimulationHistory: (result, name) => {
    const { simEnemies, simFriendlies, drawnWaypoints, simulationHistory } = get();
    const timestamp = new Date();
    const autoName = name || `Analysis ${timestamp.toLocaleTimeString('en-US', { timeZone: 'Asia/Riyadh' })}`;

    const historyEntry: SimulationHistoryEntry = {
      id: uuidv4(),
      timestamp,
      name: autoName,
      result,
      enemyCount: simEnemies.length,
      friendlyCount: simFriendlies.length,
      waypointCount: drawnWaypoints.length,
    };

    set({
      simulationHistory: [historyEntry, ...simulationHistory].slice(0, 20),
    });
  },

  loadFromSimulationHistory: (id) => {
    const { simulationHistory } = get();
    const entry = simulationHistory.find(h => h.id === id);
    if (entry) {
      set({
        simulationResult: entry.result,
        selectedHistoryId: id,
        selectedReportId: null, // Clear tactical report selection to avoid conflicts
        reportModalOpen: true,
      });
    }
  },

  removeFromSimulationHistory: (id) => {
    const { simulationHistory, selectedHistoryId } = get();
    set({
      simulationHistory: simulationHistory.filter(h => h.id !== id),
      selectedHistoryId: selectedHistoryId === id ? null : selectedHistoryId,
    });
  },

  clearSimulationHistory: () => set({ simulationHistory: [], selectedHistoryId: null, tacticalReportHistory: [], selectedReportId: null }),

  setSelectedHistoryId: (id) => set({ selectedHistoryId: id }),

  clearSimulation: () => set({
    simEnemies: [],
    simFriendlies: [],
    drawnWaypoints: [],
    // Keep simulationResult so the report button stays accessible
  }),

  clearAll: () =>
    set({
      soldiers: [],
      enemies: [],
      nextPlanId: 1,
      tacticalRoutes: [],
      routeVisibility: {},
      selectedRouteId: null,
      samVisualization: null,
      samVisualizationBounds: null,
      planImages: {},
      geminiRouteImage: null,
      geminiRouteImageBounds: null,
      tacticalAnalysisReport: null,
      mapMode: 'idle',
      isPlanning: false,
      // Reset route drawing state
      routeMode: 'ai-generate',
      drawnWaypoints: [],
      routeEvaluation: null,
      isEvaluating: false,
      // Reset simulation state
      simEnemies: [],
      simFriendlies: [],
      simulationResult: null,
    }),
}));
