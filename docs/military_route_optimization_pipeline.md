# Military Route Optimization Pipeline with Gemini API
## Complete Technical Guide - All Free Services

---

## Executive Summary

This guide provides a production-ready pipeline for building a terrain-aware military route optimization system. The core problem: **Gemini can identify mountains visually but doesn't know they're impassable**. The solution feeds Gemini structured geospatial data (elevation, slope, roads) alongside satellite imagery, enabling intelligent routing decisions grounded in physical geography.

**All services used are FREE:**

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Google Maps Platform | Elevation + Satellite images | $200/month credit (~40,000 calls) |
| Google Gemini API | AI reasoning engine | Free via AI Studio |
| OSRM | Route validation | 100% free, no API key |
| Google Earth Engine | Advanced terrain analysis | Free for non-commercial |
| OpenRouteService | Elevation profiles + surfaces | 2,000 requests/day free |
| OpenTopography | DEM file downloads | 300 requests/day free |

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites & Setup](#2-prerequisites--setup)
3. [Data Acquisition Layer](#3-data-acquisition-layer)
4. [Terrain Processing Layer](#4-terrain-processing-layer)
5. [Gemini Integration Layer](#5-gemini-integration-layer)
6. [Route Validation Layer](#6-route-validation-layer)
7. [Complete Pipeline Integration](#7-complete-pipeline-integration)
8. [Working Example with Dummy Data](#8-working-example-with-dummy-data)
9. [Touchscreen Interface Integration](#9-touchscreen-interface-integration)
10. [Appendix: API Reference](#10-appendix-api-reference)

---

## 1. Architecture Overview

### The Core Problem

When you feed Gemini a satellite image and ask it to plan a route:
- It sees mountains as **visual features** (colors, textures, shadows)
- It does NOT understand they represent **elevation barriers**
- It draws routes over mountains because pixels look traversable

### The Solution

Feed Gemini **TWO inputs**:
1. **Satellite Image** → Visual context (current conditions, obstacles, flooding)
2. **Structured JSON** → Quantitative terrain data (elevation, slope, roads)

The prompt explicitly tells Gemini: *"Trust the elevation data over visual estimates."*

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INPUT                                    │
│  • Start point (lat, lon)                                       │
│  • End point (lat, lon)                                         │
│  • Vehicle type                                                 │
│  • Optional: waypoints, no-go zones                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               DATA ACQUISITION LAYER                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Google Maps  │  │ Earth Engine │  │ OpenTopo     │           │
│  │ • Satellite  │  │ • SRTM DEM   │  │ • DEM files  │           │
│  │ • Elevation  │  │ • Land cover │  │ • Offline    │           │
│  │ • Roads      │  │ • Terrain    │  │   processing │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               TERRAIN PROCESSING LAYER                           │
│                                                                  │
│  • Calculate slope from elevation                                │
│  • Classify traversability (easy/moderate/difficult/impassable) │
│  • Extract elevation profiles along potential paths             │
│  • Identify terrain types (forest, rock, water, urban)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               GEMINI INTEGRATION LAYER                           │
│                                                                  │
│  INPUT:                                                         │
│  ┌─────────────┐  ┌─────────────────────────────────┐           │
│  │  Satellite  │  │  Structured JSON:               │           │
│  │   Image     │  │  • Elevation statistics         │           │
│  │  (visual)   │  │  • Slope analysis               │           │
│  │             │  │  • Road network                 │           │
│  │             │  │  • Land cover %                 │           │
│  │             │  │  • Vehicle constraints          │           │
│  └─────────────┘  └─────────────────────────────────┘           │
│                                                                  │
│  OUTPUT: RoutingDecision (waypoints, hazards, reasoning)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               ROUTE VALIDATION LAYER                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │    OSRM     │  │ OpenRoute    │                             │
│  │ • Snap to   │  │ • Elevation  │                             │
│  │   roads     │  │   profiles   │                             │
│  │ • Validate  │  │ • Surface    │                             │
│  │   path      │  │   types      │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUT                                  │
│  • Optimized route with waypoints                               │
│  • Terrain assessment per segment                               │
│  • Hazard warnings                                              │
│  • Alternative routes                                           │
│  • Confidence scores                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites & Setup

### Required Accounts (All Free)

#### 1. Google Cloud Platform
- Go to: https://console.cloud.google.com
- Create new project
- Enable billing (required for API access, but $200 free credit covers everything)
- Enable these APIs:
  - Maps Elevation API
  - Maps Static API  
  - Directions API
  - Roads API

#### 2. Google AI Studio (Gemini)
- Go to: https://aistudio.google.com
- Sign in with Google account
- Get API key (free tier is generous)

#### 3. Google Earth Engine
- Go to: https://earthengine.google.com
- Click "Sign Up"
- Select "Noncommercial" → Free
- Wait for approval (usually 1-2 days)
- Once approved, enable Earth Engine API in Cloud Console

#### 4. OpenRouteService
- Go to: https://openrouteservice.org/dev
- Register for free account
- Get API key (2,000 requests/day free)

#### 5. OpenTopography
- Go to: https://opentopography.org
- Create account
- Request API key (300 requests/day free)

### Environment Variables

Create a `.env` file:

```bash
# Required
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
GEMINI_API_KEY=your-gemini-api-key

# Optional but recommended
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
ORS_API_KEY=your-openrouteservice-api-key
OPENTOPOGRAPHY_API_KEY=your-opentopography-api-key
```

### Python Dependencies

```bash
pip install requests numpy rasterio richdem google-genai openrouteservice earthengine-api pydantic python-dotenv
```

### Load Environment

```python
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ORS_API_KEY = os.environ.get('ORS_API_KEY')
OPENTOPOGRAPHY_API_KEY = os.environ.get('OPENTOPOGRAPHY_API_KEY')
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
```

---

## 3. Data Acquisition Layer

### 3.1 Google Maps Client

This is your primary data source for elevation and satellite imagery.

```python
import requests
import os
from typing import List, Tuple, Dict, Optional
import math

class GoogleMapsClient:
    """
    Client for Google Maps Platform APIs.
    Provides elevation data, satellite imagery, and road routing.
    
    FREE TIER: $200/month credit covers approximately:
    - 40,000 elevation API calls
    - 100,000 static map loads
    - 40,000 directions requests
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('GOOGLE_MAPS_API_KEY')
        if not self.api_key:
            raise ValueError("Google Maps API key required")
        
        # API endpoints
        self.elevation_url = "https://maps.googleapis.com/maps/api/elevation/json"
        self.static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
        self.directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    def get_elevation_at_points(self, coordinates: List[Tuple[float, float]]) -> Dict:
        """
        Get elevation at specific coordinate points.
        
        Args:
            coordinates: List of (lat, lon) tuples (max 512 per request)
        
        Returns:
            Dict with elevations and metadata
        """
        if len(coordinates) > 512:
            raise ValueError("Maximum 512 coordinates per request")
        
        locations = "|".join([f"{lat},{lon}" for lat, lon in coordinates])
        
        params = {
            "locations": locations,
            "key": self.api_key
        }
        
        response = requests.get(self.elevation_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            return {
                "success": True,
                "elevations": [
                    {
                        "lat": r['location']['lat'],
                        "lon": r['location']['lng'],
                        "elevation_m": r['elevation'],
                        "resolution_m": r.get('resolution', 30)
                    }
                    for r in data['results']
                ]
            }
        return {"success": False, "error": data['status']}
    
    def get_elevation_profile(
        self, 
        path_coords: List[Tuple[float, float]], 
        samples: int = 100
    ) -> Dict:
        """
        Extract elevation profile along a route path.
        Google will interpolate elevations between your coordinates.
        
        Args:
            path_coords: List of (lat, lon) tuples defining the path
            samples: Number of equidistant sample points (max 512)
        
        Returns:
            Dict with elevation profile data
        """
        path_str = "|".join([f"{lat},{lon}" for lat, lon in path_coords])
        
        params = {
            "path": path_str,
            "samples": min(samples, 512),
            "key": self.api_key
        }
        
        response = requests.get(self.elevation_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            elevations = [r['elevation'] for r in data['results']]
            locations = [(r['location']['lat'], r['location']['lng']) 
                        for r in data['results']]
            
            # Calculate elevation statistics
            elevation_changes = [elevations[i+1] - elevations[i] 
                                for i in range(len(elevations)-1)]
            
            return {
                "success": True,
                "elevations_m": elevations,
                "locations": locations,
                "resolution_m": data['results'][0].get('resolution', 30),
                "statistics": {
                    "min_elevation_m": min(elevations),
                    "max_elevation_m": max(elevations),
                    "total_ascent_m": sum(c for c in elevation_changes if c > 0),
                    "total_descent_m": abs(sum(c for c in elevation_changes if c < 0)),
                    "max_elevation_change_m": max(abs(c) for c in elevation_changes) if elevation_changes else 0
                }
            }
        return {"success": False, "error": data['status']}
    
    def get_satellite_image(
        self,
        center: Tuple[float, float],
        zoom: int = 14,
        size: str = "640x640",
        scale: int = 2,
        map_type: str = "satellite"
    ) -> Optional[bytes]:
        """
        Retrieve satellite or terrain imagery for a location.
        
        Args:
            center: (lat, lon) tuple for map center
            zoom: Zoom level (1-21, higher = more detail)
                  14 = ~10km view, 16 = ~2.5km view, 18 = ~600m view
            size: Image dimensions (max 640x640)
            scale: 1 or 2 (2 = high DPI, actual image is 1280x1280)
            map_type: "satellite", "terrain", "roadmap", "hybrid"
        
        Returns:
            Image bytes (JPEG) or None if failed
        """
        params = {
            "center": f"{center[0]},{center[1]}",
            "zoom": zoom,
            "size": size,
            "maptype": map_type,
            "scale": scale,
            "key": self.api_key
        }
        
        response = requests.get(self.static_maps_url, params=params)
        
        if response.status_code == 200:
            return response.content
        return None
    
    def get_terrain_image(
        self,
        center: Tuple[float, float],
        zoom: int = 12
    ) -> Optional[bytes]:
        """
        Get terrain map showing elevation contours and shading.
        Useful as secondary image for Gemini to understand topology.
        """
        return self.get_satellite_image(
            center=center,
            zoom=zoom,
            map_type="terrain"
        )
    
    def get_road_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None,
        avoid: List[str] = None
    ) -> Dict:
        """
        Get road-based route with turn-by-turn segments.
        
        Args:
            origin: (lat, lon) start point
            destination: (lat, lon) end point
            waypoints: Optional intermediate points
            avoid: List of features to avoid: "tolls", "highways", "ferries"
        
        Returns:
            Route data including distance, duration, and steps
        """
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "mode": "driving",
            "key": self.api_key
        }
        
        if waypoints:
            wp_str = "|".join([f"{w[0]},{w[1]}" for w in waypoints])
            params["waypoints"] = f"optimize:true|{wp_str}"
        
        if avoid:
            params["avoid"] = "|".join(avoid)
        
        response = requests.get(self.directions_url, params=params)
        data = response.json()
        
        if data.get('status') == 'OK' and data.get('routes'):
            route = data['routes'][0]
            leg = route['legs'][0]
            
            return {
                "success": True,
                "distance_m": leg['distance']['value'],
                "duration_s": leg['duration']['value'],
                "start_address": leg.get('start_address'),
                "end_address": leg.get('end_address'),
                "steps": [
                    {
                        "instruction": step.get('html_instructions', ''),
                        "distance_m": step['distance']['value'],
                        "duration_s": step['duration']['value'],
                        "start_location": (
                            step['start_location']['lat'],
                            step['start_location']['lng']
                        ),
                        "end_location": (
                            step['end_location']['lat'],
                            step['end_location']['lng']
                        )
                    }
                    for step in leg.get('steps', [])
                ],
                "polyline": route.get('overview_polyline', {}).get('points')
            }
        return {"success": False, "error": data.get('status', 'Unknown error')}
    
    def get_elevation_grid(
        self,
        bounds: Tuple[float, float, float, float],
        grid_size: int = 10
    ) -> Dict:
        """
        Get elevation data for a grid of points covering an area.
        
        Args:
            bounds: (south, north, west, east) bounding box
            grid_size: Number of points per side (total = grid_size^2)
        
        Returns:
            Grid of elevation data with statistics
        """
        south, north, west, east = bounds
        
        # Generate grid points
        lat_step = (north - south) / (grid_size - 1)
        lon_step = (east - west) / (grid_size - 1)
        
        grid_points = []
        for i in range(grid_size):
            for j in range(grid_size):
                lat = south + (i * lat_step)
                lon = west + (j * lon_step)
                grid_points.append((lat, lon))
        
        # Get elevations (may need multiple calls if > 512 points)
        all_elevations = []
        for i in range(0, len(grid_points), 512):
            batch = grid_points[i:i+512]
            result = self.get_elevation_at_points(batch)
            if result['success']:
                all_elevations.extend(result['elevations'])
        
        if all_elevations:
            elevs = [e['elevation_m'] for e in all_elevations]
            return {
                "success": True,
                "bounds": bounds,
                "grid_size": grid_size,
                "points": all_elevations,
                "statistics": {
                    "min_elevation_m": min(elevs),
                    "max_elevation_m": max(elevs),
                    "mean_elevation_m": sum(elevs) / len(elevs),
                    "elevation_range_m": max(elevs) - min(elevs)
                }
            }
        return {"success": False, "error": "Failed to get elevations"}
```

### 3.2 Google Earth Engine Client

Advanced terrain analysis with global datasets.

```python
import ee

class EarthEngineClient:
    """
    Client for Google Earth Engine.
    Provides access to SRTM elevation data, land cover, and terrain analysis.
    
    FREE TIER: Completely free for non-commercial use.
    Requires approval (1-2 days).
    """
    
    def __init__(self, project_id: str = None):
        """
        Initialize Earth Engine client.
        First time: Run ee.Authenticate() to login via browser.
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        
        try:
            ee.Initialize(project=self.project_id)
        except Exception:
            print("First time setup: Authenticating with Earth Engine...")
            ee.Authenticate()
            ee.Initialize(project=self.project_id)
    
    def get_terrain_analysis(self, bounds: List[float]) -> Dict:
        """
        Comprehensive terrain analysis for a bounding box.
        
        Args:
            bounds: [west, south, east, north] in degrees
        
        Returns:
            Dict with elevation statistics and slope analysis
        """
        aoi = ee.Geometry.Rectangle(bounds)
        
        # Load SRTM 30m DEM
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi)
        
        # Calculate terrain derivatives
        slope = ee.Terrain.slope(dem)
        aspect = ee.Terrain.aspect(dem)
        
        # Calculate statistics
        stats = dem.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.minMax(), sharedInputs=True
            ).combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        slope_stats = slope.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.minMax(), sharedInputs=True
            ),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        return {
            "source": "USGS SRTM 30m",
            "bounds": bounds,
            "elevation": {
                "min_m": stats.get('elevation_min'),
                "max_m": stats.get('elevation_max'),
                "mean_m": stats.get('elevation_mean'),
                "std_dev_m": stats.get('elevation_stdDev')
            },
            "slope": {
                "min_deg": slope_stats.get('slope_min'),
                "max_deg": slope_stats.get('slope_max'),
                "mean_deg": slope_stats.get('slope_mean')
            }
        }
    
    def get_slope_distribution(self, bounds: List[float]) -> Dict:
        """
        Calculate what percentage of terrain falls into each slope category.
        Critical for understanding traversability.
        """
        aoi = ee.Geometry.Rectangle(bounds)
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi)
        slope = ee.Terrain.slope(dem)
        
        # Classify slope into categories
        slope_classes = (
            slope.lt(5).multiply(1)
            .add(slope.gte(5).And(slope.lt(15)).multiply(2))
            .add(slope.gte(15).And(slope.lt(30)).multiply(3))
            .add(slope.gte(30).And(slope.lt(45)).multiply(4))
            .add(slope.gte(45).multiply(5))
        )
        
        # Count pixels in each class
        histogram = slope_classes.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        hist_data = histogram.get('slope', {})
        total = sum(hist_data.values()) if hist_data else 1
        
        return {
            "flat_0_5_deg_pct": hist_data.get('1', 0) / total,
            "gentle_5_15_deg_pct": hist_data.get('2', 0) / total,
            "moderate_15_30_deg_pct": hist_data.get('3', 0) / total,
            "steep_30_45_deg_pct": hist_data.get('4', 0) / total,
            "very_steep_45_plus_pct": hist_data.get('5', 0) / total
        }
    
    def get_land_cover(self, bounds: List[float]) -> Dict:
        """
        Extract ESA WorldCover land cover percentages.
        10m resolution global land cover map.
        """
        aoi = ee.Geometry.Rectangle(bounds)
        worldcover = ee.ImageCollection('ESA/WorldCover/v200').first().clip(aoi)
        
        histogram = worldcover.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=aoi,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        # ESA WorldCover class codes
        class_names = {
            '10': 'tree_cover',
            '20': 'shrubland', 
            '30': 'grassland',
            '40': 'cropland',
            '50': 'built_up',
            '60': 'bare_sparse_vegetation',
            '70': 'snow_ice',
            '80': 'water',
            '90': 'herbaceous_wetland',
            '95': 'mangroves',
            '100': 'moss_lichen'
        }
        
        hist_data = histogram.get('Map', {})
        total = sum(hist_data.values()) if hist_data else 1
        
        return {
            class_names.get(k, f'class_{k}'): v / total
            for k, v in hist_data.items()
        }
    
    def get_elevation_along_path(
        self, 
        coordinates: List[Tuple[float, float]]
    ) -> List[Dict]:
        """
        Sample elevation at specific coordinate points using SRTM.
        
        Args:
            coordinates: List of (lon, lat) pairs - NOTE: lon first!
        
        Returns:
            List of elevation samples
        """
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation')
        
        # Create point features
        features = [
            ee.Feature(ee.Geometry.Point([lon, lat]))  # GEE uses [lon, lat]
            for lon, lat in coordinates
        ]
        points = ee.FeatureCollection(features)
        
        # Sample elevations
        sampled = dem.sampleRegions(
            collection=points,
            scale=30,
            geometries=True
        ).getInfo()
        
        return [
            {
                "lon": f['geometry']['coordinates'][0],
                "lat": f['geometry']['coordinates'][1],
                "elevation_m": f['properties']['elevation']
            }
            for f in sampled['features']
        ]
```

### 3.3 OpenTopography Client

Download DEM files for offline processing.

```python
class OpenTopographyClient:
    """
    Client for OpenTopography API.
    Download DEM tiles for offline terrain processing.
    
    FREE TIER: 300 requests/day (academic use).
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('OPENTOPOGRAPHY_API_KEY')
        self.base_url = "https://portal.opentopography.org/API/globaldem"
    
    def download_dem(
        self,
        bounds: Tuple[float, float, float, float],
        output_path: str,
        dem_type: str = "SRTMGL1"
    ) -> Optional[str]:
        """
        Download DEM file for a region.
        
        Args:
            bounds: (south, north, west, east) bounding box
            output_path: Where to save the GeoTIFF file
            dem_type: One of:
                - "SRTMGL1" (30m, recommended)
                - "SRTMGL3" (90m)
                - "AW3D30" (30m ALOS)
                - "COP30" (30m Copernicus)
                - "NASADEM" (30m)
        
        Returns:
            Path to downloaded file or None
        """
        params = {
            "demtype": dem_type,
            "south": bounds[0],
            "north": bounds[1],
            "west": bounds[2],
            "east": bounds[3],
            "outputFormat": "GTiff",
            "API_Key": self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return output_path
        
        print(f"Download failed: {response.status_code} - {response.text}")
        return None
```

---

## 4. Terrain Processing Layer

### 4.1 Local DEM Processor

Process downloaded DEM files for detailed terrain analysis.

```python
import numpy as np

class LocalDEMProcessor:
    """
    Process local DEM files for terrain analysis.
    Use when you need offline capability or very detailed analysis.
    
    Requires: rasterio, richdem
    """
    
    def __init__(self, dem_path: str):
        self.dem_path = dem_path
        self._load_dem()
    
    def _load_dem(self):
        """Load DEM and extract metadata."""
        import rasterio
        
        with rasterio.open(self.dem_path) as src:
            self.dem_data = src.read(1).astype(float)
            self.transform = src.transform
            self.crs = src.crs
            self.bounds = src.bounds
            self.resolution = src.res
            
            # Handle nodata
            nodata = src.nodata
            if nodata is not None:
                self.dem_data[self.dem_data == nodata] = np.nan
    
    def get_elevation_at_point(self, lat: float, lon: float) -> Optional[float]:
        """Get elevation at a specific coordinate."""
        from rasterio.transform import rowcol
        
        row, col = rowcol(self.transform, lon, lat)
        
        if 0 <= row < self.dem_data.shape[0] and 0 <= col < self.dem_data.shape[1]:
            elev = self.dem_data[row, col]
            return float(elev) if not np.isnan(elev) else None
        return None
    
    def calculate_slope(self) -> np.ndarray:
        """
        Calculate slope in degrees using gradient method.
        """
        # Calculate gradients
        dy, dx = np.gradient(self.dem_data, self.resolution[0])
        
        # Calculate slope magnitude
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_deg = np.degrees(slope_rad)
        
        return slope_deg
    
    def classify_traversability(self, vehicle_max_slope: float = 30) -> np.ndarray:
        """
        Classify terrain traversability based on slope.
        
        Returns array where:
        1 = Easy (0-5°)
        2 = Moderate (5-15°)  
        3 = Difficult (15-30°)
        4 = Very Difficult (30-45°)
        5 = Impassable (>45°)
        
        Args:
            vehicle_max_slope: Maximum slope the vehicle can handle
        """
        slope = self.calculate_slope()
        
        traversability = np.zeros_like(slope, dtype=np.uint8)
        traversability[slope <= 5] = 1
        traversability[(slope > 5) & (slope <= 15)] = 2
        traversability[(slope > 15) & (slope <= 30)] = 3
        traversability[(slope > 30) & (slope <= 45)] = 4
        traversability[slope > 45] = 5
        
        return traversability
    
    def get_terrain_profile(
        self, 
        coordinates: List[Tuple[float, float]]
    ) -> Dict:
        """
        Extract terrain profile along a path.
        
        Args:
            coordinates: List of (lat, lon) tuples
        
        Returns:
            Dict with elevations, slopes, and distances
        """
        from rasterio.transform import rowcol
        
        slope_arr = self.calculate_slope()
        
        elevations = []
        slopes = []
        distances = [0]
        
        for i, (lat, lon) in enumerate(coordinates):
            row, col = rowcol(self.transform, lon, lat)
            
            if 0 <= row < self.dem_data.shape[0] and 0 <= col < self.dem_data.shape[1]:
                elev = self.dem_data[row, col]
                slp = slope_arr[row, col]
                
                elevations.append(float(elev) if not np.isnan(elev) else None)
                slopes.append(float(slp) if not np.isnan(slp) else None)
                
                if i > 0:
                    dist = self._haversine(
                        coordinates[i-1][0], coordinates[i-1][1],
                        lat, lon
                    )
                    distances.append(distances[-1] + dist)
            else:
                elevations.append(None)
                slopes.append(None)
        
        # Calculate statistics
        valid_elevs = [e for e in elevations if e is not None]
        valid_slopes = [s for s in slopes if s is not None]
        
        elevation_changes = [
            valid_elevs[i+1] - valid_elevs[i] 
            for i in range(len(valid_elevs)-1)
        ]
        
        return {
            "coordinates": coordinates,
            "elevations_m": elevations,
            "slopes_deg": slopes,
            "cumulative_distance_m": distances,
            "statistics": {
                "total_distance_m": distances[-1] if distances else 0,
                "min_elevation_m": min(valid_elevs) if valid_elevs else None,
                "max_elevation_m": max(valid_elevs) if valid_elevs else None,
                "elevation_gain_m": sum(c for c in elevation_changes if c > 0),
                "elevation_loss_m": abs(sum(c for c in elevation_changes if c < 0)),
                "max_slope_deg": max(valid_slopes) if valid_slopes else None,
                "mean_slope_deg": sum(valid_slopes)/len(valid_slopes) if valid_slopes else None
            }
        }
    
    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        return 2 * R * np.arcsin(np.sqrt(a))
    
    def get_statistics(self) -> Dict:
        """Get overall DEM statistics."""
        slope = self.calculate_slope()
        
        return {
            "bounds": {
                "south": self.bounds.bottom,
                "north": self.bounds.top,
                "west": self.bounds.left,
                "east": self.bounds.right
            },
            "resolution_m": self.resolution[0],
            "elevation": {
                "min_m": float(np.nanmin(self.dem_data)),
                "max_m": float(np.nanmax(self.dem_data)),
                "mean_m": float(np.nanmean(self.dem_data)),
                "std_dev_m": float(np.nanstd(self.dem_data))
            },
            "slope": {
                "min_deg": float(np.nanmin(slope)),
                "max_deg": float(np.nanmax(slope)),
                "mean_deg": float(np.nanmean(slope))
            }
        }
```

---

## 5. Gemini Integration Layer

### 5.1 Structured Output Models

Define the exact JSON structure Gemini should return.

```python
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum

class TraversabilityLevel(str, Enum):
    EASY = "easy"
    MODERATE = "moderate"
    DIFFICULT = "difficult"
    VERY_DIFFICULT = "very_difficult"
    IMPASSABLE = "impassable"

class HazardSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RouteWaypoint(BaseModel):
    """A single waypoint along the route."""
    lat: float = Field(description="Latitude in decimal degrees")
    lon: float = Field(description="Longitude in decimal degrees")
    elevation_m: float = Field(description="Elevation in meters")
    distance_from_start_km: float = Field(description="Cumulative distance from start")
    terrain_type: str = Field(description="Dominant terrain: road, trail, off-road, etc.")
    surface_type: str = Field(description="Surface: asphalt, gravel, dirt, rock, etc.")
    traversability: TraversabilityLevel
    slope_deg: Optional[float] = Field(description="Slope at this point in degrees")
    notes: Optional[str] = Field(description="Special considerations for this waypoint")

class TerrainHazard(BaseModel):
    """A hazard identified along or near the route."""
    hazard_type: str = Field(description="Type: steep_slope, water_crossing, cliff, etc.")
    severity: HazardSeverity
    lat: float
    lon: float
    description: str
    mitigation: Optional[str] = Field(description="How to handle this hazard")

class RouteSegment(BaseModel):
    """A segment of the route between waypoints."""
    segment_id: int
    start_waypoint: int = Field(description="Index of start waypoint")
    end_waypoint: int = Field(description="Index of end waypoint")
    distance_km: float
    estimated_time_minutes: float
    average_slope_deg: float
    max_slope_deg: float
    surface_type: str
    traversability: TraversabilityLevel
    requires_4wd: bool
    hazards: List[int] = Field(description="Indices of hazards on this segment")

class AlternativeRoute(BaseModel):
    """An alternative route option."""
    name: str
    description: str
    pros: List[str]
    cons: List[str]
    distance_km: float
    estimated_time_hours: float
    overall_difficulty: TraversabilityLevel

class RoutingDecision(BaseModel):
    """Complete routing decision from Gemini."""
    route_name: str = Field(description="Descriptive name for this route")
    mission_summary: str = Field(description="Brief description of the routing solution")
    
    # Distance and time
    total_distance_km: float
    estimated_duration_hours: float
    
    # Elevation analysis
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    max_elevation_m: float
    min_elevation_m: float
    max_slope_deg: float
    
    # Route details
    waypoints: List[RouteWaypoint]
    segments: List[RouteSegment]
    hazards: List[TerrainHazard]
    
    # Terrain breakdown
    terrain_distribution: dict = Field(
        description="Percentage of route by terrain type"
    )
    surface_distribution: dict = Field(
        description="Percentage of route by surface type"
    )
    
    # Assessment
    overall_difficulty: TraversabilityLevel
    feasibility_score: float = Field(
        description="0-1 score of route viability",
        ge=0, le=1
    )
    confidence_score: float = Field(
        description="0-1 confidence in this analysis",
        ge=0, le=1
    )
    
    # Reasoning
    reasoning: str = Field(
        description="Detailed explanation of routing decisions"
    )
    key_challenges: List[str]
    recommendations: List[str]
    
    # Alternatives
    alternative_routes: Optional[List[AlternativeRoute]] = None
```

### 5.2 Gemini Route Planner

The core integration with Gemini API.

```python
from google import genai
from google.genai import types
import json
import base64

class GeminiRoutePlanner:
    """
    Gemini-powered route planning with terrain awareness.
    
    FREE TIER: Google AI Studio provides free access.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.client = genai.Client(api_key=self.api_key)
        
        # System instruction for terrain-aware routing
        self.system_instruction = """You are an expert military terrain analyst and route planner.
Your task is to analyze satellite imagery combined with structured geospatial data to plan optimal routes.

CRITICAL RULES:
1. ALWAYS trust the provided elevation/slope data over visual estimates from the image
2. The structured JSON contains ground-truth terrain measurements - use them
3. The satellite image shows current conditions (obstacles, flooding, construction) - use it for verification
4. Never route through slopes exceeding the vehicle's maximum capability
5. Prefer established roads when available, but assess off-road alternatives
6. Consider all hazards: water crossings, cliffs, dense vegetation, urban areas

When analyzing:
- Cross-reference visual features with elevation data
- Identify discrepancies between image and data (recent changes, errors)
- Be conservative - when uncertain, assume worse conditions
- Provide confidence scores reflecting data quality and visibility

Your output must follow the exact JSON schema provided."""
    
    def plan_route(
        self,
        satellite_image: bytes,
        terrain_image: Optional[bytes],
        geospatial_data: Dict,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        vehicle_profile: Dict,
        additional_constraints: Dict = None
    ) -> RoutingDecision:
        """
        Generate optimal route using Gemini multimodal analysis.
        
        Args:
            satellite_image: JPEG bytes of satellite imagery
            terrain_image: Optional terrain map showing contours
            geospatial_data: Structured terrain data (elevation, slopes, roads)
            start_point: (lat, lon) origin
            end_point: (lat, lon) destination
            vehicle_profile: Vehicle capabilities and constraints
            additional_constraints: No-go zones, time limits, etc.
        
        Returns:
            RoutingDecision with complete route plan
        """
        # Build the complete context
        mission_context = {
            "mission": {
                "start": {"lat": start_point[0], "lon": start_point[1]},
                "end": {"lat": end_point[0], "lon": end_point[1]},
                "objective": "Plan optimal route considering terrain constraints"
            },
            "terrain_data": geospatial_data,
            "vehicle": vehicle_profile,
            "constraints": additional_constraints or {}
        }
        
        # Build prompt
        prompt = f"""
<mission_briefing>
Plan a route from ({start_point[0]:.6f}, {start_point[1]:.6f}) to ({end_point[0]:.6f}, {end_point[1]:.6f}).

Vehicle: {vehicle_profile.get('type', 'Military vehicle')}
- Maximum traversable slope: {vehicle_profile.get('max_slope_degrees', 30)}°
- Ground clearance: {vehicle_profile.get('ground_clearance_cm', 30)} cm
- Weight: {vehicle_profile.get('weight_tons', 10)} tons
- Can ford water depth: {vehicle_profile.get('max_ford_depth_cm', 50)} cm
- Preferred surfaces: {', '.join(vehicle_profile.get('preferred_surfaces', ['paved', 'gravel']))}
</mission_briefing>

<geospatial_data>
{json.dumps(mission_context, indent=2)}
</geospatial_data>

<analysis_instructions>
1. Analyze the satellite image for current ground conditions
2. Cross-reference with the structured elevation and slope data
3. Identify the optimal route respecting all constraints
4. Mark waypoints every 1-2 km with terrain assessments
5. Identify all hazards visible in imagery or implied by terrain data
6. Calculate realistic time estimates based on terrain difficulty
7. Suggest alternatives if the primary route has significant risks
</analysis_instructions>

<output_instructions>
Provide a complete routing decision in JSON format.
Be thorough but realistic. Include all waypoints, hazards, and reasoning.
Your confidence score should reflect actual data quality - lower if visibility is poor or data seems incomplete.
</output_instructions>
"""
        
        # Build content parts
        content_parts = []
        
        # Add satellite image
        content_parts.append(
            types.Part.from_bytes(
                data=satellite_image,
                mime_type='image/jpeg'
            )
        )
        
        # Add terrain image if provided
        if terrain_image:
            content_parts.append(
                types.Part.from_bytes(
                    data=terrain_image,
                    mime_type='image/jpeg'
                )
            )
        
        # Add text prompt
        content_parts.append(prompt)
        
        # Generate response
        response = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=content_parts,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                response_mime_type='application/json',
                response_schema=RoutingDecision,
                temperature=0.2,  # Low for consistent, deterministic output
                max_output_tokens=8192
            )
        )
        
        # Parse response
        return RoutingDecision.model_validate_json(response.text)
    
    def analyze_terrain_only(
        self,
        satellite_image: bytes,
        bounds: Tuple[float, float, float, float]
    ) -> Dict:
        """
        Analyze terrain from satellite image only (quick assessment).
        Useful for initial reconnaissance before detailed planning.
        """
        prompt = f"""
Analyze this satellite image covering the area from 
({bounds[0]:.4f}, {bounds[2]:.4f}) to ({bounds[1]:.4f}, {bounds[3]:.4f}).

Identify and describe:
1. Terrain types visible (mountains, valleys, plains, etc.)
2. Apparent elevation variations
3. Road/path networks
4. Water bodies
5. Vegetation density
6. Urban/built areas
7. Potential obstacles for vehicle movement
8. Overall traversability assessment

Provide a structured JSON response.
"""
        
        response = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(data=satellite_image, mime_type='image/jpeg'),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.3
            )
        )
        
        return json.loads(response.text)
```

---

## 6. Route Validation Layer

### 6.1 OSRM Validator

Validate routes against actual road networks.

```python
class OSRMValidator:
    """
    Validate routes using OSRM (Open Source Routing Machine).
    
    FREE: 100% free, no API key required.
    Uses the public demo server.
    """
    
    def __init__(self):
        self.base_url = "https://router.project-osrm.org"
    
    def validate_route(
        self,
        waypoints: List[Tuple[float, float]]
    ) -> Dict:
        """
        Map-match waypoints against road network.
        
        Args:
            waypoints: List of (lon, lat) tuples - NOTE: lon first for OSRM!
        
        Returns:
            Validation results including confidence and snapped coordinates
        """
        # Build coordinate string
        coords_str = ";".join([f"{lon},{lat}" for lon, lat in waypoints])
        
        url = f"{self.base_url}/match/v1/driving/{coords_str}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "annotations": "true",
            "radiuses": ";".join(["50"] * len(waypoints))  # 50m matching radius
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("matchings"):
            matching = data["matchings"][0]
            return {
                "valid": True,
                "confidence": matching.get("confidence", 0),
                "matched_distance_m": matching.get("distance", 0),
                "matched_duration_s": matching.get("duration", 0),
                "snapped_coordinates": matching["geometry"]["coordinates"],
                "tracepoints": [
                    {
                        "original": waypoints[i],
                        "snapped": (
                            t["location"][0], t["location"][1]
                        ) if t else None,
                        "distance_from_original_m": t.get("distance", 0) if t else None,
                        "matched": t is not None
                    }
                    for i, t in enumerate(data.get("tracepoints", []))
                ]
            }
        
        return {
            "valid": False,
            "error": data.get("code", "Unknown error"),
            "message": data.get("message", "")
        }
    
    def get_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        via: List[Tuple[float, float]] = None
    ) -> Dict:
        """
        Get optimal road route between points.
        
        Args:
            start: (lon, lat) origin
            end: (lon, lat) destination
            via: Optional intermediate waypoints
        
        Returns:
            Optimal route with geometry and turn-by-turn
        """
        points = [start]
        if via:
            points.extend(via)
        points.append(end)
        
        coords_str = ";".join([f"{lon},{lat}" for lon, lat in points])
        
        url = f"{self.base_url}/route/v1/driving/{coords_str}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
            "annotations": "true"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "valid": True,
                "distance_m": route.get("distance", 0),
                "duration_s": route.get("duration", 0),
                "geometry": route.get("geometry", {}),
                "legs": [
                    {
                        "distance_m": leg.get("distance", 0),
                        "duration_s": leg.get("duration", 0),
                        "steps": [
                            {
                                "name": step.get("name", ""),
                                "distance_m": step.get("distance", 0),
                                "duration_s": step.get("duration", 0),
                                "maneuver": step.get("maneuver", {})
                            }
                            for step in leg.get("steps", [])
                        ]
                    }
                    for leg in route.get("legs", [])
                ]
            }
        
        return {"valid": False, "error": data.get("code", "Unknown")}
    
    def compare_proposed_vs_optimal(
        self,
        proposed_waypoints: List[Tuple[float, float]],
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> Dict:
        """
        Compare a proposed route against the optimal road route.
        Useful for understanding how much the proposed route deviates.
        """
        # Get optimal route
        optimal = self.get_optimal_route(start, end)
        
        # Validate proposed route
        proposed = self.validate_route(proposed_waypoints)
        
        if optimal.get("valid") and proposed.get("valid"):
            optimal_dist = optimal["distance_m"]
            proposed_dist = proposed["matched_distance_m"]
            
            return {
                "comparison_valid": True,
                "optimal_route": {
                    "distance_m": optimal_dist,
                    "duration_s": optimal["duration_s"]
                },
                "proposed_route": {
                    "distance_m": proposed_dist,
                    "duration_s": proposed["matched_duration_s"],
                    "confidence": proposed["confidence"]
                },
                "analysis": {
                    "distance_ratio": proposed_dist / optimal_dist if optimal_dist > 0 else 0,
                    "detour_percentage": ((proposed_dist - optimal_dist) / optimal_dist * 100) if optimal_dist > 0 else 0,
                    "is_efficient": proposed_dist <= optimal_dist * 1.2  # Within 20% of optimal
                }
            }
        
        return {
            "comparison_valid": False,
            "optimal_error": optimal.get("error"),
            "proposed_error": proposed.get("error")
        }
```

### 6.2 OpenRouteService Validator

Additional validation with elevation and surface data.

```python
import openrouteservice

class OpenRouteServiceValidator:
    """
    Additional route validation with elevation profiles and surface types.
    
    FREE TIER: 2,000 requests/day.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('ORS_API_KEY')
        self.client = openrouteservice.Client(key=self.api_key) if self.api_key else None
    
    def get_route_with_elevation(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None
    ) -> Dict:
        """
        Get route with detailed elevation profile and surface analysis.
        
        Args:
            start: (lon, lat) origin
            end: (lon, lat) destination
            waypoints: Optional intermediate points (lon, lat)
        
        Returns:
            Route with elevation, surface, and steepness data
        """
        if not self.client:
            return {"error": "ORS client not initialized - provide API key"}
        
        coordinates = [list(start)]
        if waypoints:
            coordinates.extend([list(w) for w in waypoints])
        coordinates.append(list(end))
        
        try:
            route = self.client.directions(
                coordinates=coordinates,
                profile='driving-car',
                elevation=True,
                extra_info=['steepness', 'surface', 'waycategory', 'waytype'],
                geometry=True
            )
            
            if route.get('routes'):
                r = route['routes'][0]
                geom = r.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                # Extract elevations if 3D coordinates
                elevations = []
                if coords and len(coords[0]) >= 3:
                    elevations = [c[2] for c in coords]
                
                summary = r.get('summary', {})
                extras = r.get('extras', {})
                
                return {
                    "valid": True,
                    "distance_m": summary.get('distance', 0),
                    "duration_s": summary.get('duration', 0),
                    "ascent_m": summary.get('ascent', 0),
                    "descent_m": summary.get('descent', 0),
                    "elevation_profile": {
                        "elevations": elevations,
                        "min_m": min(elevations) if elevations else None,
                        "max_m": max(elevations) if elevations else None
                    },
                    "surface_analysis": self._parse_extras(extras.get('surface', {})),
                    "steepness_analysis": self._parse_extras(extras.get('steepness', {})),
                    "way_types": self._parse_extras(extras.get('waytype', {})),
                    "geometry": geom
                }
            
            return {"valid": False, "error": "No route found"}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _parse_extras(self, extra_data: Dict) -> Dict:
        """Parse ORS extra_info format into readable dict."""
        if not extra_data:
            return {}
        
        values = extra_data.get('values', [])
        summary = extra_data.get('summary', [])
        
        return {
            "segments": [
                {"start": v[0], "end": v[1], "value": v[2]}
                for v in values
            ],
            "summary": [
                {"value": s.get('value'), "distance_m": s.get('distance'), "percentage": s.get('amount')}
                for s in summary
            ]
        }
    
    def validate_elevation_constraints(
        self,
        waypoints: List[Tuple[float, float]],
        max_slope_degrees: float = 30
    ) -> Dict:
        """
        Check if a route meets elevation/slope constraints.
        """
        if len(waypoints) < 2:
            return {"valid": False, "error": "Need at least 2 waypoints"}
        
        route = self.get_route_with_elevation(
            start=waypoints[0],
            end=waypoints[-1],
            waypoints=waypoints[1:-1] if len(waypoints) > 2 else None
        )
        
        if not route.get("valid"):
            return route
        
        # Analyze steepness
        steepness = route.get("steepness_analysis", {})
        steep_segments = [
            s for s in steepness.get("summary", [])
            if abs(s.get("value", 0)) > max_slope_degrees
        ]
        
        total_distance = route["distance_m"]
        steep_distance = sum(s.get("distance_m", 0) for s in steep_segments)
        
        return {
            "valid": True,
            "meets_constraints": len(steep_segments) == 0,
            "max_slope_constraint": max_slope_degrees,
            "route_summary": {
                "distance_m": total_distance,
                "ascent_m": route.get("ascent_m", 0),
                "descent_m": route.get("descent_m", 0)
            },
            "constraint_violations": {
                "steep_segments_count": len(steep_segments),
                "steep_distance_m": steep_distance,
                "steep_percentage": (steep_distance / total_distance * 100) if total_distance > 0 else 0
            },
            "elevation_profile": route.get("elevation_profile", {}),
            "surface_breakdown": route.get("surface_analysis", {})
        }
```

---

## 7. Complete Pipeline Integration

### 7.1 Main Pipeline Class

Brings everything together.

```python
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import json

@dataclass
class VehicleProfile:
    """Vehicle capabilities and constraints."""
    name: str
    type: str  # e.g., "MRAP", "Light Tactical", "Heavy Truck"
    max_slope_degrees: float
    ground_clearance_cm: float
    weight_tons: float
    max_ford_depth_cm: float
    preferred_surfaces: List[str]
    avoid_surfaces: List[str]
    max_speed_on_road_kmh: float = 100
    max_speed_off_road_kmh: float = 30

# Predefined vehicle profiles
VEHICLE_PROFILES = {
    "mrap": VehicleProfile(
        name="M-ATV MRAP",
        type="Mine-Resistant Ambush Protected",
        max_slope_degrees=35,
        ground_clearance_cm=36,
        weight_tons=14.5,
        max_ford_depth_cm=76,
        preferred_surfaces=["asphalt", "concrete", "gravel", "improved_dirt"],
        avoid_surfaces=["deep_mud", "loose_sand", "swamp"],
        max_speed_on_road_kmh=105,
        max_speed_off_road_kmh=40
    ),
    "humvee": VehicleProfile(
        name="HMMWV",
        type="High Mobility Multipurpose Wheeled Vehicle",
        max_slope_degrees=40,
        ground_clearance_cm=41,
        weight_tons=3.5,
        max_ford_depth_cm=76,
        preferred_surfaces=["asphalt", "gravel", "dirt", "sand"],
        avoid_surfaces=["deep_mud", "swamp", "boulder_field"],
        max_speed_on_road_kmh=113,
        max_speed_off_road_kmh=50
    ),
    "light_truck": VehicleProfile(
        name="Light Tactical Truck",
        type="4x4 Light Truck",
        max_slope_degrees=30,
        ground_clearance_cm=25,
        weight_tons=5,
        max_ford_depth_cm=50,
        preferred_surfaces=["asphalt", "concrete", "gravel"],
        avoid_surfaces=["mud", "sand", "rock", "unimproved"],
        max_speed_on_road_kmh=110,
        max_speed_off_road_kmh=25
    ),
    "heavy_truck": VehicleProfile(
        name="Heavy Equipment Transporter",
        type="Heavy Logistics Vehicle",
        max_slope_degrees=20,
        ground_clearance_cm=30,
        weight_tons=35,
        max_ford_depth_cm=100,
        preferred_surfaces=["asphalt", "concrete"],
        avoid_surfaces=["dirt", "sand", "mud", "gravel_loose"],
        max_speed_on_road_kmh=80,
        max_speed_off_road_kmh=15
    )
}


class MilitaryRoutePipeline:
    """
    Complete terrain-aware military route optimization pipeline.
    
    Integrates:
    - Google Maps (elevation, satellite, roads)
    - Google Earth Engine (terrain analysis, land cover)
    - Gemini API (intelligent route planning)
    - OSRM (route validation)
    - OpenRouteService (elevation profiles)
    """
    
    def __init__(
        self,
        google_maps_key: str = None,
        gemini_key: str = None,
        ors_key: str = None,
        gee_project: str = None
    ):
        # Initialize clients
        self.maps = GoogleMapsClient(google_maps_key)
        self.gemini = GeminiRoutePlanner(gemini_key)
        self.osrm = OSRMValidator()
        
        # Optional clients
        self.ors = OpenRouteServiceValidator(ors_key) if ors_key else None
        
        try:
            self.gee = EarthEngineClient(gee_project) if gee_project else None
        except Exception as e:
            print(f"Earth Engine not available: {e}")
            self.gee = None
    
    def collect_geospatial_data(
        self,
        center: Tuple[float, float],
        radius_km: float = 15
    ) -> Dict:
        """
        Collect all geospatial data for a region.
        
        Args:
            center: (lat, lon) center point
            radius_km: Radius of analysis area
        
        Returns:
            Comprehensive geospatial dataset
        """
        # Calculate bounds
        lat_offset = radius_km / 111.0
        lon_offset = radius_km / (111.0 * math.cos(math.radians(center[0])))
        
        bounds = (
            center[0] - lat_offset,  # south
            center[0] + lat_offset,  # north
            center[1] - lon_offset,  # west
            center[1] + lon_offset   # east
        )
        
        gee_bounds = [bounds[2], bounds[0], bounds[3], bounds[1]]  # [w, s, e, n]
        
        result = {
            "center": center,
            "radius_km": radius_km,
            "bounds": {
                "south": bounds[0],
                "north": bounds[1],
                "west": bounds[2],
                "east": bounds[3]
            }
        }
        
        # Get satellite imagery
        print("Fetching satellite imagery...")
        result["satellite_image"] = self.maps.get_satellite_image(
            center, zoom=13, size="640x640", scale=2
        )
        
        # Get terrain imagery
        print("Fetching terrain map...")
        result["terrain_image"] = self.maps.get_terrain_image(center, zoom=12)
        
        # Get elevation grid
        print("Fetching elevation data...")
        elevation_grid = self.maps.get_elevation_grid(bounds, grid_size=15)
        result["elevation"] = {
            "source": "Google Elevation API",
            "resolution_m": 30,
            "statistics": elevation_grid.get("statistics", {})
        }
        
        # Get Earth Engine data if available
        if self.gee:
            print("Fetching terrain analysis from Earth Engine...")
            try:
                terrain = self.gee.get_terrain_analysis(gee_bounds)
                slope_dist = self.gee.get_slope_distribution(gee_bounds)
                land_cover = self.gee.get_land_cover(gee_bounds)
                
                result["terrain_analysis"] = terrain
                result["slope_distribution"] = slope_dist
                result["land_cover"] = land_cover
            except Exception as e:
                print(f"Earth Engine error: {e}")
        
        return result
    
    def plan_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        vehicle: VehicleProfile,
        waypoints: List[Tuple[float, float]] = None,
        no_go_zones: List[List[Tuple[float, float]]] = None,
        collect_new_data: bool = True,
        existing_data: Dict = None
    ) -> Dict:
        """
        Plan an optimal route with full terrain analysis.
        
        Args:
            start: (lat, lon) origin
            end: (lat, lon) destination
            vehicle: Vehicle profile with capabilities
            waypoints: Optional intermediate waypoints
            no_go_zones: List of polygon coordinates to avoid
            collect_new_data: Whether to fetch fresh geospatial data
            existing_data: Pre-collected geospatial data to use
        
        Returns:
            Complete route plan with validation
        """
        print(f"\n{'='*60}")
        print(f"ROUTE PLANNING: {vehicle.name}")
        print(f"From: {start}")
        print(f"To: {end}")
        print(f"{'='*60}\n")
        
        # Step 1: Collect geospatial data
        if collect_new_data or existing_data is None:
            center = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            
            # Calculate radius to cover the route
            route_distance_km = self._haversine_km(start[0], start[1], end[0], end[1])
            radius_km = max(route_distance_km * 0.75, 10)  # At least 10km
            
            print(f"Collecting geospatial data (radius: {radius_km:.1f} km)...")
            geo_data = self.collect_geospatial_data(center, radius_km)
        else:
            geo_data = existing_data
        
        # Step 2: Get baseline road route
        print("Getting baseline road route...")
        road_route = self.maps.get_road_route(start, end, waypoints)
        
        # Step 3: Build structured context for Gemini
        print("Building terrain context...")
        
        vehicle_dict = {
            "name": vehicle.name,
            "type": vehicle.type,
            "max_slope_degrees": vehicle.max_slope_degrees,
            "ground_clearance_cm": vehicle.ground_clearance_cm,
            "weight_tons": vehicle.weight_tons,
            "max_ford_depth_cm": vehicle.max_ford_depth_cm,
            "preferred_surfaces": vehicle.preferred_surfaces,
            "avoid_surfaces": vehicle.avoid_surfaces,
            "max_speed_on_road_kmh": vehicle.max_speed_on_road_kmh,
            "max_speed_off_road_kmh": vehicle.max_speed_off_road_kmh
        }
        
        geospatial_context = {
            "region": geo_data.get("bounds", {}),
            "elevation": geo_data.get("elevation", {}),
            "terrain_analysis": geo_data.get("terrain_analysis", {}),
            "slope_distribution": geo_data.get("slope_distribution", {}),
            "land_cover": geo_data.get("land_cover", {}),
            "road_network": {
                "baseline_route": {
                    "distance_m": road_route.get("distance_m", 0) if road_route.get("success") else None,
                    "duration_s": road_route.get("duration_s", 0) if road_route.get("success") else None,
                    "available": road_route.get("success", False)
                }
            }
        }
        
        if no_go_zones:
            geospatial_context["no_go_zones"] = no_go_zones
        
        # Step 4: Generate route with Gemini
        print("Generating route with Gemini...")
        
        routing_decision = self.gemini.plan_route(
            satellite_image=geo_data["satellite_image"],
            terrain_image=geo_data.get("terrain_image"),
            geospatial_data=geospatial_context,
            start_point=start,
            end_point=end,
            vehicle_profile=vehicle_dict,
            additional_constraints={"no_go_zones": no_go_zones} if no_go_zones else None
        )
        
        # Step 5: Validate route
        print("Validating route...")
        
        # Extract waypoint coordinates for validation
        route_coords = [
            (wp.lon, wp.lat)  # OSRM uses lon, lat
            for wp in routing_decision.waypoints
        ]
        
        # OSRM validation
        osrm_validation = self.osrm.validate_route(route_coords)
        
        # ORS validation if available
        ors_validation = None
        if self.ors and len(route_coords) >= 2:
            ors_validation = self.ors.validate_elevation_constraints(
                route_coords,
                max_slope_degrees=vehicle.max_slope_degrees
            )
        
        # Step 6: Compile results
        result = {
            "status": "success",
            "route_plan": routing_decision.model_dump(),
            "validation": {
                "osrm": osrm_validation,
                "openrouteservice": ors_validation
            },
            "geospatial_summary": {
                "bounds": geo_data.get("bounds"),
                "elevation_stats": geo_data.get("elevation", {}).get("statistics"),
                "terrain_analysis": geo_data.get("terrain_analysis"),
                "land_cover": geo_data.get("land_cover")
            },
            "vehicle_used": vehicle_dict
        }
        
        print("\n" + "="*60)
        print("ROUTE PLANNING COMPLETE")
        print(f"Distance: {routing_decision.total_distance_km:.2f} km")
        print(f"Duration: {routing_decision.estimated_duration_hours:.2f} hours")
        print(f"Difficulty: {routing_decision.overall_difficulty}")
        print(f"Feasibility: {routing_decision.feasibility_score:.0%}")
        print(f"Confidence: {routing_decision.confidence_score:.0%}")
        print("="*60 + "\n")
        
        return result
    
    def _haversine_km(self, lat1, lon1, lat2, lon2) -> float:
        """Calculate distance in kilometers."""
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.asin(math.sqrt(a))
    
    def quick_assessment(
        self,
        center: Tuple[float, float],
        radius_km: float = 10
    ) -> Dict:
        """
        Quick terrain assessment without full route planning.
        Useful for initial reconnaissance.
        """
        # Get satellite image
        sat_image = self.maps.get_satellite_image(center, zoom=13)
        
        # Get basic elevation data
        lat_off = radius_km / 111
        lon_off = radius_km / (111 * math.cos(math.radians(center[0])))
        bounds = (
            center[0] - lat_off, center[0] + lat_off,
            center[1] - lon_off, center[1] + lon_off
        )
        
        elevation = self.maps.get_elevation_grid(bounds, grid_size=10)
        
        # Quick Gemini analysis
        assessment = self.gemini.analyze_terrain_only(sat_image, bounds)
        
        return {
            "center": center,
            "radius_km": radius_km,
            "elevation_summary": elevation.get("statistics", {}),
            "terrain_assessment": assessment
        }
```

---

## 8. Working Example with Dummy Data

### 8.1 Complete Example Script

```python
"""
Complete working example of the Military Route Optimization Pipeline.
Uses dummy data that mirrors production structure exactly.

Run this to understand the data flow before connecting real APIs.
"""

import json
from datetime import datetime

# ============================================================
# DUMMY DATA - Mirrors exact production API response structure
# Location: Colorado Rockies (mountainous terrain for testing)
# ============================================================

# Coordinates
START_POINT = (40.0150, -105.2705)  # Boulder, CO
END_POINT = (39.5501, -105.7821)    # Leadville, CO
CENTER_POINT = (39.7826, -105.5263)  # Midpoint

# Simulated elevation data (what Google Elevation API returns)
DUMMY_ELEVATION_DATA = {
    "source": "Google Elevation API",
    "resolution_m": 30,
    "statistics": {
        "min_elevation_m": 1655,
        "max_elevation_m": 4267,
        "mean_elevation_m": 2950,
        "elevation_range_m": 2612
    },
    "profile_along_direct_path": [
        {"distance_km": 0, "lat": 40.0150, "lon": -105.2705, "elevation_m": 1655},
        {"distance_km": 8, "lat": 39.9500, "lon": -105.3500, "elevation_m": 2134},
        {"distance_km": 16, "lat": 39.8850, "lon": -105.4300, "elevation_m": 2743},
        {"distance_km": 24, "lat": 39.8200, "lon": -105.5100, "elevation_m": 3200},
        {"distance_km": 32, "lat": 39.7550, "lon": -105.5900, "elevation_m": 3658},
        {"distance_km": 40, "lat": 39.6900, "lon": -105.6700, "elevation_m": 3900},
        {"distance_km": 48, "lat": 39.6250, "lon": -105.7300, "elevation_m": 3505},
        {"distance_km": 56, "lat": 39.5501, "lon": -105.7821, "elevation_m": 3094}
    ]
}

# Simulated terrain analysis (what Earth Engine returns)
DUMMY_TERRAIN_ANALYSIS = {
    "source": "USGS SRTM via Earth Engine",
    "elevation": {
        "min_m": 1655,
        "max_m": 4267,
        "mean_m": 2950,
        "std_dev_m": 580
    },
    "slope": {
        "min_deg": 0,
        "max_deg": 52,
        "mean_deg": 18.5
    }
}

# Slope distribution (percentage of terrain in each category)
DUMMY_SLOPE_DISTRIBUTION = {
    "flat_0_5_deg_pct": 0.08,
    "gentle_5_15_deg_pct": 0.32,
    "moderate_15_30_deg_pct": 0.38,
    "steep_30_45_deg_pct": 0.17,
    "very_steep_45_plus_deg_pct": 0.05
}

# Land cover distribution
DUMMY_LAND_COVER = {
    "source": "ESA WorldCover 2021",
    "distribution": {
        "tree_cover": 0.42,
        "shrubland": 0.15,
        "grassland": 0.13,
        "bare_rock": 0.20,
        "snow_ice": 0.05,
        "water": 0.02,
        "built_up": 0.03
    }
}

# Road network data
DUMMY_ROAD_NETWORK = {
    "roads": [
        {
            "id": "US-36",
            "name": "US Highway 36",
            "type": "highway",
            "surface": "asphalt",
            "condition": "excellent",
            "max_weight_tons": 40
        },
        {
            "id": "CO-72",
            "name": "Peak to Peak Highway",
            "type": "state_highway",
            "surface": "asphalt",
            "condition": "good",
            "max_weight_tons": 25,
            "notes": "Winter chains may be required"
        },
        {
            "id": "CO-91",
            "name": "Tennessee Pass Road",
            "type": "state_highway",
            "surface": "asphalt",
            "condition": "good",
            "max_weight_tons": 25
        },
        {
            "id": "FR-102",
            "name": "Forest Road 102",
            "type": "forest_road",
            "surface": "gravel",
            "condition": "fair",
            "max_weight_tons": 10,
            "notes": "Seasonal closure spring"
        }
    ],
    "baseline_road_route": {
        "distance_km": 95.5,
        "duration_hours": 2.1,
        "via": ["US-36", "CO-72", "CO-91"]
    }
}

# Vehicle constraints
DUMMY_VEHICLE = {
    "name": "M-ATV MRAP",
    "type": "Mine-Resistant Ambush Protected",
    "max_slope_degrees": 35,
    "ground_clearance_cm": 36,
    "weight_tons": 14.5,
    "max_ford_depth_cm": 76,
    "preferred_surfaces": ["asphalt", "concrete", "gravel", "improved_dirt"],
    "avoid_surfaces": ["deep_mud", "loose_sand", "swamp"],
    "max_speed_on_road_kmh": 105,
    "max_speed_off_road_kmh": 40
}

# No-go zones (areas to avoid)
DUMMY_NO_GO_ZONES = [
    # Civilian area near Boulder
    [
        (40.02, -105.28), (40.02, -105.26),
        (40.00, -105.26), (40.00, -105.28)
    ],
    # Protected wilderness area
    [
        (39.85, -105.55), (39.85, -105.50),
        (39.80, -105.50), (39.80, -105.55)
    ]
]

# ============================================================
# COMPLETE STRUCTURED CONTEXT FOR GEMINI
# This is exactly what gets sent to Gemini API
# ============================================================

def build_gemini_context():
    """Build the complete context object that Gemini receives."""
    
    return {
        "mission": {
            "id": f"ROUTE-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "start": {
                "lat": START_POINT[0],
                "lon": START_POINT[1],
                "name": "Boulder, CO"
            },
            "end": {
                "lat": END_POINT[0],
                "lon": END_POINT[1],
                "name": "Leadville, CO"
            },
            "objective": "Tactical transit with minimal detection risk",
            "priority": "speed_with_safety"
        },
        
        "region": {
            "center": {"lat": CENTER_POINT[0], "lon": CENTER_POINT[1]},
            "bounds": {
                "north": 40.1,
                "south": 39.5,
                "west": -105.85,
                "east": -105.2
            },
            "area_km2": 2800
        },
        
        "elevation": DUMMY_ELEVATION_DATA,
        
        "terrain_analysis": DUMMY_TERRAIN_ANALYSIS,
        
        "slope_distribution": DUMMY_SLOPE_DISTRIBUTION,
        
        "land_cover": DUMMY_LAND_COVER,
        
        "road_network": DUMMY_ROAD_NETWORK,
        
        "vehicle": DUMMY_VEHICLE,
        
        "constraints": {
            "no_go_zones": DUMMY_NO_GO_ZONES,
            "time_window": None,
            "stealth_required": False
        },
        
        "weather": {
            "current_temp_c": 12,
            "precipitation": "none",
            "visibility_km": 15,
            "snow_line_m": 3800,
            "wind_speed_kmh": 15
        }
    }


def simulate_gemini_response():
    """
    Simulated Gemini response showing expected output structure.
    In production, Gemini generates this based on image + context.
    """
    
    return {
        "route_name": "Boulder-Leadville Mountain Transit",
        "mission_summary": "Primary route follows established highways with one mountain pass crossing. Route avoids designated no-go zones and stays within vehicle slope capabilities except for one challenging segment near Tennessee Pass.",
        
        "total_distance_km": 95.5,
        "estimated_duration_hours": 2.8,
        
        "total_elevation_gain_m": 2450,
        "total_elevation_loss_m": 1005,
        "max_elevation_m": 3900,
        "min_elevation_m": 1655,
        "max_slope_deg": 28,
        
        "waypoints": [
            {
                "lat": 40.0150,
                "lon": -105.2705,
                "elevation_m": 1655,
                "distance_from_start_km": 0,
                "terrain_type": "urban_exit",
                "surface_type": "asphalt",
                "traversability": "easy",
                "slope_deg": 2,
                "notes": "Start point - Boulder city limits"
            },
            {
                "lat": 39.9500,
                "lon": -105.3500,
                "elevation_m": 2134,
                "distance_from_start_km": 12,
                "terrain_type": "mountain_road",
                "surface_type": "asphalt",
                "traversability": "easy",
                "slope_deg": 8,
                "notes": "Begin mountain ascent on CO-72"
            },
            {
                "lat": 39.8600,
                "lon": -105.4800,
                "elevation_m": 2896,
                "distance_from_start_km": 28,
                "terrain_type": "mountain_pass_approach",
                "surface_type": "asphalt",
                "traversability": "moderate",
                "slope_deg": 15,
                "notes": "Switchbacks begin - reduced speed advised"
            },
            {
                "lat": 39.7800,
                "lon": -105.5500,
                "elevation_m": 3505,
                "distance_from_start_km": 42,
                "terrain_type": "mountain_pass",
                "surface_type": "asphalt",
                "traversability": "moderate",
                "slope_deg": 12,
                "notes": "Rollins Pass vicinity - exposed terrain"
            },
            {
                "lat": 39.7000,
                "lon": -105.6400,
                "elevation_m": 3810,
                "distance_from_start_km": 58,
                "terrain_type": "high_altitude_road",
                "surface_type": "asphalt",
                "traversability": "difficult",
                "slope_deg": 22,
                "notes": "Tennessee Pass - most challenging segment"
            },
            {
                "lat": 39.6200,
                "lon": -105.7200,
                "elevation_m": 3350,
                "distance_from_start_km": 75,
                "terrain_type": "mountain_descent",
                "surface_type": "asphalt",
                "traversability": "moderate",
                "slope_deg": 18,
                "notes": "Descending into Eagle River valley"
            },
            {
                "lat": 39.5501,
                "lon": -105.7821,
                "elevation_m": 3094,
                "distance_from_start_km": 95.5,
                "terrain_type": "town_approach",
                "surface_type": "asphalt",
                "traversability": "easy",
                "slope_deg": 5,
                "notes": "End point - Leadville outskirts"
            }
        ],
        
        "segments": [
            {
                "segment_id": 1,
                "start_waypoint": 0,
                "end_waypoint": 1,
                "distance_km": 12,
                "estimated_time_minutes": 15,
                "average_slope_deg": 5,
                "max_slope_deg": 8,
                "surface_type": "asphalt",
                "traversability": "easy",
                "requires_4wd": False,
                "hazards": []
            },
            {
                "segment_id": 2,
                "start_waypoint": 1,
                "end_waypoint": 2,
                "distance_km": 16,
                "estimated_time_minutes": 22,
                "average_slope_deg": 12,
                "max_slope_deg": 18,
                "surface_type": "asphalt",
                "traversability": "moderate",
                "requires_4wd": False,
                "hazards": [0]
            },
            {
                "segment_id": 3,
                "start_waypoint": 2,
                "end_waypoint": 3,
                "distance_km": 14,
                "estimated_time_minutes": 20,
                "average_slope_deg": 10,
                "max_slope_deg": 15,
                "surface_type": "asphalt",
                "traversability": "moderate",
                "requires_4wd": False,
                "hazards": [1]
            },
            {
                "segment_id": 4,
                "start_waypoint": 3,
                "end_waypoint": 4,
                "distance_km": 16,
                "estimated_time_minutes": 28,
                "average_slope_deg": 18,
                "max_slope_deg": 28,
                "surface_type": "asphalt",
                "traversability": "difficult",
                "requires_4wd": True,
                "hazards": [2, 3]
            },
            {
                "segment_id": 5,
                "start_waypoint": 4,
                "end_waypoint": 5,
                "distance_km": 17,
                "estimated_time_minutes": 25,
                "average_slope_deg": 15,
                "max_slope_deg": 22,
                "surface_type": "asphalt",
                "traversability": "moderate",
                "requires_4wd": False,
                "hazards": []
            },
            {
                "segment_id": 6,
                "start_waypoint": 5,
                "end_waypoint": 6,
                "distance_km": 20.5,
                "estimated_time_minutes": 22,
                "average_slope_deg": 8,
                "max_slope_deg": 12,
                "surface_type": "asphalt",
                "traversability": "easy",
                "requires_4wd": False,
                "hazards": []
            }
        ],
        
        "hazards": [
            {
                "hazard_type": "steep_grade",
                "severity": "medium",
                "lat": 39.88,
                "lon": -105.45,
                "description": "15% grade for 2km - maintain speed for momentum",
                "mitigation": "Use low gear on descent, maintain 40 kmh uphill"
            },
            {
                "hazard_type": "exposure",
                "severity": "low",
                "lat": 39.80,
                "lon": -105.54,
                "description": "Open terrain with minimal cover for 5km",
                "mitigation": "Move during low visibility conditions if stealth required"
            },
            {
                "hazard_type": "altitude",
                "severity": "medium",
                "lat": 39.70,
                "lon": -105.64,
                "description": "Above 3800m - potential for snow even in summer",
                "mitigation": "Check weather forecast, carry chains"
            },
            {
                "hazard_type": "steep_switchbacks",
                "severity": "high",
                "lat": 39.72,
                "lon": -105.62,
                "description": "Series of tight switchbacks with 28° max slope",
                "mitigation": "Reduce speed to 20 kmh, use low range if available"
            }
        ],
        
        "terrain_distribution": {
            "mountain_road": 0.45,
            "mountain_pass": 0.25,
            "high_altitude": 0.15,
            "urban_suburban": 0.10,
            "valley_floor": 0.05
        },
        
        "surface_distribution": {
            "asphalt": 0.95,
            "concrete": 0.03,
            "gravel": 0.02
        },
        
        "overall_difficulty": "moderate",
        "feasibility_score": 0.85,
        "confidence_score": 0.90,
        
        "reasoning": """Route analysis based on satellite imagery cross-referenced with SRTM elevation data shows a viable path following established highways. 

The primary challenge is the Tennessee Pass crossing at 3810m elevation, where slopes reach 28° in the switchback sections. While this exceeds comfortable driving conditions, it remains within the M-ATV's 35° capability with adequate margin.

The designated no-go zones near Boulder and the wilderness area are successfully avoided by the selected route. Land cover analysis shows 42% tree cover providing concealment for much of the route.

Weather conditions are currently favorable, but the segment above 3800m is susceptible to rapid weather changes. Recommend monitoring forecasts and having contingency for shelter if conditions deteriorate.

The route's 95.5km distance takes approximately 2.8 hours accounting for reduced speeds in mountain sections. This is 40 minutes longer than the baseline estimate due to terrain-adjusted speed calculations.""",
        
        "key_challenges": [
            "Tennessee Pass elevation and switchbacks",
            "Extended exposure above treeline (8km)",
            "Potential for weather changes at altitude",
            "Limited alternate routes if primary blocked"
        ],
        
        "recommendations": [
            "Depart early morning for best weather window",
            "Carry tire chains regardless of season",
            "Maintain radio contact at waypoints 3, 4, 5",
            "Identify shelter points along route for weather contingency",
            "Consider convoy spacing of 500m in switchback sections"
        ],
        
        "alternative_routes": [
            {
                "name": "I-70 Southern Route",
                "description": "Longer route via Interstate 70 through Eisenhower Tunnel",
                "pros": [
                    "Lower maximum elevation (3400m vs 3810m)",
                    "Better road conditions year-round",
                    "More services available"
                ],
                "cons": [
                    "40km longer distance",
                    "Higher traffic exposure",
                    "Toll road sections"
                ],
                "distance_km": 135,
                "estimated_time_hours": 2.5,
                "overall_difficulty": "easy"
            }
        ]
    }


def print_example():
    """Print the complete example for reference."""
    
    print("\n" + "="*70)
    print("MILITARY ROUTE OPTIMIZATION PIPELINE - EXAMPLE DATA")
    print("="*70)
    
    print("\n[1] MISSION PARAMETERS")
    print("-"*40)
    print(f"Start: Boulder, CO {START_POINT}")
    print(f"End: Leadville, CO {END_POINT}")
    print(f"Vehicle: {DUMMY_VEHICLE['name']}")
    print(f"Max Slope: {DUMMY_VEHICLE['max_slope_degrees']}°")
    
    print("\n[2] COMPLETE GEMINI CONTEXT (sent to API)")
    print("-"*40)
    context = build_gemini_context()
    print(json.dumps(context, indent=2))
    
    print("\n[3] SIMULATED GEMINI RESPONSE")
    print("-"*40)
    response = simulate_gemini_response()
    print(json.dumps(response, indent=2))
    
    print("\n[4] QUICK REFERENCE - API ENDPOINTS")
    print("-"*40)
    print("""
Google Elevation API:
  URL: https://maps.googleapis.com/maps/api/elevation/json
  Params: locations=LAT,LON|LAT,LON&key=API_KEY
  
Google Static Maps API:
  URL: https://maps.googleapis.com/maps/api/staticmap
  Params: center=LAT,LON&zoom=14&size=640x640&maptype=satellite&key=API_KEY

Google Directions API:
  URL: https://maps.googleapis.com/maps/api/directions/json
  Params: origin=LAT,LON&destination=LAT,LON&key=API_KEY

OSRM (free, no key):
  Route: https://router.project-osrm.org/route/v1/driving/LON,LAT;LON,LAT
  Match: https://router.project-osrm.org/match/v1/driving/LON,LAT;LON,LAT

Gemini API:
  Model: gemini-2.0-flash
  Input: Image bytes + JSON context
  Output: Structured JSON (RoutingDecision schema)
""")


if __name__ == "__main__":
    print_example()
```

---

## 9. Touchscreen Interface Integration

### 9.1 Backend API Structure

For your touchscreen interface, expose these REST endpoints:

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional

app = FastAPI(title="Military Route Planner API")

# Initialize pipeline
pipeline = MilitaryRoutePipeline()

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    vehicle_type: str = "mrap"
    waypoints: Optional[List[Tuple[float, float]]] = None
    no_go_zones: Optional[List[List[Tuple[float, float]]]] = None

class PointRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 10

@app.post("/api/plan-route")
async def plan_route(request: RouteRequest):
    """Main route planning endpoint."""
    
    vehicle = VEHICLE_PROFILES.get(request.vehicle_type)
    if not vehicle:
        raise HTTPException(400, f"Unknown vehicle: {request.vehicle_type}")
    
    result = pipeline.plan_route(
        start=(request.start_lat, request.start_lon),
        end=(request.end_lat, request.end_lon),
        vehicle=vehicle,
        waypoints=request.waypoints,
        no_go_zones=request.no_go_zones
    )
    
    return result

@app.post("/api/quick-assess")
async def quick_assessment(request: PointRequest):
    """Quick terrain assessment for a point."""
    
    result = pipeline.quick_assessment(
        center=(request.lat, request.lon),
        radius_km=request.radius_km
    )
    
    return result

@app.get("/api/elevation")
async def get_elevation(lat: float, lon: float):
    """Get elevation at a single point."""
    
    result = pipeline.maps.get_elevation_at_points([(lat, lon)])
    return result

@app.get("/api/satellite-image")
async def get_satellite(lat: float, lon: float, zoom: int = 14):
    """Get satellite image for a location."""
    
    image_bytes = pipeline.maps.get_satellite_image(
        center=(lat, lon),
        zoom=zoom
    )
    
    if image_bytes:
        import base64
        return {"image": base64.b64encode(image_bytes).decode()}
    
    raise HTTPException(500, "Failed to fetch image")

@app.get("/api/vehicles")
async def list_vehicles():
    """List available vehicle profiles."""
    
    return {
        name: {
            "name": v.name,
            "type": v.type,
            "max_slope": v.max_slope_degrees,
            "weight_tons": v.weight_tons
        }
        for name, v in VEHICLE_PROFILES.items()
    }
```

### 9.2 Frontend Integration Notes

For your touchscreen UI:

1. **Map Display**: Use Leaflet.js or MapLibre with satellite tile layer
2. **Point Selection**: Touch to add waypoints, long-press for start/end
3. **Route Visualization**: Draw polyline from waypoint coordinates
4. **Hazard Markers**: Show hazards with severity-colored icons
5. **Elevation Profile**: Chart.js line graph below map

---

## 10. Appendix: API Reference

### Quick Reference Card

| API | Endpoint | Free Limit | Key Required |
|-----|----------|------------|--------------|
| Google Elevation | maps.googleapis.com/maps/api/elevation | $200/mo credit | Yes |
| Google Static Maps | maps.googleapis.com/maps/api/staticmap | $200/mo credit | Yes |
| Google Directions | maps.googleapis.com/maps/api/directions | $200/mo credit | Yes |
| Gemini | generativelanguage.googleapis.com | Free tier | Yes |
| OSRM | router.project-osrm.org | Unlimited | No |
| OpenRouteService | api.openrouteservice.org | 2000/day | Yes |
| Earth Engine | earthengine.googleapis.com | Unlimited (non-commercial) | Project ID |
| OpenTopography | portal.opentopography.org/API | 300/day | Yes |

### Environment Setup Checklist

```bash
# 1. Create .env file
cat > .env << 'EOF'
GOOGLE_MAPS_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
ORS_API_KEY=your-key-here
OPENTOPOGRAPHY_API_KEY=your-key-here
GOOGLE_CLOUD_PROJECT=your-project-id
EOF

# 2. Install dependencies
pip install \
    requests \
    numpy \
    rasterio \
    richdem \
    google-genai \
    openrouteservice \
    earthengine-api \
    pydantic \
    python-dotenv \
    fastapi \
    uvicorn

# 3. Authenticate Earth Engine (first time only)
python -c "import ee; ee.Authenticate()"

# 4. Test installation
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Google Maps:', 'OK' if os.getenv('GOOGLE_MAPS_API_KEY') else 'MISSING')
print('Gemini:', 'OK' if os.getenv('GEMINI_API_KEY') else 'MISSING')
"
```

---

## Summary

This pipeline enables Gemini to make intelligent routing decisions by providing:

1. **Satellite imagery** → Visual context for current conditions
2. **Elevation data** → Quantitative height measurements
3. **Slope analysis** → Traversability constraints
4. **Road network** → Established route options
5. **Land cover** → Terrain type distribution
6. **Vehicle profile** → Capability constraints

The key insight: **Gemini excels at reasoning when given structured data alongside images**. By extracting terrain constraints into JSON before calling Gemini, you transform a vision problem into a reasoning problem that Gemini can solve effectively.

All services are free for development and moderate production use. Scale considerations only apply at high volume (>40,000 route calculations/month).
