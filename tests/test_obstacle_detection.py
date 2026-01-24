#!/usr/bin/env python3
"""
Test script for Gemini Vision obstacle detection and pathfinding.

Usage:
    python test_obstacle_detection.py <satellite_image.png> --start lat,lon --end lat,lon

Or interactively:
    python test_obstacle_detection.py <satellite_image.png> --interactive

The script will:
1. Load the satellite image
2. Run Gemini obstacle detection
3. Run A* pathfinding
4. Save visualization with obstacles and path
"""

import asyncio
import argparse
import base64
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from georoute.config import load_config
from georoute.processing.gemini_obstacle_detector import GeminiObstacleDetector
from georoute.processing.grid_pathfinder import GridPathfinder, generate_tactical_routes


def load_image_base64(image_path: str) -> str:
    """Load image and convert to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def visualize_detection(
    image_path: str,
    obstacle_mask: np.ndarray,
    routes: list,
    bounds: dict,
    output_path: str,
    grid_size: int = 32
):
    """
    Create visualization overlay on the satellite image.

    Args:
        image_path: Path to original satellite image
        obstacle_mask: Binary obstacle grid
        routes: List of route dictionaries with waypoints
        bounds: Geographic bounds
        output_path: Path to save visualization
        grid_size: Size of the obstacle detection grid
    """
    # Load original image
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # Create overlay for obstacles
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate cell size in pixels
    cell_w = width / grid_size
    cell_h = height / grid_size

    # Draw obstacle cells (semi-transparent red)
    for row in range(grid_size):
        for col in range(grid_size):
            if obstacle_mask[row, col] == 1:
                x1 = int(col * cell_w)
                y1 = int(row * cell_h)
                x2 = int((col + 1) * cell_w)
                y2 = int((row + 1) * cell_h)
                draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 100))

    # Draw grid lines (very faint)
    for i in range(grid_size + 1):
        x = int(i * cell_w)
        y = int(i * cell_h)
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 30), width=1)
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 30), width=1)

    # Composite overlay on image
    img = Image.alpha_composite(img, overlay)

    # Draw routes
    draw = ImageDraw.Draw(img)
    route_colors = [
        (0, 255, 0, 255),    # Green - Direct
        (0, 150, 255, 255),  # Blue - Left
        (255, 150, 0, 255),  # Orange - Right
    ]

    for i, route in enumerate(routes):
        color = route_colors[i % len(route_colors)]
        waypoints = route.get("waypoints", [])

        if len(waypoints) < 2:
            continue

        # Convert GPS to pixel coordinates
        points = []
        for wp in waypoints:
            lat = wp["lat"]
            lon = wp["lon"]

            # GPS to pixel (row 0 = north = top, col 0 = west = left)
            px = int((lon - bounds["west"]) / (bounds["east"] - bounds["west"]) * width)
            py = int((bounds["north"] - lat) / (bounds["north"] - bounds["south"]) * height)

            # Clamp to image bounds
            px = max(0, min(width - 1, px))
            py = max(0, min(height - 1, py))
            points.append((px, py))

        # Draw route line
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)

        # Draw waypoint markers
        for j, (px, py) in enumerate(points):
            if j == 0:
                # Start point - green circle
                draw.ellipse([px-8, py-8, px+8, py+8], fill=(0, 255, 0, 255), outline=(255, 255, 255))
            elif j == len(points) - 1:
                # End point - red circle
                draw.ellipse([px-8, py-8, px+8, py+8], fill=(255, 0, 0, 255), outline=(255, 255, 255))
            else:
                # Intermediate - small white dot
                draw.ellipse([px-3, py-3, px+3, py+3], fill=(255, 255, 255, 200))

        # Label route
        if points:
            label_x, label_y = points[len(points)//2]
            route_name = route.get("name", f"Route {i+1}")
            draw.text((label_x + 10, label_y), route_name, fill=color)

    # Add legend
    legend_y = 10
    draw.rectangle([10, legend_y, 200, legend_y + 100], fill=(0, 0, 0, 180))
    draw.text((15, legend_y + 5), "LEGEND:", fill=(255, 255, 255))
    draw.rectangle([15, legend_y + 25, 30, legend_y + 35], fill=(255, 0, 0, 100))
    draw.text((35, legend_y + 22), "Detected Obstacles", fill=(255, 255, 255))
    draw.line([(15, legend_y + 50), (30, legend_y + 50)], fill=(0, 255, 0), width=3)
    draw.text((35, legend_y + 45), "Direct Route", fill=(255, 255, 255))
    draw.line([(15, legend_y + 70), (30, legend_y + 70)], fill=(0, 150, 255), width=3)
    draw.text((35, legend_y + 65), "Left Approach", fill=(255, 255, 255))
    draw.line([(15, legend_y + 90), (30, legend_y + 90)], fill=(255, 150, 0), width=3)
    draw.text((35, legend_y + 85), "Right Approach", fill=(255, 255, 255))

    # Convert back to RGB and save
    img = img.convert("RGB")
    img.save(output_path)
    print(f"Saved visualization to: {output_path}")


async def test_detection(
    image_path: str,
    bounds: dict,
    start_gps: tuple,
    end_gps: tuple,
    output_path: str,
    grid_size: int = 32,
    buffer_pixels: int = 2
):
    """
    Run full obstacle detection and pathfinding test.

    Args:
        image_path: Path to satellite image
        bounds: Geographic bounds {"north", "south", "east", "west"}
        start_gps: (lat, lon) start position
        end_gps: (lat, lon) end position
        output_path: Path to save visualization
        grid_size: Detection grid size (default 32)
        buffer_pixels: Buffer around obstacles (default 2)
    """
    print(f"\n{'='*60}")
    print("GEMINI VISION OBSTACLE DETECTION TEST")
    print(f"{'='*60}")
    print(f"Image: {image_path}")
    print(f"Grid size: {grid_size}x{grid_size}")
    print(f"Buffer: {buffer_pixels} cells")
    print(f"Start: {start_gps}")
    print(f"End: {end_gps}")
    print(f"Bounds: {bounds}")
    print(f"{'='*60}\n")

    # Load config
    config = load_config()

    # Initialize detector
    detector = GeminiObstacleDetector(
        api_key=config.gemini_api_key,
        buffer_pixels=buffer_pixels,
        grid_size=grid_size
    )

    # Load image
    print("Loading satellite image...")
    image_b64 = load_image_base64(image_path)
    print(f"Image size: {len(image_b64)} bytes (base64)")

    # Run detection
    print("\nRunning Gemini obstacle detection...")
    result = await detector.detect_obstacles(
        satellite_image_base64=image_b64,
        bounds=bounds,
        context="tactical area"
    )

    print(f"\nDetection Results:")
    print(f"  Obstacles found: {result.obstacle_count} cells")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Notes: {result.detection_notes}")

    # Calculate coverage
    total_cells = grid_size * grid_size
    obstacle_pct = 100 * np.sum(result.obstacle_mask) / total_cells
    buffered_pct = 100 * np.sum(result.buffered_mask) / total_cells
    print(f"  Raw obstacle coverage: {obstacle_pct:.1f}%")
    print(f"  Buffered obstacle coverage: {buffered_pct:.1f}%")

    # Run pathfinding
    print("\nRunning A* pathfinding...")
    routes = generate_tactical_routes(
        obstacle_mask=result.buffered_mask,
        start_gps=start_gps,
        end_gps=end_gps,
        bounds=bounds
    )

    print(f"\nGenerated {len(routes)} routes:")
    for route in routes:
        wp_count = len(route.get("waypoints", []))
        path_clear = route.get("path_clear", False)
        status = "✓ Clear" if path_clear else "⚠ Fallback"
        print(f"  {route['route_id']}. {route['name']}: {wp_count} waypoints [{status}]")

    # Create visualization
    print("\nGenerating visualization...")
    visualize_detection(
        image_path=image_path,
        obstacle_mask=result.buffered_mask,
        routes=routes,
        bounds=bounds,
        output_path=output_path,
        grid_size=grid_size
    )

    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")
    print(f"Output saved to: {output_path}")

    return result, routes


def main():
    parser = argparse.ArgumentParser(description="Test Gemini obstacle detection")
    parser.add_argument("image", help="Path to satellite image")
    parser.add_argument("--start", required=True, help="Start GPS: lat,lon")
    parser.add_argument("--end", required=True, help="End GPS: lat,lon")
    parser.add_argument("--north", type=float, help="North bound (default: infer from start/end)")
    parser.add_argument("--south", type=float, help="South bound")
    parser.add_argument("--east", type=float, help="East bound")
    parser.add_argument("--west", type=float, help="West bound")
    parser.add_argument("--grid", type=int, default=32, help="Grid size (default: 32)")
    parser.add_argument("--buffer", type=int, default=2, help="Buffer pixels (default: 2)")
    parser.add_argument("--output", "-o", default="test_result.png", help="Output path")

    args = parser.parse_args()

    # Parse start/end
    start_lat, start_lon = map(float, args.start.split(","))
    end_lat, end_lon = map(float, args.end.split(","))

    # Calculate bounds with margin if not provided
    margin = 0.002  # ~200m margin
    if args.north and args.south and args.east and args.west:
        bounds = {
            "north": args.north,
            "south": args.south,
            "east": args.east,
            "west": args.west
        }
    else:
        bounds = {
            "north": max(start_lat, end_lat) + margin,
            "south": min(start_lat, end_lat) - margin,
            "east": max(start_lon, end_lon) + margin,
            "west": min(start_lon, end_lon) - margin
        }
        print(f"Auto-calculated bounds: {bounds}")

    # Run test
    asyncio.run(test_detection(
        image_path=args.image,
        bounds=bounds,
        start_gps=(start_lat, start_lon),
        end_gps=(end_lat, end_lon),
        output_path=args.output,
        grid_size=args.grid,
        buffer_pixels=args.buffer
    ))


if __name__ == "__main__":
    main()
