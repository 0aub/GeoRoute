import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMission, getUnitDisplayName } from '@/hooks/useMission';
import { ZoomIndicator } from './ZoomIndicator';
import type { Coordinate, RiskLevel } from '@/types';

// Fix Leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Unit marker icons - NATO APP-6 style military symbols
const createUnitIcon = (isFriendly: boolean) => {
  if (isFriendly) {
    // NATO Friendly Unit: Blue rounded rectangle with infantry symbol
    return L.divIcon({
      className: 'custom-unit-marker',
      html: `
        <div style="
          width: 36px;
          height: 28px;
          background: #3b82f6;
          border: 2px solid white;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px rgba(0,0,0,0.4);
          cursor: move;
        ">
          <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
            <line x1="4" y1="14" x2="10" y2="2" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <line x1="16" y1="14" x2="10" y2="2" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
      `,
      iconSize: [36, 28],
      iconAnchor: [18, 14],
    });
  } else {
    // NATO Hostile Unit: Red diamond shape
    return L.divIcon({
      className: 'custom-unit-marker',
      html: `
        <div style="
          width: 32px;
          height: 32px;
          background: #ef4444;
          border: 2px solid white;
          transform: rotate(45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px rgba(0,0,0,0.4);
          cursor: move;
        ">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="transform: rotate(-45deg);">
            <circle cx="8" cy="8" r="3" fill="white"/>
          </svg>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  }
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
  }>({
    unitMarkers: [],
    routePolylines: [],
    samOverlay: null,
    planOverlays: {},
    drawnWaypointMarkers: [],
    drawnRoutePolyline: null,
    evaluationOverlay: null,
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
      if ((mapMode === 'place-soldier' || mapMode === 'place-enemy' || mapMode === 'draw-route') && !isInGulfRegion(coord.lat, coord.lon)) {
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
      }
    };

    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [mapMode, addSoldier, addEnemy, addDrawnWaypoint]);

  // Update unit markers - always show markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing unit markers
    markersRef.current.unitMarkers.forEach((m) => map.removeLayer(m));
    markersRef.current.unitMarkers = [];

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
  }, [soldiers, enemies, updateSoldierPosition, updateEnemyPosition]);

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

  // Render drawn route waypoints and polyline
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

    // Create waypoint markers
    drawnWaypoints.forEach((wp, index) => {
      // Color: first = blue, last = red, middle = white
      let color = '#ffffff';
      if (index === 0) color = '#3b82f6';
      else if (index === drawnWaypoints.length - 1) color = '#ef4444';

      const marker = L.circleMarker([wp.lat, wp.lng], {
        radius: 6,
        fillColor: color,
        fillOpacity: 1,
        color: '#ffffff',
        weight: 2,
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

    // Create connecting polyline (dashed blue)
    if (drawnWaypoints.length >= 2) {
      const coords = drawnWaypoints.map((wp) => [wp.lat, wp.lng] as [number, number]);
      markersRef.current.drawnRoutePolyline = L.polyline(coords, {
        color: '#3b82f6',
        weight: 3,
        opacity: 0.8,
        dashArray: '10, 6',
      }).addTo(map);
    }

    return () => {
      markersRef.current.drawnWaypointMarkers.forEach((m) => map.removeLayer(m));
      if (markersRef.current.drawnRoutePolyline) {
        map.removeLayer(markersRef.current.drawnRoutePolyline);
      }
    };
  }, [drawnWaypoints, updateDrawnWaypoint]);

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

  // Change cursor based on mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const container = map.getContainer();
    if (mapMode === 'draw-route') {
      container.style.cursor = 'crosshair';
    } else if (mapMode !== 'idle') {
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
