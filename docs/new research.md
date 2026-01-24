# Free High-Accuracy Tactical Pathfinding on Satellite Imagery

The most effective free approach combines **Segment Anything Model (SAM)** or **U-Net** for building detection with **free building footprint datasets** (Microsoft/OSM/Overture), fused into a cost grid for **A* pathfinding via pyastar2d**, producing smooth GPS waypoints through Douglas-Peucker simplification and cubic spline interpolation. This pipeline achieves **85-94% building detection accuracy** and generates meter-level waypoints suitable for tactical movement planning—entirely with free, open-source tools.

Your current Copernicus DEM + ESA WorldCover approach fails because WorldCover's **10m resolution** cannot detect individual buildings—it classifies broad land cover types. Pixel-level building detection requires either ML segmentation on the satellite imagery itself or high-resolution building footprint datasets, both of which are available for free.

---

## The optimal free pipeline architecture

The recommended architecture processes satellite imagery through four stages: obstacle detection, cost grid generation, pathfinding, and waypoint export. Each stage has multiple free options with different accuracy/speed tradeoffs.

**Stage 1: Building/Obstacle Detection** uses one of three approaches. The **segment-geospatial** library wrapping SAM provides zero-shot building segmentation without training, achieving 75-85% IoU. **U-Net with pretrained encoders** (via segmentation-models-pytorch) achieves higher accuracy at 85-94% IoU but requires fine-tuning. Free **building footprint datasets** from Microsoft, OSM, or Overture Maps provide pre-extracted polygons covering most of the globe.

**Stage 2: Cost Grid Generation** converts detected obstacles into a traversability matrix where each cell has a movement cost. Buildings get infinite cost, buffer zones around buildings get graduated costs (higher near obstacles), roads get low costs, and open ground gets medium costs. The scipy `distance_transform_edt` function efficiently computes buffer zones.

**Stage 3: Pathfinding** uses **pyastar2d** for grids up to 10,000×10,000 cells, solving a 4000×4000 maze in under 1 second. For larger areas, hierarchical pathfinding (HPA*) reduces computation by 96%+ through cluster-based preprocessing.

**Stage 4: Waypoint Export** simplifies the pixel path via Douglas-Peucker, smooths it with cubic splines, resamples at fixed intervals (e.g., every 2-5 meters), converts to GPS coordinates using rasterio transforms, and exports as GeoJSON for your React frontend.

---

## Image-based obstacle detection with SAM

The **Segment Anything Model** by Meta, accessible through the **segment-geospatial (SamGeo)** Python package, provides the fastest path to building detection without training custom models.

```python
# Installation
pip install segment-geospatial[samgeo2]  # For SAM 2 (faster, more accurate)

# Basic building segmentation
from samgeo import SamGeo
from samgeo.common import tms_to_geotiff

# Download satellite imagery for your area
bbox = [-122.42, 37.77, -122.40, 37.79]  # San Francisco example
tms_to_geotiff(output="satellite.tif", bbox=bbox, zoom=19, source="Satellite")

# Initialize SAM (vit_h = highest quality, vit_b = fastest)
sam = SamGeo(model_type="vit_h", checkpoint="sam_vit_h_4b8939.pth")

# Automatic mask generation
sam.generate("satellite.tif", "building_mask.tif", 
             batch=True, foreground=True, erosion_kernel=(3,3))

# Convert to vector polygons
sam.tiff_to_gpkg("building_mask.tif", "buildings.gpkg")
```

**Text-prompted segmentation** using GroundingDINO integration allows natural language queries:

```python
pip install segment-geospatial[text]

sam = SamGeo(model_type="vit_h", automatic=False)
sam.set_image("satellite.tif")
sam.predict(text_prompt="building", output="buildings.tif")
```

SAM 2 provides **5× faster inference** and better accuracy on smaller objects. Memory requirements are **8GB+ VRAM** for vit_h (best quality), **4GB** for vit_b (fastest). Google Colab's free GPU tier works with vit_b.

For **highest accuracy** (89-94% IoU), use **U-Net or DeepLabV3+** with pretrained encoders via segmentation-models-pytorch:

```python
import segmentation_models_pytorch as smp
import torch

# Create model with pretrained ImageNet encoder
model = smp.Unet(
    encoder_name="se_resnext50_32x4d",  # Best accuracy
    encoder_weights="imagenet",
    in_channels=3,
    classes=1,
    activation='sigmoid'
)

# For production: fine-tune on SpaceNet building dataset (free on AWS S3)
# aws s3 cp s3://spacenet-dataset/ ./data/ --recursive --request-payer requester
```

---

## Gemini Vision is not viable for pixel-accurate detection

Research reveals significant limitations making Gemini unsuitable as the primary obstacle detection system. Gemini's coordinate system normalizes positions to a **1000×1000 grid**, limiting precision to 0.1% of image dimensions. On a 1km satellite image, this means **~1 meter precision at best**—inadequate for tactical pathfinding requiring sub-meter accuracy.

More critically, academic studies show Gemini achieves only **68.5% accuracy** on object detection versus **91.2% for trained YOLO models**—a 22.7 percentage point gap. "Arithmetic-spatial hallucinations" cause the model to correctly identify objects but miscalculate their coordinates.

The free tier limits are now severely restrictive: only **5 requests per minute** and approximately **25 requests per day** for Gemini 2.5 Pro as of December 2025.

**Viable hybrid approach**: Use Gemini for scene classification (urban/rural/water) and obstacle type labeling, then feed those classifications to SAM for precise segmentation:

```python
# 1. Gemini identifies obstacle types and approximate locations
obstacles = detect_with_gemini(image)  # Returns bounding boxes + labels

# 2. SAM provides pixel-accurate masks at those locations
from segment_anything import SamPredictor
predictor = SamPredictor(sam_model)
predictor.set_image(image_array)

for obs in obstacles:
    center_x = (obs['bbox']['x1'] + obs['bbox']['x2']) // 2
    center_y = (obs['bbox']['y1'] + obs['bbox']['y2']) // 2
    
    masks, scores, _ = predictor.predict(
        point_coords=np.array([[center_x, center_y]]),
        point_labels=np.array([1])
    )
    precise_mask = masks[np.argmax(scores)]
```

---

## Free building footprint datasets provide excellent coverage

Three major free datasets cover most populated areas globally, eliminating the need for image segmentation in many cases.

**Overture Maps** (recommended) conflates data from OSM, Microsoft, Google, and Esri into **2.35+ billion building footprints** with global coverage. It prioritizes human-curated OSM data, filling gaps with ML-derived footprints:

```python
# Overture Maps CLI (simplest method)
pip install overturemaps

# Download buildings for your area
overturemaps download --bbox=-122.42,37.77,-122.40,37.79 \
    -f geojson --type=building -o buildings.geojson
```

**Microsoft Building Footprints** provides **1.4+ billion buildings** with ~1% false positive rate, derived from Maxar/Airbus imagery. Coverage is excellent in North America, Europe, and urban areas globally.

**OpenStreetMap** via OSMnx offers the most detailed building attributes (heights, types, addresses) in well-mapped areas:

```python
import osmnx as ox

# Extract buildings by bounding box
buildings = ox.features.features_from_bbox(
    bbox=(37.79, 37.77, -122.40, -122.42),  # north, south, east, west
    tags={'building': True}
)

# Filter to polygons only
buildings = buildings[buildings.geometry.type.isin(['Polygon', 'MultiPolygon'])]
```

**Converting to obstacle masks**:

```python
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_bounds

def buildings_to_obstacle_mask(buildings_gdf, bounds, resolution_meters=1.0):
    """Convert building polygons to binary raster mask."""
    west, south, east, north = bounds
    
    # Project to UTM for meter-based resolution
    buildings_utm = buildings_gdf.to_crs(buildings_gdf.estimate_utm_crs())
    bounds_utm = buildings_utm.total_bounds
    
    width = int((bounds_utm[2] - bounds_utm[0]) / resolution_meters)
    height = int((bounds_utm[3] - bounds_utm[1]) / resolution_meters)
    
    transform = from_bounds(bounds_utm[0], bounds_utm[1], 
                           bounds_utm[2], bounds_utm[3], width, height)
    
    # Rasterize: 1 = building, 0 = traversable
    shapes = [(geom, 1) for geom in buildings_utm.geometry if geom is not None]
    mask = rasterize(shapes, out_shape=(height, width), transform=transform,
                     fill=0, all_touched=True, dtype=np.uint8)
    
    return mask, transform
```

---

## High-resolution pathfinding with pyastar2d

For grids up to 10,000×10,000 cells, **pyastar2d** provides C++ performance with Python convenience, solving a 4000×4000 maze in **0.83 seconds**.

```python
pip install pyastar2d

import numpy as np
import pyastar2d
from scipy.ndimage import distance_transform_edt

def create_cost_grid(obstacle_mask, buffer_meters=3, resolution_meters=1):
    """Create weighted cost grid from binary obstacle mask."""
    buffer_pixels = int(buffer_meters / resolution_meters)
    
    cost = np.ones(obstacle_mask.shape, dtype=np.float32)
    cost[obstacle_mask == 1] = np.inf  # Obstacles impassable
    
    # Graduated costs near obstacles using distance transform
    walkable = obstacle_mask == 0
    distances = distance_transform_edt(walkable)
    
    # Within buffer zone: cost increases from 1 to 5 approaching obstacles
    in_buffer = (distances > 0) & (distances < buffer_pixels)
    cost[in_buffer] = 1.0 + 4.0 * (1.0 - distances[in_buffer] / buffer_pixels)
    
    return cost

# Find path
cost_grid = create_cost_grid(obstacle_mask, buffer_meters=3)
path = pyastar2d.astar_path(cost_grid, start=(100, 100), goal=(4500, 4500), 
                            allow_diagonal=True)
```

**Terrain-aware cost grids** assign different weights based on surface type:

```python
TERRAIN_COSTS = {
    'road': 1.0,
    'trail': 1.5,
    'open_ground': 2.5,
    'low_vegetation': 4.0,
    'dense_vegetation': 8.0,
    'building': np.inf,
    'water': np.inf
}

def apply_terrain_costs(cost_grid, terrain_classification):
    """Apply terrain-based costs to pathfinding grid."""
    for terrain_type, cost in TERRAIN_COSTS.items():
        mask = terrain_classification == terrain_type
        if cost == np.inf:
            cost_grid[mask] = np.inf
        else:
            cost_grid[mask] *= cost
    return cost_grid
```

For **very large areas**, use **Jump Point Search (JPS)** on uniform grids for 10-100× speedup, or **Hierarchical Pathfinding (HPA*)** which precomputes cluster connections for sub-millisecond online queries.

---

## Waypoint generation for realistic tactical movement

The raw A* output contains thousands of grid-aligned points. Converting this to usable tactical waypoints requires simplification, smoothing, resampling, and coordinate transformation.

**Complete waypoint processing pipeline**:

```python
import numpy as np
from rdp import rdp
from scipy.interpolate import CubicSpline
import rasterio

def process_path_to_waypoints(pixel_path, geotiff_path, interval_meters=5.0):
    """Convert pixel path to GPS waypoints at regular intervals."""
    
    # 1. Simplify path (Douglas-Peucker)
    simplified = rdp(np.array(pixel_path), epsilon=2.0)
    
    # 2. Smooth with cubic spline
    x, y = simplified[:, 0], simplified[:, 1]
    
    # Parameterize by arc length
    dx, dy = np.diff(x), np.diff(y)
    distances = np.sqrt(dx**2 + dy**2)
    s = np.concatenate([[0], np.cumsum(distances)])
    
    # Fit cubic splines
    cs_x = CubicSpline(s, x)
    cs_y = CubicSpline(s, y)
    
    # 3. Resample at fixed intervals
    total_length = s[-1]
    num_waypoints = int(total_length / interval_meters) + 1
    s_new = np.linspace(0, total_length, num_waypoints)
    
    smooth_x = cs_x(s_new)
    smooth_y = cs_y(s_new)
    pixel_waypoints = np.column_stack([smooth_x, smooth_y])
    
    # 4. Convert pixels to GPS
    with rasterio.open(geotiff_path) as src:
        gps_waypoints = []
        for col, row in pixel_waypoints:
            lon, lat = rasterio.transform.xy(src.transform, row, col)
            gps_waypoints.append([lon, lat])
    
    return np.array(gps_waypoints)

def to_geojson(gps_waypoints):
    """Export as GeoJSON for React frontend."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": gps_waypoints.tolist()
                },
                "properties": {"type": "tactical_route"}
            }
        ] + [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": wp.tolist()},
                "properties": {"waypoint_index": i}
            }
            for i, wp in enumerate(gps_waypoints[::5])  # Every 5th point as marker
        ]
    }
```

**Natural movement variation** avoids perfectly straight paths:

```python
def add_movement_variation(path, max_deviation=0.5):
    """Add subtle random variations for realistic movement."""
    directions = np.diff(path, axis=0)
    directions = np.vstack([directions, directions[-1]])
    
    # Perpendicular offset vectors
    perp = np.column_stack([-directions[:, 1], directions[:, 0]])
    perp = perp / (np.linalg.norm(perp, axis=1, keepdims=True) + 1e-10)
    
    # Smooth noise
    noise = np.cumsum(np.random.randn(len(path)) * 0.1)
    noise -= np.linspace(noise[0], noise[-1], len(path))  # Remove drift
    noise = noise / np.max(np.abs(noise) + 1e-10) * max_deviation
    
    return path + perp * noise[:, np.newaxis]
```

---

## Accuracy considerations and edge cases

Building detection achieves **70-92% F1 score** depending on urban density, with key challenges being tree canopy occlusion, shadows, and spectral similarity with roads. **Fences and walls** require sub-0.5m resolution imagery and DSM data—standard satellite imagery cannot reliably detect them.

**Buffer zones** are essential for safety. Recommended margins: buildings (2-5m), water (3-5m), dense vegetation (1-2m). The cost grid's graduated buffer approach naturally routes paths away from obstacle edges.

**Bridges vs underpasses** cannot be distinguished from 2D imagery alone. The solution is to fuse with OSM tags (`bridge=yes`, `tunnel=yes`) or DSM elevation data. Flag ambiguous crossings for manual review.

**Multi-source fusion** significantly improves reliability. Combining CNN segmentation with OSM footprints improved F1 scores by **1.1-12.5%** in academic studies:

```python
def compute_confidence(cnn_probability, osm_present, msft_present):
    """Fuse multiple sources into confidence score."""
    score = cnn_probability * 0.5
    if osm_present: score += 0.3
    if msft_present: score += 0.2
    return min(score, 1.0)
```

---

## Complete working pipeline example

```python
"""
Full tactical pathfinding pipeline:
Satellite image → Building detection → Cost grid → A* path → GPS waypoints
"""

import numpy as np
import osmnx as ox
import pyastar2d
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from rdp import rdp
from scipy.interpolate import CubicSpline

# Configuration
BBOX = (37.79, 37.77, -122.40, -122.42)  # north, south, east, west
RESOLUTION_M = 1.0
BUFFER_M = 3.0
WAYPOINT_INTERVAL_M = 5.0

# 1. Extract buildings from OSM
print("Extracting buildings...")
buildings = ox.features.features_from_bbox(BBOX, tags={'building': True})
buildings = buildings[buildings.geometry.type.isin(['Polygon', 'MultiPolygon'])]
buildings_utm = ox.projection.project_gdf(buildings)

# Add safety buffer
buildings_utm['geometry'] = buildings_utm.geometry.buffer(BUFFER_M)

# 2. Create obstacle mask
bounds = buildings_utm.total_bounds
width = int((bounds[2] - bounds[0]) / RESOLUTION_M)
height = int((bounds[3] - bounds[1]) / RESOLUTION_M)

from rasterio.transform import from_bounds
transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)

shapes = [(geom, 1) for geom in buildings_utm.geometry]
obstacle_mask = rasterize(shapes, (height, width), transform=transform, 
                          fill=0, all_touched=True, dtype=np.uint8)

# 3. Create cost grid with buffer zones
cost_grid = np.ones((height, width), dtype=np.float32)
cost_grid[obstacle_mask == 1] = np.inf

distances = distance_transform_edt(obstacle_mask == 0)
buffer_px = int(BUFFER_M / RESOLUTION_M)
in_buffer = (distances > 0) & (distances < buffer_px)
cost_grid[in_buffer] = 1 + 4 * (1 - distances[in_buffer] / buffer_px)

# 4. Find path
start_px = (50, 50)
goal_px = (height - 50, width - 50)
print(f"Finding path on {height}x{width} grid...")

path = pyastar2d.astar_path(cost_grid, start_px, goal_px, allow_diagonal=True)
print(f"Raw path: {len(path)} points")

# 5. Simplify and smooth
simplified = rdp(path, epsilon=2.0)
print(f"Simplified: {len(simplified)} points")

# Cubic spline smoothing
x, y = simplified[:, 0], simplified[:, 1]
s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
cs_x, cs_y = CubicSpline(s, x), CubicSpline(s, y)

n_waypoints = int(s[-1] * RESOLUTION_M / WAYPOINT_INTERVAL_M)
s_new = np.linspace(0, s[-1], n_waypoints)
smooth_path = np.column_stack([cs_x(s_new), cs_y(s_new)])

# 6. Convert to GPS
from pyproj import Transformer
utm_crs = buildings_utm.crs
to_wgs84 = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)

gps_waypoints = []
for row, col in smooth_path:
    utm_x = bounds[0] + col * RESOLUTION_M
    utm_y = bounds[3] - row * RESOLUTION_M  # Y inverted
    lon, lat = to_wgs84.transform(utm_x, utm_y)
    gps_waypoints.append([lon, lat])

print(f"Final waypoints: {len(gps_waypoints)} at {WAYPOINT_INTERVAL_M}m intervals")

# 7. Export GeoJSON for React
import json
geojson = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": gps_waypoints},
        "properties": {"type": "tactical_route", "waypoint_count": len(gps_waypoints)}
    }]
}
with open("tactical_route.geojson", "w") as f:
    json.dump(geojson, f)
```

---

## Conclusion

The optimal free approach for tactical pathfinding on satellite imagery combines **Overture Maps building footprints** (or SAM for areas with poor coverage) with **pyastar2d pathfinding** on buffer-enhanced cost grids, outputting spline-smoothed GPS waypoints as GeoJSON. This achieves pixel-level accuracy far exceeding your current DEM/WorldCover approach.

Key implementation choices: Use segment-geospatial with SAM for quick prototyping, upgrade to U-Net with SE-ResNeXt encoder for production accuracy. Always add 2-5m buffer zones around buildings. For areas larger than 10km², consider hierarchical pathfinding. Export GeoJSON LineStrings for React visualization via MapLibre GL or Deck.gl.

The entire pipeline uses only open-source tools: osmnx, segment-geospatial, pyastar2d, rasterio, scipy—all freely available via pip.