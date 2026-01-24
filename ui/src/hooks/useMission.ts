import { create } from 'zustand';
import type {
  Coordinate,
  Waypoint,
  NoGoZone,
  VehicleProfile,
  RouteResult,
  MapMode,
  TacticalUnit,
  TacticalRoute,
} from '@/types';

interface MissionState {
  // Points (Legacy - for backward compatibility)
  startPoint: Coordinate | null;
  endPoint: Coordinate | null;
  waypoints: Waypoint[];
  noGoZones: NoGoZone[];

  // Selection (Legacy)
  selectedVehicle: VehicleProfile | null;

  // Route result (Legacy)
  routeResult: RouteResult | null;

  // Tactical Units (NEW)
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];

  // Tactical Routes (NEW)
  tacticalRoutes: TacticalRoute[];
  routeVisibility: Record<number, boolean>;
  selectedRouteId: number | null;

  // Map mode
  mapMode: MapMode;

  // UI state
  isPlanning: boolean;
  bottomPanelOpen: boolean;
  hoveredDistance: number | null;
  advancedAnalytics: boolean;
  currentZoom: number;

  // Actions (Legacy)
  setStartPoint: (point: Coordinate | null) => void;
  setEndPoint: (point: Coordinate | null) => void;
  addWaypoint: (point: Coordinate) => void;
  removeWaypoint: (id: string) => void;
  reorderWaypoints: (waypoints: Waypoint[]) => void;
  addNoGoZone: (zone: NoGoZone) => void;
  removeNoGoZone: (id: string) => void;
  setSelectedVehicle: (vehicle: VehicleProfile | null) => void;
  setRouteResult: (result: RouteResult | null) => void;
  setMapMode: (mode: MapMode) => void;
  setIsPlanning: (planning: boolean) => void;
  setBottomPanelOpen: (open: boolean) => void;
  setHoveredDistance: (distance: number | null) => void;
  setAdvancedAnalytics: (enabled: boolean) => void;
  setCurrentZoom: (zoom: number) => void;
  clearAll: () => void;

  // Tactical Actions (NEW)
  addSoldier: (unit: Omit<TacticalUnit, 'unit_id'>) => void;
  removeSoldier: (unitId: string) => void;
  updateSoldierPosition: (unitId: string, coord: Coordinate) => void;
  addEnemy: (unit: Omit<TacticalUnit, 'unit_id'>) => void;
  removeEnemy: (unitId: string) => void;
  updateEnemyPosition: (unitId: string, coord: Coordinate) => void;
  setTacticalRoutes: (routes: TacticalRoute[]) => void;
  toggleRouteVisibility: (routeId: number) => void;
  setSelectedRoute: (routeId: number | null) => void;
}

export const useMission = create<MissionState>((set, get) => ({
  // Legacy state
  startPoint: null,
  endPoint: null,
  waypoints: [],
  noGoZones: [],
  selectedVehicle: null,
  routeResult: null,

  // Tactical state
  soldiers: [],
  enemies: [],
  tacticalRoutes: [],
  routeVisibility: {},
  selectedRouteId: null,

  // UI state
  mapMode: 'idle',
  isPlanning: false,
  bottomPanelOpen: true,
  hoveredDistance: null,
  advancedAnalytics: false,
  currentZoom: 14,

  setStartPoint: (point) => set({ startPoint: point, mapMode: 'idle' }),
  setEndPoint: (point) => set({ endPoint: point, mapMode: 'idle' }),
  
  addWaypoint: (point) => {
    const { waypoints } = get();
    const newWaypoint: Waypoint = {
      ...point,
      id: crypto.randomUUID(),
      order: waypoints.length,
    };
    set({ waypoints: [...waypoints, newWaypoint], mapMode: 'idle' });
  },
  
  removeWaypoint: (id) => {
    const { waypoints } = get();
    const filtered = waypoints
      .filter((w) => w.id !== id)
      .map((w, i) => ({ ...w, order: i }));
    set({ waypoints: filtered });
  },
  
  reorderWaypoints: (waypoints) => set({ waypoints }),
  
  addNoGoZone: (zone) => {
    const { noGoZones } = get();
    set({ noGoZones: [...noGoZones, zone], mapMode: 'idle' });
  },
  
  removeNoGoZone: (id) => {
    const { noGoZones } = get();
    set({ noGoZones: noGoZones.filter((z) => z.id !== id) });
  },
  
  setSelectedVehicle: (vehicle) => set({ selectedVehicle: vehicle }),
  setRouteResult: (result) => set({ routeResult: result }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setIsPlanning: (planning) => set({ isPlanning: planning }),
  setBottomPanelOpen: (open) => set({ bottomPanelOpen: open }),
  setHoveredDistance: (distance) => set({ hoveredDistance: distance }),
  setAdvancedAnalytics: (enabled) => set({ advancedAnalytics: enabled }),
  setCurrentZoom: (zoom) => set({ currentZoom: zoom }),

  // Tactical unit actions
  addSoldier: (unit) => {
    const { soldiers } = get();
    const newSoldier: TacticalUnit = {
      ...unit,
      unit_id: crypto.randomUUID(),
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
      unit_id: crypto.randomUUID(),
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
  setTacticalRoutes: (routes) => {
    // Initialize route visibility to all true
    const visibility = routes.reduce(
      (acc, route) => ({ ...acc, [route.route_id]: true }),
      {} as Record<number, boolean>
    );
    set({
      tacticalRoutes: routes,
      routeVisibility: visibility,
      selectedRouteId: routes.length > 0 ? routes[0].route_id : null,
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

  clearAll: () =>
    set({
      // Legacy state
      startPoint: null,
      endPoint: null,
      waypoints: [],
      noGoZones: [],
      routeResult: null,
      // Tactical state
      soldiers: [],
      enemies: [],
      tacticalRoutes: [],
      routeVisibility: {},
      selectedRouteId: null,
      // UI state
      mapMode: 'idle',
      isPlanning: false,
    }),
}));
