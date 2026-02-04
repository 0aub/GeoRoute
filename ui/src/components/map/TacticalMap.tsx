import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMission, getUnitDisplayName, ENEMY_VISION_SPECS, type SimEnemy, type SimFriendly } from '@/hooks/useMission';
import { ZoomIndicator } from './ZoomIndicator';
import type { Coordinate, RiskLevel } from '@/types';

// Fix Leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Unit marker icons - NATO APP-6 style military symbols - Large, high-visibility
const createUnitIcon = (isFriendly: boolean) => {
  if (isFriendly) {
    // NATO Friendly Unit: Blue rounded rectangle with infantry symbol
    return L.divIcon({
      className: 'custom-unit-marker',
      html: `
        <div style="
          width: 50px;
          height: 40px;
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          border: 4px solid white;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 16px rgba(0,0,0,0.6);
          cursor: move;
        ">
          <svg width="28" height="24" viewBox="0 0 28 24" fill="none">
            <line x1="6" y1="20" x2="14" y2="4" stroke="white" stroke-width="4" stroke-linecap="round"/>
            <line x1="22" y1="20" x2="14" y2="4" stroke="white" stroke-width="4" stroke-linecap="round"/>
          </svg>
        </div>
      `,
      iconSize: [50, 40],
      iconAnchor: [25, 20],
    });
  } else {
    // NATO Hostile Unit: Red diamond shape
    return L.divIcon({
      className: 'custom-unit-marker',
      html: `
        <div style="
          width: 44px;
          height: 44px;
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border: 4px solid white;
          transform: rotate(45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 16px rgba(0,0,0,0.6);
          cursor: move;
        ">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style="transform: rotate(-45deg);">
            <circle cx="10" cy="10" r="5" fill="white"/>
          </svg>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });
  }
};

// Simulation enemy icons by type - military style with direction indicator
const createSimEnemyIcon = (type: string, facing: number) => {
  // All enemies use red
  const color = '#dc2626';

  // Military symbols - all 28x28 for consistency
  const symbols: Record<string, string> = {
    sniper: `<svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="5" style="stroke:#ffffff;stroke-width:3;fill:none"/>
      <line x1="14" y1="2" x2="14" y2="7" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="14" y1="21" x2="14" y2="26" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="2" y1="14" x2="7" y2="14" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="21" y1="14" x2="26" y2="14" style="stroke:#ffffff;stroke-width:3"/>
    </svg>`,
    rifleman: `<svg viewBox="0 0 28 28" width="28" height="28">
      <line x1="6" y1="24" x2="14" y2="4" style="stroke:#ffffff;stroke-width:4;stroke-linecap:round"/>
      <line x1="22" y1="24" x2="14" y2="4" style="stroke:#ffffff;stroke-width:4;stroke-linecap:round"/>
    </svg>`,
    observer: `<svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="10" style="stroke:#ffffff;stroke-width:3;fill:none"/>
      <circle cx="14" cy="14" r="4" style="fill:#ffffff"/>
    </svg>`,
  };

  return L.divIcon({
    className: 'sim-enemy-marker',
    html: `
      <div style="
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, ${color} 0%, ${color}dd 100%);
        border: 3px solid white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 3px 10px rgba(0,0,0,0.5);
        cursor: move;
        position: relative;
      ">
        <div style="
          position: absolute;
          top: -12px;
          left: 50%;
          transform: translateX(-50%) rotate(${facing}deg);
          transform-origin: center 34px;
        ">
          <svg width="14" height="16" viewBox="0 0 14 16">
            <polygon points="7,0 14,14 7,10 0,14" style="fill:#ffffff;stroke:${color};stroke-width:1.5"/>
          </svg>
        </div>
        ${symbols[type] || symbols.rifleman}
      </div>
    `,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
};

// Simulation friendly icons by type - NATO blue rectangles
const createSimFriendlyIcon = (type: string) => {
  // Military symbols - same size as enemy icons (28x28)
  const symbols: Record<string, string> = {
    rifleman: `<svg viewBox="0 0 28 28" width="28" height="28">
      <line x1="6" y1="24" x2="14" y2="4" style="stroke:#ffffff;stroke-width:4;stroke-linecap:round"/>
      <line x1="22" y1="24" x2="14" y2="4" style="stroke:#ffffff;stroke-width:4;stroke-linecap:round"/>
    </svg>`,
    sniper: `<svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="5" style="stroke:#ffffff;stroke-width:3;fill:none"/>
      <line x1="14" y1="2" x2="14" y2="7" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="14" y1="21" x2="14" y2="26" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="2" y1="14" x2="7" y2="14" style="stroke:#ffffff;stroke-width:3"/>
      <line x1="21" y1="14" x2="26" y2="14" style="stroke:#ffffff;stroke-width:3"/>
    </svg>`,
    medic: `<svg viewBox="0 0 28 28" width="28" height="28">
      <rect x="11" y="4" width="6" height="20" style="fill:#ffffff" rx="1"/>
      <rect x="4" y="11" width="20" height="6" style="fill:#ffffff" rx="1"/>
    </svg>`,
  };

  return L.divIcon({
    className: 'sim-friendly-marker',
    html: `
      <div style="
        width: 44px;
        height: 36px;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: 3px solid white;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 3px 10px rgba(0,0,0,0.5);
        cursor: move;
      ">
        ${symbols[type] || symbols.rifleman}
      </div>
    `,
    iconSize: [44, 36],
    iconAnchor: [22, 18],
  });
};

// Calculate vision cone polygon points
// Compass bearing: 0° = North, 90° = East, 180° = South, 270° = West
const calculateVisionCone = (
  lat: number,
  lng: number,
  facing: number,
  distanceMeters: number,
  angleWidth: number
): L.LatLngExpression[] => {
  const points: L.LatLngExpression[] = [[lat, lng]]; // Start at the enemy position

  // Convert distance from meters to approximate degrees (1 degree ≈ 111km)
  const distanceDeg = distanceMeters / 111000;

  // Calculate the arc points
  const halfAngle = angleWidth / 2;
  const startAngle = facing - halfAngle;
  const endAngle = facing + halfAngle;

  // Generate points along the arc (every 5 degrees for smoothness)
  // For compass bearing: North=0°, East=90°
  // lat += cos(bearing), lng += sin(bearing)
  for (let angle = startAngle; angle <= endAngle; angle += 5) {
    const radians = angle * (Math.PI / 180);
    const newLat = lat + distanceDeg * Math.cos(radians);
    const newLng = lng + distanceDeg * Math.sin(radians) / Math.cos(lat * (Math.PI / 180)); // Adjust for latitude
    points.push([newLat, newLng]);
  }

  // Ensure the last point is at the exact end angle
  const endRadians = endAngle * (Math.PI / 180);
  const endLat = lat + distanceDeg * Math.cos(endRadians);
  const endLng = lng + distanceDeg * Math.sin(endRadians) / Math.cos(lat * (Math.PI / 180));
  points.push([endLat, endLng]);

  return points;
};

// Risk level to color mapping - Brand aligned and highly visible
const riskColorMap: Record<RiskLevel, string> = {
  safe: '#00A05A',      // Brand Light Green - safe/clear
  moderate: '#F5C623',  // Golden Yellow - caution
  high: '#FF6B00',      // Vivid Orange - warning
  critical: '#DC2626',  // Clear Red - danger
};

// Tile layers - Using ESRI World Imagery (matches backend satellite fetch)
const tileLayers = {
  satellite: L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
      attribution: 'Tiles © Esri',
      maxZoom: 19,
    }
  ),
  terrain: L.tileLayer(
    'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    {
      attribution: 'Map data © OpenTopoMap',
      maxZoom: 17,
    }
  ),
};

// Gulf region validation
const GULF_BOUNDS = {
  minLat: 16.0,
  maxLat: 32.0,
  minLon: 34.5,
  maxLon: 60.0,
};

const isInGulfRegion = (lat: number, lon: number): boolean => {
  return (
    lat >= GULF_BOUNDS.minLat &&
    lat <= GULF_BOUNDS.maxLat &&
    lon >= GULF_BOUNDS.minLon &&
    lon <= GULF_BOUNDS.maxLon
  );
};

export const TacticalMap = () => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<{
    unitMarkers: L.Marker[];
    routePolylines: L.Polyline[];
    samOverlay: L.ImageOverlay | null;
    planOverlays: Record<number, L.ImageOverlay>;
    drawnWaypointMarkers: L.CircleMarker[];
    drawnRoutePolyline: L.Polyline | null;
    evaluationOverlay: L.ImageOverlay | null;
    // Simulation elements
    simEnemyMarkers: L.Marker[];
    simEnemyVisionCones: L.Polygon[];
    simFriendlyMarkers: L.Marker[];
  }>({
    unitMarkers: [],
    routePolylines: [],
    samOverlay: null,
    planOverlays: {},
    drawnWaypointMarkers: [],
    drawnRoutePolyline: null,
    evaluationOverlay: null,
    // Simulation elements
    simEnemyMarkers: [],
    simEnemyVisionCones: [],
    simFriendlyMarkers: [],
  });

  const {
    mapMode,
    soldiers,
    enemies,
    tacticalRoutes,
    routeVisibility,
    addSoldier,
    addEnemy,
    updateSoldierPosition,
    updateEnemyPosition,
    setCurrentZoom,
    samVisualization,
    samVisualizationBounds,
    planImages,
    // Route drawing state
    drawnWaypoints,
    addDrawnWaypoint,
    updateDrawnWaypoint,
    routeEvaluation,
    // Simulation state
    simEnemies,
    simFriendlies,
    addSimEnemy,
    addSimFriendly,
    updateSimEnemyPosition,
    updateSimEnemyFacing,
    updateSimFriendlyPosition,
    simulationResult,  // For cover analysis colors
  } = useMission();

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Gulf region bounds (GCC countries: Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, Oman)
    const gulfBounds: L.LatLngBoundsExpression = [
      [16.0, 34.5], // Southwest corner (Southern Saudi/Yemen border, Red Sea)
      [32.0, 60.0]  // Northeast corner (Northern Kuwait, Eastern Oman)
    ];

    const map = L.map(mapRef.current, {
      center: [24.7, 46.7], // Riyadh, Saudi Arabia
      zoom: 7,
      zoomControl: false,
      minZoom: 7,
      maxZoom: 19,
      maxBounds: gulfBounds,
      maxBoundsViscosity: 1.0, // Prevent panning outside bounds
    });

    // Add base layer
    tileLayers.satellite.addTo(map);

    // Add layer control
    L.control.layers(
      { Satellite: tileLayers.satellite, Terrain: tileLayers.terrain },
      {},
      { position: 'topright' }
    ).addTo(map);

    // Add zoom control
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Add Gulf region boundary overlay (visual indicator)
    const gulfBoundary = L.rectangle(gulfBounds, {
      color: '#22c55e',
      weight: 2,
      fillOpacity: 0,
      opacity: 0.4,
      dashArray: '10, 10',
      interactive: false,
    }).addTo(map);

    // Add gray overlay for areas outside Gulf region
    // This creates a world-sized polygon with a hole for the Gulf region
    const worldBounds: L.LatLngExpression[] = [
      [-90, -180],
      [90, -180],
      [90, 180],
      [-90, 180],
      [-90, -180],
    ];

    const gulfHole: L.LatLngExpression[] = [
      [16.0, 34.5],  // SW
      [32.0, 34.5],  // NW
      [32.0, 60.0],  // NE
      [16.0, 60.0],  // SE
      [16.0, 34.5],  // Close
    ];

    const outsideGulfOverlay = L.polygon([worldBounds, gulfHole], {
      color: '#000000',
      weight: 0,
      fillColor: '#000000',
      fillOpacity: 0.85,
      interactive: false,
    }).addTo(map);

    mapInstanceRef.current = map;

    // Track zoom changes
    map.on('zoomend', () => {
      setCurrentZoom(map.getZoom());
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Handle map clicks based on mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const handleClick = (e: L.LeafletMouseEvent) => {
      const coord: Coordinate = { lat: e.latlng.lat, lon: e.latlng.lng };

      // Modes that need Gulf region validation
      const restrictedModes = ['place-soldier', 'place-enemy', 'draw-route', 'place-sim-enemy', 'place-sim-friendly'];

      // Check zoom level for placing points - require zoom >= 17 for accuracy
      if (restrictedModes.includes(mapMode) && map.getZoom() < 17) {
        L.popup()
          .setLatLng(e.latlng)
          .setContent(
            '<div style="color: #f59e0b; font-weight: bold;">⚠️ Zoom In Required</div>' +
            '<div style="margin-top: 4px;">Please zoom in to level 17 or higher<br/>' +
            'for accurate point placement.<br/>' +
            '<small style="color: #9ca3af;">Current zoom: ' + map.getZoom().toFixed(0) + '</small></div>'
          )
          .openOn(map);
        return;
      }

      // Validate Gulf region for tactical operations
      if (restrictedModes.includes(mapMode) && !isInGulfRegion(coord.lat, coord.lon)) {
        L.popup()
          .setLatLng(e.latlng)
          .setContent(
            '<div style="color: #ef4444; font-weight: bold;">⚠️ Outside Gulf Region</div>' +
            '<div style="margin-top: 4px;">System restricted to GCC countries:<br/>' +
            'Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, Oman</div>'
          )
          .openOn(map);
        return;
      }

      if (mapMode === 'place-soldier') {
        addSoldier({ lat: coord.lat, lon: coord.lon, is_friendly: true });
      } else if (mapMode === 'place-enemy') {
        addEnemy({ lat: coord.lat, lon: coord.lon, is_friendly: false });
      } else if (mapMode === 'draw-route') {
        addDrawnWaypoint(coord.lat, coord.lon);
      } else if (mapMode === 'place-sim-enemy') {
        addSimEnemy(coord.lat, coord.lon);
      } else if (mapMode === 'place-sim-friendly') {
        addSimFriendly(coord.lat, coord.lon);
      }
    };

    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [mapMode, addSoldier, addEnemy, addDrawnWaypoint, addSimEnemy, addSimFriendly]);

  // Update unit markers - hide when Gemini route image is showing
  // (Gemini draws markers in the correct position on the image)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing unit markers
    markersRef.current.unitMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.unitMarkers = [];

    // Always render unit markers - keep them visible even after route generation
    // Create soldier markers (draggable, blue)
    soldiers.forEach((soldier) => {
      const displayName = getUnitDisplayName(soldier);
      const marker = L.marker([soldier.lat, soldier.lon], {
        icon: createUnitIcon(true),
        draggable: true,
      })
        .on('dragend', (e) => {
          const newPos = (e.target as L.Marker).getLatLng();
          updateSoldierPosition(soldier.unit_id, {
            lat: newPos.lat,
            lon: newPos.lng,
          });
        })
        .bindPopup(`<strong>${displayName}</strong>`)
        .addTo(map);

      markersRef.current.unitMarkers.push(marker);
    });

    // Create enemy markers (draggable, red)
    enemies.forEach((enemy) => {
      const displayName = getUnitDisplayName(enemy);
      const marker = L.marker([enemy.lat, enemy.lon], {
        icon: createUnitIcon(false),
        draggable: true,
      })
        .on('dragend', (e) => {
          const newPos = (e.target as L.Marker).getLatLng();
          updateEnemyPosition(enemy.unit_id, {
            lat: newPos.lat,
            lon: newPos.lng,
          });
        })
        .bindPopup(`<strong>${displayName}</strong>`)
        .addTo(map);

      markersRef.current.unitMarkers.push(marker);
    });

    return () => {
      markersRef.current.unitMarkers.forEach((m) => map.removeLayer(m));
    };
  }, [soldiers, enemies, updateSoldierPosition, updateEnemyPosition, planImages]);

  // Update tactical routes (multi-route with color-coded segments)
  // Skip polyline rendering when Gemini image overlay is available
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || tacticalRoutes.length === 0) return;

    // Clear existing route polylines
    markersRef.current.routePolylines.forEach((p) => map.removeLayer(p));
    markersRef.current.routePolylines = [];

    // Skip polyline rendering if plan images are available
    // The plan images already show the routes visually
    if (Object.keys(planImages).length > 0) {
      return;
    }

    // Render each tactical route
    tacticalRoutes.forEach((route) => {
      const isVisible = routeVisibility[route.route_id];

      // Create polyline for each segment with risk-based color
      route.segments.forEach((segment) => {
        const coords = route.waypoints
          .slice(segment.start_waypoint_idx, segment.end_waypoint_idx + 1)
          .map((wp) => [wp.lat, wp.lon] as [number, number]);

        const color = riskColorMap[segment.risk_level];

        const polyline = L.polyline(coords, {
          color,
          weight: 4,
          opacity: isVisible ? 0.8 : 0,
          className: `route-${route.route_id}`,
        })
          .bindPopup(
            `
            <div style="min-width: 220px;">
              <strong>${route.name}</strong><br/>
              <span style="font-size: 12px;">Segment ${segment.segment_id}</span><br/>
              <hr style="border-color: #333; margin: 6px 0;" />
              <strong>Risk Level:</strong>
              <span style="color: ${color}; font-weight: bold;">
                ${segment.risk_level.toUpperCase()}
              </span><br/>
              <strong>Distance:</strong> ${segment.distance_m.toFixed(0)}m<br/>
              <strong>Risk Factors:</strong><br/>
              <ul style="margin: 4px 0; padding-left: 20px;">
                ${segment.risk_factors.map((f) => `<li>${f}</li>`).join('')}
              </ul>
            </div>
          `
          )
          .addTo(map);

        markersRef.current.routePolylines.push(polyline);
      });
    });

    // Fit bounds to all visible routes
    if (tacticalRoutes.length > 0) {
      const allCoords = tacticalRoutes
        .filter((r) => routeVisibility[r.route_id])
        .flatMap((r) => r.waypoints.map((wp) => [wp.lat, wp.lon] as [number, number]));

      if (allCoords.length > 0) {
        map.fitBounds(L.latLngBounds(allCoords), { padding: [50, 50] });
      }
    }

    return () => {
      markersRef.current.routePolylines.forEach((p) => map.removeLayer(p));
    };
  }, [tacticalRoutes, routeVisibility, planImages]);

  // Update SAM obstacle visualization overlay (NEW)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing SAM overlay
    if (markersRef.current.samOverlay) {
      map.removeLayer(markersRef.current.samOverlay);
      markersRef.current.samOverlay = null;
    }

    // Add new SAM overlay if available
    if (samVisualization && samVisualizationBounds) {
      const imageUrl = `data:image/png;base64,${samVisualization}`;
      const bounds: L.LatLngBoundsExpression = [
        [samVisualizationBounds.south, samVisualizationBounds.west],
        [samVisualizationBounds.north, samVisualizationBounds.east],
      ];

      markersRef.current.samOverlay = L.imageOverlay(imageUrl, bounds, {
        opacity: 0.6,
        interactive: false,
      }).addTo(map);
    }

    return () => {
      if (markersRef.current.samOverlay) {
        map.removeLayer(markersRef.current.samOverlay);
      }
    };
  }, [samVisualization, samVisualizationBounds]);

  // Gemini Route Image Overlay
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Remove overlays for plans that no longer exist
    Object.keys(markersRef.current.planOverlays).forEach((planIdStr) => {
      const planId = Number(planIdStr);
      if (!planImages[planId]) {
        map.removeLayer(markersRef.current.planOverlays[planId]);
        delete markersRef.current.planOverlays[planId];
      }
    });

    // Add/update overlays for all plan images
    Object.entries(planImages).forEach(([planIdStr, planData]) => {
      const planId = Number(planIdStr);

      // Skip if already rendered
      if (markersRef.current.planOverlays[planId]) {
        return;
      }

      const imageUrl = `data:image/png;base64,${planData.image}`;
      const bounds: L.LatLngBoundsExpression = [
        [planData.bounds.south, planData.bounds.west],
        [planData.bounds.north, planData.bounds.east],
      ];

      markersRef.current.planOverlays[planId] = L.imageOverlay(imageUrl, bounds, {
        opacity: 0.9,
        interactive: false,
      }).addTo(map);
    });

    return () => {
      Object.values(markersRef.current.planOverlays).forEach((overlay) => {
        map.removeLayer(overlay);
      });
      markersRef.current.planOverlays = {};
    };
  }, [planImages]);

  // Helper: Check if a point is inside a vision cone (polygon)
  const isPointInVisionCone = (
    pointLat: number,
    pointLng: number,
    enemy: SimEnemy
  ): boolean => {
    const specs = ENEMY_VISION_SPECS[enemy.type];
    const conePoints = calculateVisionCone(
      enemy.lat,
      enemy.lng,
      enemy.facing,
      specs.distance,
      specs.angle
    );

    // Ray casting algorithm to check if point is inside polygon
    let inside = false;
    const n = conePoints.length;
    for (let i = 0, j = n - 1; i < n; j = i++) {
      const [yi, xi] = conePoints[i] as [number, number];
      const [yj, xj] = conePoints[j] as [number, number];

      if (
        yi > pointLat !== yj > pointLat &&
        pointLng < ((xj - xi) * (pointLat - yi)) / (yj - yi) + xi
      ) {
        inside = !inside;
      }
    }
    return inside;
  };

  // Check if a route segment is exposed to any enemy vision
  const isSegmentExposed = (
    lat1: number,
    lng1: number,
    lat2: number,
    lng2: number,
    enemies: SimEnemy[]
  ): boolean => {
    // Check multiple points along the segment
    const numSamples = 5;
    for (let i = 0; i <= numSamples; i++) {
      const t = i / numSamples;
      const lat = lat1 + (lat2 - lat1) * t;
      const lng = lng1 + (lng2 - lng1) * t;

      for (const enemy of enemies) {
        if (isPointInVisionCone(lat, lng, enemy)) {
          return true;
        }
      }
    }
    return false;
  };

  // Render drawn route waypoints and smart-colored polyline
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing drawn route visualization
    markersRef.current.drawnWaypointMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.drawnWaypointMarkers = [];
    if (markersRef.current.drawnRoutePolyline) {
      map.removeLayer(markersRef.current.drawnRoutePolyline);
      markersRef.current.drawnRoutePolyline = null;
    }

    // Don't render if no waypoints
    if (drawnWaypoints.length === 0) return;

    // Create waypoint markers (larger, more visible)
    drawnWaypoints.forEach((wp, index) => {
      // All waypoints are blue (friendly color) - user's route
      let color = '#2563eb';
      let radius = 8;
      if (index === 0) {
        color = '#22c55e'; // Green for start
        radius = 10;
      } else if (index === drawnWaypoints.length - 1) {
        color = '#2563eb'; // Blue for end (friendly)
        radius = 10;
      }

      const marker = L.circleMarker([wp.lat, wp.lng], {
        radius,
        fillColor: color,
        fillOpacity: 1,
        color: '#ffffff',
        weight: 3,
        className: 'drawn-waypoint',
      })
        .on('drag', (e: any) => {
          const newPos = e.target.getLatLng();
          updateDrawnWaypoint(index, newPos.lat, newPos.lng);
        })
        .addTo(map);

      // Make draggable by adding custom drag behavior
      marker.on('mousedown', function(e) {
        map.dragging.disable();
        const onMove = (moveEvent: L.LeafletMouseEvent) => {
          marker.setLatLng(moveEvent.latlng);
        };
        const onUp = () => {
          map.dragging.enable();
          map.off('mousemove', onMove);
          map.off('mouseup', onUp);
          const newPos = marker.getLatLng();
          updateDrawnWaypoint(index, newPos.lat, newPos.lng);
        };
        map.on('mousemove', onMove);
        map.on('mouseup', onUp);
      });

      markersRef.current.drawnWaypointMarkers.push(marker);
    });

    // Create smart-colored connecting polylines
    // Before analysis: Amber = in danger zone, Green = clear
    // After analysis: Use actual cover status from segment_cover_analysis
    if (drawnWaypoints.length >= 2) {
      const polylines: L.Polyline[] = [];

      // Helper to get cover status color
      const getCoverStatusColor = (status: string) => {
        switch (status) {
          case 'exposed': return '#ef4444';    // Red - actually exposed
          case 'partial': return '#f59e0b';    // Amber - partial cover
          case 'covered': return '#22c55e';    // Green - covered by building/terrain
          case 'clear': return '#3b82f6';      // Blue - outside all cones
          default: return '#6b7280';           // Gray - unknown
        }
      };

      for (let i = 0; i < drawnWaypoints.length - 1; i++) {
        const wp1 = drawnWaypoints[i];
        const wp2 = drawnWaypoints[i + 1];

        // Check if we have AI analysis for this segment
        const segmentAnalysis = simulationResult?.segment_cover_analysis?.find(
          (sca) => sca.segment_index === i
        );

        let segmentColor: string;
        let tooltip: string;
        let dashArray: string;

        if (segmentAnalysis) {
          // AFTER analysis: Use actual cover status
          segmentColor = getCoverStatusColor(segmentAnalysis.cover_status);
          dashArray = segmentAnalysis.cover_status === 'exposed' ? '8, 8' : '12, 6';

          // Build detailed tooltip
          if (segmentAnalysis.cover_status === 'exposed') {
            tooltip = `EXPOSED - ${segmentAnalysis.explanation || 'No cover available'}`;
          } else if (segmentAnalysis.cover_status === 'covered') {
            tooltip = `COVERED - ${segmentAnalysis.blocking_feature || segmentAnalysis.cover_type || 'Protected'}`;
          } else if (segmentAnalysis.cover_status === 'partial') {
            tooltip = `PARTIAL COVER - ${segmentAnalysis.explanation || 'Some concealment'}`;
          } else {
            tooltip = 'CLEAR - Outside enemy vision';
          }
        } else {
          // BEFORE analysis: Use geometric check with amber for "in cone"
          const inCone = simEnemies.length > 0 && isSegmentExposed(
            wp1.lat, wp1.lng,
            wp2.lat, wp2.lng,
            simEnemies
          );

          if (inCone) {
            segmentColor = '#f59e0b';  // Amber - in danger zone (unknown cover)
            tooltip = 'IN DANGER ZONE - Run analysis to check for cover';
            dashArray = '8, 8';
          } else {
            segmentColor = '#22c55e';  // Green - clear
            tooltip = 'CLEAR - Outside enemy vision';
            dashArray = '12, 6';
          }
        }

        const polyline = L.polyline(
          [[wp1.lat, wp1.lng], [wp2.lat, wp2.lng]],
          {
            color: segmentColor,
            weight: 5,
            opacity: 0.9,
            dashArray,
          }
        ).addTo(map);

        // Add tooltip showing status
        polyline.bindTooltip(tooltip, {
          sticky: true,
          className: segmentColor === '#ef4444' ? 'exposed-tooltip' : 'safe-tooltip',
        });

        polylines.push(polyline);
      }

      // Store first polyline reference (we'll clean up all in return)
      markersRef.current.drawnRoutePolyline = polylines[0] || null;
      // Store the rest in a temp array for cleanup
      (markersRef.current as any).additionalPolylines = polylines.slice(1);
    }

    return () => {
      markersRef.current.drawnWaypointMarkers.forEach((m) => map.removeLayer(m));
      if (markersRef.current.drawnRoutePolyline) {
        map.removeLayer(markersRef.current.drawnRoutePolyline);
      }
      // Clean up additional polylines
      const additional = (markersRef.current as any).additionalPolylines;
      if (additional) {
        additional.forEach((p: L.Polyline) => map.removeLayer(p));
      }
    };
  }, [drawnWaypoints, updateDrawnWaypoint, simEnemies, simulationResult]);

  // Render route evaluation annotated image overlay
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing evaluation overlay
    if (markersRef.current.evaluationOverlay) {
      map.removeLayer(markersRef.current.evaluationOverlay);
      markersRef.current.evaluationOverlay = null;
    }

    // Add evaluation overlay if available
    if (routeEvaluation?.annotated_image && routeEvaluation?.annotated_image_bounds) {
      const imageUrl = `data:image/png;base64,${routeEvaluation.annotated_image}`;
      const bounds: L.LatLngBoundsExpression = [
        [routeEvaluation.annotated_image_bounds.south, routeEvaluation.annotated_image_bounds.west],
        [routeEvaluation.annotated_image_bounds.north, routeEvaluation.annotated_image_bounds.east],
      ];

      markersRef.current.evaluationOverlay = L.imageOverlay(imageUrl, bounds, {
        opacity: 0.95,
        interactive: false,
      }).addTo(map);

      // Fit map to the evaluation bounds
      map.fitBounds(bounds, { padding: [50, 50] });
    }

    return () => {
      if (markersRef.current.evaluationOverlay) {
        map.removeLayer(markersRef.current.evaluationOverlay);
      }
    };
  }, [routeEvaluation]);

  // Render simulation enemies with vision cones
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing simulation enemy elements
    markersRef.current.simEnemyMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.simEnemyVisionCones.forEach((c) => map.removeLayer(c));
    markersRef.current.simEnemyMarkers = [];
    markersRef.current.simEnemyVisionCones = [];

    // Create enemy markers and vision cones
    simEnemies.forEach((enemy) => {
      const specs = ENEMY_VISION_SPECS[enemy.type];

      // Calculate vision cone points
      const conePoints = calculateVisionCone(
        enemy.lat,
        enemy.lng,
        enemy.facing,
        specs.distance,
        specs.angle
      );

      // Create vision cone polygon
      const cone = L.polygon(conePoints, {
        color: specs.color,
        fillColor: specs.color,
        fillOpacity: 0.2,
        weight: 2,
        opacity: 0.6,
      }).addTo(map);

      markersRef.current.simEnemyVisionCones.push(cone);

      // Create enemy marker
      const marker = L.marker([enemy.lat, enemy.lng], {
        icon: createSimEnemyIcon(enemy.type, enemy.facing),
        draggable: true,
      })
        .on('dragend', (e) => {
          const newPos = (e.target as L.Marker).getLatLng();
          updateSimEnemyPosition(enemy.id, newPos.lat, newPos.lng);
        })
        .bindPopup(
          `<div style="text-align: center;">
            <strong>${enemy.type.toUpperCase()}</strong><br/>
            <small>Facing: ${enemy.facing}°</small><br/>
            <small>Range: ${specs.distance}m</small><br/>
            <button onclick="window.rotateEnemy('${enemy.id}')" style="margin-top: 4px; padding: 2px 8px; cursor: pointer;">
              Rotate +45°
            </button>
          </div>`
        )
        .addTo(map);

      markersRef.current.simEnemyMarkers.push(marker);
    });

    // Add rotation handler to window (for popup button)
    (window as any).rotateEnemy = (id: string) => {
      const enemy = simEnemies.find((e) => e.id === id);
      if (enemy) {
        updateSimEnemyFacing(id, (enemy.facing + 45) % 360);
      }
    };

    return () => {
      markersRef.current.simEnemyMarkers.forEach((m) => map.removeLayer(m));
      markersRef.current.simEnemyVisionCones.forEach((c) => map.removeLayer(c));
    };
  }, [simEnemies, updateSimEnemyPosition, updateSimEnemyFacing]);

  // Render simulation friendly units
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing friendly markers
    markersRef.current.simFriendlyMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.simFriendlyMarkers = [];

    // Create friendly markers
    simFriendlies.forEach((friendly) => {
      const marker = L.marker([friendly.lat, friendly.lng], {
        icon: createSimFriendlyIcon(friendly.type),
        draggable: true,
      })
        .on('dragend', (e) => {
          const newPos = (e.target as L.Marker).getLatLng();
          updateSimFriendlyPosition(friendly.id, newPos.lat, newPos.lng);
        })
        .bindPopup(`<strong>${friendly.type.toUpperCase()}</strong>`)
        .addTo(map);

      markersRef.current.simFriendlyMarkers.push(marker);
    });

    return () => {
      markersRef.current.simFriendlyMarkers.forEach((m) => map.removeLayer(m));
    };
  }, [simFriendlies, updateSimFriendlyPosition]);

  // Change cursor based on mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const container = map.getContainer();
    const interactiveModes = ['draw-route', 'place-soldier', 'place-enemy', 'place-sim-enemy', 'place-sim-friendly'];
    if (interactiveModes.includes(mapMode)) {
      container.style.cursor = 'crosshair';
    } else {
      container.style.cursor = '';
    }
  }, [mapMode]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />
      <ZoomIndicator map={mapInstanceRef.current} />
    </div>
  );
};
