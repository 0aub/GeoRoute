import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMission } from '@/hooks/useMission';
import { ZoomIndicator } from './ZoomIndicator';
import type { Coordinate, NoGoZone, RiskLevel } from '@/types';

// Fix Leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom markers
const createIcon = (color: string, size: number = 24) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

const startIcon = createIcon('#22c55e', 28);
const endIcon = createIcon('#ef4444', 28);
const waypointIcon = (index: number) =>
  L.divIcon({
    className: 'waypoint-marker',
    html: `<div style="
      width: 24px;
      height: 24px;
      background: #3b82f6;
      border: 2px solid white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 11px;
      font-weight: bold;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    ">${index + 1}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

const hazardIcons = {
  low: L.divIcon({
    className: 'hazard-marker',
    html: `<div style="color: #eab308;">⚠</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  }),
  medium: L.divIcon({
    className: 'hazard-marker',
    html: `<div style="color: #f97316; font-size: 18px;">⚠</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  }),
  high: L.divIcon({
    className: 'hazard-marker',
    html: `<div style="color: #ef4444; font-size: 20px;">⚠</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  }),
  critical: L.divIcon({
    className: 'hazard-marker',
    html: `<div style="color: #ef4444; font-size: 20px;">☠</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  }),
};

// Unit marker icons (Simplified to Friendly/Enemy)
const createUnitIcon = (isFriendly: boolean) => {
  const color = isFriendly ? '#3b82f6' : '#ef4444'; // Blue for friendly, Red for enemy
  const emoji = isFriendly ? '👤' : '☠️'; // Person for friendly, skull for enemy

  return L.divIcon({
    className: 'custom-unit-marker',
    html: `
      <div style="
        width: 32px;
        height: 32px;
        background: ${color};
        border: 3px solid white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        cursor: move;
      ">${emoji}</div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Risk level to color mapping - Brand aligned and highly visible
const riskColorMap: Record<RiskLevel, string> = {
  safe: '#00A05A',      // Brand Light Green - safe/clear
  moderate: '#F5C623',  // Golden Yellow - caution
  high: '#FF6B00',      // Vivid Orange - warning
  critical: '#DC2626',  // Clear Red - danger
};

// Tile layers
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
    start: L.Marker | null;
    end: L.Marker | null;
    waypoints: L.Marker[];
    hazards: L.Marker[];
    route: L.Polyline | null;
    noGoZones: L.Polygon[];
    hoverMarker: L.CircleMarker | null;
    unitMarkers: L.Marker[]; // NEW: for soldiers and enemies
    routePolylines: L.Polyline[]; // NEW: for multi-route segments
  }>({
    start: null,
    end: null,
    waypoints: [],
    hazards: [],
    route: null,
    noGoZones: [],
    hoverMarker: null,
    unitMarkers: [],
    routePolylines: [],
  });
  const drawingPointsRef = useRef<L.LatLng[]>([]);
  const drawingPolygonRef = useRef<L.Polygon | null>(null);

  const {
    startPoint,
    endPoint,
    waypoints,
    noGoZones,
    routeResult,
    mapMode,
    hoveredDistance,
    setStartPoint,
    setEndPoint,
    addWaypoint,
    addNoGoZone,
    setMapMode,
    // Tactical state (NEW)
    soldiers,
    enemies,
    tacticalRoutes,
    routeVisibility,
    addSoldier,
    addEnemy,
    updateSoldierPosition,
    updateEnemyPosition,
    setCurrentZoom,
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

      // Validate Gulf region for tactical operations
      if ((mapMode === 'place-soldier' || mapMode === 'place-enemy') && !isInGulfRegion(coord.lat, coord.lon)) {
        // Show popup at click location
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

      switch (mapMode) {
        case 'set-start':
          setStartPoint(coord);
          break;
        case 'set-end':
          setEndPoint(coord);
          break;
        case 'add-waypoint':
          addWaypoint(coord);
          break;
        case 'draw-no-go':
          drawingPointsRef.current.push(e.latlng);
          updateDrawingPolygon(map);
          break;
        case 'place-soldier':
          addSoldier({
            lat: coord.lat,
            lon: coord.lon,
            is_friendly: true,
          });
          break;
        case 'place-enemy':
          addEnemy({
            lat: coord.lat,
            lon: coord.lon,
            is_friendly: false,
          });
          break;
      }
    };

    const handleDblClick = (e: L.LeafletMouseEvent) => {
      if (mapMode === 'draw-no-go' && drawingPointsRef.current.length >= 3) {
        e.originalEvent.preventDefault();
        const zone: NoGoZone = {
          id: crypto.randomUUID(),
          coordinates: drawingPointsRef.current.map((p) => ({
            lat: p.lat,
            lon: p.lng,
          })),
        };
        addNoGoZone(zone);
        drawingPointsRef.current = [];
        if (drawingPolygonRef.current) {
          map.removeLayer(drawingPolygonRef.current);
          drawingPolygonRef.current = null;
        }
        setMapMode('idle');
      }
    };

    map.on('click', handleClick);
    map.on('dblclick', handleDblClick);

    return () => {
      map.off('click', handleClick);
      map.off('dblclick', handleDblClick);
    };
  }, [
    mapMode,
    setStartPoint,
    setEndPoint,
    addWaypoint,
    addNoGoZone,
    setMapMode,
    addSoldier,
    addEnemy,
  ]);

  const updateDrawingPolygon = (map: L.Map) => {
    if (drawingPolygonRef.current) {
      map.removeLayer(drawingPolygonRef.current);
    }
    if (drawingPointsRef.current.length > 0) {
      drawingPolygonRef.current = L.polygon(drawingPointsRef.current, {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.3,
        dashArray: '5, 5',
      }).addTo(map);
    }
  };

  // Update start marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (markersRef.current.start) {
      map.removeLayer(markersRef.current.start);
      markersRef.current.start = null;
    }

    if (startPoint) {
      markersRef.current.start = L.marker([startPoint.lat, startPoint.lon], {
        icon: startIcon,
      })
        .addTo(map)
        .bindPopup('<strong>Start Point</strong>');
    }
  }, [startPoint]);

  // Update end marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (markersRef.current.end) {
      map.removeLayer(markersRef.current.end);
      markersRef.current.end = null;
    }

    if (endPoint) {
      markersRef.current.end = L.marker([endPoint.lat, endPoint.lon], {
        icon: endIcon,
      })
        .addTo(map)
        .bindPopup('<strong>End Point</strong>');
    }
  }, [endPoint]);

  // Update waypoint markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    markersRef.current.waypoints.forEach((m) => map.removeLayer(m));
    markersRef.current.waypoints = [];

    waypoints.forEach((wp, index) => {
      const marker = L.marker([wp.lat, wp.lon], {
        icon: waypointIcon(index),
      })
        .addTo(map)
        .bindPopup(`<strong>Waypoint ${index + 1}</strong>`);
      markersRef.current.waypoints.push(marker);
    });
  }, [waypoints]);

  // Update no-go zones
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    markersRef.current.noGoZones.forEach((p) => map.removeLayer(p));
    markersRef.current.noGoZones = [];

    noGoZones.forEach((zone) => {
      const polygon = L.polygon(
        zone.coordinates.map((c) => [c.lat, c.lon] as [number, number]),
        {
          color: '#ef4444',
          fillColor: '#ef4444',
          fillOpacity: 0.3,
          weight: 2,
        }
      ).addTo(map);
      markersRef.current.noGoZones.push(polygon);
    });
  }, [noGoZones]);

  // Update unit markers (NEW for tactical planning)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing unit markers
    markersRef.current.unitMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.unitMarkers = [];

    // Create soldier markers (draggable, blue)
    soldiers.forEach((soldier) => {
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
        .bindPopup('<strong>Friendly Unit</strong>')
        .addTo(map);

      markersRef.current.unitMarkers.push(marker);
    });

    // Create enemy markers (draggable, red)
    enemies.forEach((enemy) => {
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
        .bindPopup('<strong>Enemy Unit</strong>')
        .addTo(map);

      markersRef.current.unitMarkers.push(marker);
    });

    return () => {
      markersRef.current.unitMarkers.forEach((m) => map.removeLayer(m));
    };
  }, [soldiers, enemies, updateSoldierPosition, updateEnemyPosition]);

  // Update route and hazards (LEGACY - for backward compatibility)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing route
    if (markersRef.current.route) {
      map.removeLayer(markersRef.current.route);
      markersRef.current.route = null;
    }

    // Clear existing hazards
    markersRef.current.hazards.forEach((m) => map.removeLayer(m));
    markersRef.current.hazards = [];

    if (routeResult) {
      // Draw route
      const routeCoords = routeResult.coordinates.map(
        (c) => [c.lat, c.lon] as [number, number]
      );
      markersRef.current.route = L.polyline(routeCoords, {
        color: '#3b82f6',
        weight: 4,
        opacity: 0.9,
      }).addTo(map);

      // Fit bounds to route
      if (routeCoords.length > 0) {
        map.fitBounds(L.latLngBounds(routeCoords), { padding: [50, 50] });
      }

      // Add hazard markers
      routeResult.hazards.forEach((hazard) => {
        const marker = L.marker([hazard.lat, hazard.lon], {
          icon: hazardIcons[hazard.severity],
        })
          .addTo(map)
          .bindPopup(`
            <div style="min-width: 200px;">
              <strong style="color: ${
                hazard.severity === 'critical'
                  ? '#ef4444'
                  : hazard.severity === 'high'
                  ? '#f97316'
                  : '#eab308'
              }">
                ${hazard.severity.toUpperCase()} HAZARD
              </strong>
              <p style="margin: 8px 0;">${hazard.description}</p>
              <hr style="border-color: #333; margin: 8px 0;" />
              <strong>Mitigation:</strong>
              <p style="margin-top: 4px;">${hazard.mitigation}</p>
            </div>
          `);
        markersRef.current.hazards.push(marker);
      });
    }
  }, [routeResult]);

  // Update tactical routes (NEW - multi-route with color-coded segments)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || tacticalRoutes.length === 0) return;

    // Clear existing route polylines
    markersRef.current.routePolylines.forEach((p) => map.removeLayer(p));
    markersRef.current.routePolylines = [];

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
  }, [tacticalRoutes, routeVisibility]);

  // Update hover marker based on elevation chart hover
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !routeResult?.elevationProfile) return;

    if (markersRef.current.hoverMarker) {
      map.removeLayer(markersRef.current.hoverMarker);
      markersRef.current.hoverMarker = null;
    }

    if (hoveredDistance !== null && routeResult.coordinates.length > 0) {
      // Find the closest point on the route
      const totalDist = routeResult.elevationProfile[routeResult.elevationProfile.length - 1]?.distance || 0;
      const ratio = hoveredDistance / totalDist;
      const index = Math.floor(ratio * (routeResult.coordinates.length - 1));
      const coord = routeResult.coordinates[Math.min(index, routeResult.coordinates.length - 1)];

      if (coord) {
        markersRef.current.hoverMarker = L.circleMarker([coord.lat, coord.lon], {
          radius: 8,
          color: '#fff',
          fillColor: '#3b82f6',
          fillOpacity: 1,
          weight: 2,
        }).addTo(map);
      }
    }
  }, [hoveredDistance, routeResult]);

  // Change cursor based on mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const container = map.getContainer();
    if (mapMode !== 'idle') {
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
