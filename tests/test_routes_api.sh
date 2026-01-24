#!/bin/bash
# Test script for Google Routes API v2

echo "========================================="
echo "Google Routes API v2 Test Script"
echo "========================================="
echo ""

echo "Step 1: Testing Routes API v2 directly..."
docker exec georoute-backend python3 -c "
import asyncio
import sys
import json
sys.path.insert(0, '/app')

async def test():
    from georoute.config import load_config
    import httpx

    config = load_config()

    url = 'https://routes.googleapis.com/directions/v2:computeRoutes'

    request_body = {
        'origin': {
            'location': {
                'latLng': {
                    'latitude': 30.16,
                    'longitude': 47.49
                }
            }
        },
        'destination': {
            'location': {
                'latLng': {
                    'latitude': 30.18,
                    'longitude': 47.52
                }
            }
        },
        'travelMode': 'WALK',
        'computeAlternativeRoutes': True,
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': config.google_maps_api_key,
        'X-Goog-FieldMask': 'routes.legs.steps.startLocation,routes.legs.steps.endLocation,routes.legs.distanceMeters,routes.legs.duration,routes.description'
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=request_body, headers=headers)
        print(f'Status Code: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            route_count = len(data.get('routes', []))
            print(f'✓ SUCCESS: {route_count} routes returned')
            return True
        else:
            data = response.json()
            if 'error' in data:
                print(f'✗ ERROR: {data[\"error\"][\"message\"]}')
            return False

asyncio.run(test())
"

echo ""
echo "Step 2: Testing get_walking_routes() method..."
docker exec georoute-backend python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')

async def test():
    from georoute.clients.google_maps import GoogleMapsClient
    from georoute.config import load_config

    config = load_config()
    gmaps = GoogleMapsClient(api_key=config.google_maps_api_key)

    try:
        routes = await gmaps.get_walking_routes(
            origin=(30.16, 47.49),
            destination=(30.18, 47.52)
        )

        if len(routes) > 0:
            print(f'✓ SUCCESS: {len(routes)} routes found')
            for i, route in enumerate(routes):
                print(f'  Route {i+1}: {len(route[\"waypoints\"])} waypoints, {route[\"total_distance_m\"]/1000:.2f}km')
        else:
            print('✗ FAILED: No routes returned')
    except Exception as e:
        print(f'✗ ERROR: {e}')
    finally:
        await gmaps.close()

asyncio.run(test())
"

echo ""
echo "========================================="
echo "If both tests passed, Routes API is working!"
echo "========================================="
