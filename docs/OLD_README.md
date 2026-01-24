# GeoRoute - Military Route Optimization System

Terrain-aware route planning using AI (Gemini) for intelligent routing decisions.

## 🚀 Quick Start

### Start the System
```bash
cd /home/aub/boo/GeoRoute
docker compose up -d
```

### Access Points
- **UI (Tactical Map):** http://localhost:9000
- **Backend API:** http://localhost:9001
- **API Documentation:** http://localhost:9001/docs

### Stop the System
```bash
docker compose down
```

---

## 📖 How to Use the System

### 1. **Set Your Start and End Points**

#### Method A: Click on Map
1. Open http://localhost:9000
2. **Left sidebar** → Find "Start Point" and "End Point" sections
3. Click **"Click Map to Set"** button
4. Click anywhere on the map to place the marker
   - **Green marker** = Start point
   - **Red marker** = End point

#### Method B: Enter Coordinates Manually
1. In the left sidebar, enter coordinates:
   - Start Point: Latitude, Longitude (e.g., `40.0150, -105.2705`)
   - End Point: Latitude, Longitude (e.g., `39.5501, -105.7821`)

### 2. **Select Your Vehicle**

In the left sidebar:
1. Click the **Vehicle Selection** dropdown
2. Choose from 4 military vehicles:
   - **M-ATV MRAP** (max slope: 35°, weight: 14.5 tons)
   - **HMMWV Humvee** (max slope: 40°, weight: 3.5 tons)
   - **Light Tactical Truck** (max slope: 30°, weight: 5 tons)
   - **Heavy Equipment Transporter** (max slope: 20°, weight: 35 tons)

### 3. **(Optional) Add Waypoints**

To force the route through specific points:
1. Click **"Add Waypoint"** button
2. Click on the map to place intermediate points
3. **Blue numbered markers** will appear
4. Routes will pass through these in order

### 4. **(Optional) Mark No-Go Zones**

To avoid specific areas:
1. Click **"Draw No-Go Zone"** toggle button
2. Click multiple points on the map to draw a polygon
3. Close the polygon by clicking near the start point
4. **Red shaded areas** = No-go zones
5. Routes will avoid these areas

### 5. **Plan Your Route**

1. Click the large **"Plan Route"** button
2. Wait for AI analysis (10-30 seconds)
3. Results will appear:
   - **Blue line on map** = Optimal route
   - **Colored triangles** = Hazards along the route
     - 🟡 Yellow = Low severity
     - 🟠 Orange = Medium severity
     - 🔴 Red = High severity
     - 💀 Red skull = Critical
   - **Bottom panel** = Elevation profile chart

### 6. **Review Route Details**

In the left sidebar, you'll see:
- **Route Name** (e.g., "Mountain Transit Route")
- **Total Distance** (km)
- **Estimated Duration** (hours)
- **Difficulty Badge** (easy/moderate/difficult/very_difficult/impassable)
- **Feasibility Score** (percentage bar)
- **Confidence Score** (how confident the AI is)
- **Key Challenges** (expandable list)
- **Recommendations** (expandable list)

### 7. **Inspect Hazards**

Click on any **colored triangle marker** on the map to see:
- Hazard type (e.g., steep slope, water crossing)
- Severity level
- Description
- Mitigation strategy (how to handle it)

### 8. **View Elevation Profile**

At the bottom of the screen:
- **Line chart** shows elevation changes along the route
- Hover over the chart to see elevation at specific points
- **Orange/Red segments** = Difficult/Very difficult terrain
- Click **collapse button** to hide/show

---

## 🗺️ Map Controls

### Zoom
- **Mouse wheel** to zoom in/out
- **+ / - buttons** in top-left corner
- **Note:** Zoom level 17-19 shows most detail. Beyond that, you may see "Map data not yet available" - this is normal for remote areas.

### Pan
- **Click and drag** the map to move around

### Layers
- **Layer toggle button** in top-right: Switch between satellite and terrain view

### Fullscreen
- **Fullscreen button** in top-right corner

---

## 📍 Example Coordinates to Try

### Mountain Route (Colorado)
```
Start:  40.0150, -105.2705  (Boulder, CO)
End:    39.5501, -105.7821  (Leadville, CO)
Vehicle: M-ATV MRAP
```

### Desert Route (Nevada)
```
Start:  36.1699, -115.1398  (Las Vegas, NV)
End:    35.0844, -114.5682  (Bullhead City, AZ)
Vehicle: HMMWV Humvee
```

### Coastal Route (California)
```
Start:  34.0522, -118.2437  (Los Angeles, CA)
End:    32.7157, -117.1611  (San Diego, CA)
Vehicle: Light Tactical Truck
```

---

## ⚙️ Advanced Features

### Quick Assessment
Before planning a full route:
1. Right-click any point on the map
2. Select **"Quick Assessment"**
3. Get instant terrain analysis for that area

### Alternative Routes
After planning:
- Scroll down in the left sidebar
- Look for **"Alternative Routes"** section
- Compare pros/cons of different path options

---

## 🔧 Troubleshooting

### "Configuration Error: VITE_API_URL"
The UI can't connect to the backend.
```bash
# Check if backend is running
curl http://localhost:9001/api/health

# Restart if needed
docker compose restart georoute-backend
```

### "Failed to fetch" Errors
```bash
# Check both services are up
docker compose ps

# View logs
docker compose logs georoute-backend
docker compose logs georoute-ui
```

### Map Tiles Not Loading
- **Check internet connection** - Map tiles are downloaded from external servers
- **Try switching layers** - Use the layer toggle button
- Some remote areas have limited high-zoom tiles - zoom out slightly

### Route Planning Takes Too Long
- **Gemini API rate limit** - Wait 60 seconds and try again
- **Complex route** - Simplify by removing waypoints or zooming out

---

## 🛠️ Technical Details

### Port Configuration
- Backend: `9001` (configurable in `.env`)
- UI: `9000` (configurable in `.env`)
- **No default fallbacks** - All ports must be explicitly set in `.env`

### API Keys Required
Set in `.env` file:
```bash
GOOGLE_MAPS_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
GOOGLE_CLOUD_PROJECT=your-project-id
```

Optional for enhanced features:
```bash
ORS_API_KEY=your-key-here
OPENTOPOGRAPHY_API_KEY=your-key-here
```

### Architecture
- **Backend:** Python FastAPI (port 9001)
- **UI:** React + Leaflet.js (port 9000)
- **AI:** Google Gemini 2.0 Flash
- **Maps:** Google Maps Elevation API + ESRI Satellite Tiles
- **Routing:** OSRM + OpenRouteService

---

## 📊 What the System Does

1. **Collects Terrain Data:**
   - Satellite imagery from Google Maps
   - Elevation data (30m resolution)
   - Slope calculations
   - Land cover analysis

2. **AI Analysis (Gemini):**
   - Analyzes satellite images visually
   - Cross-references with elevation data
   - Identifies hazards (cliffs, water, steep slopes)
   - Respects vehicle capabilities
   - Generates optimal waypoints

3. **Route Validation:**
   - Checks against road networks (OSRM)
   - Validates slope constraints
   - Calculates realistic travel times
   - Identifies alternative routes

4. **Output:**
   - Visual route on map
   - Hazard markers
   - Elevation profile
   - Detailed recommendations

---

## 📝 Notes

- **First route may be slow** - APIs need to warm up
- **Rate limits apply** - Gemini: ~15 requests/minute
- **Zoom limit** - Satellite tiles max out at zoom level 19
- **Accuracy** - Elevation data is ±10m, suitable for planning but verify on ground
- **No offline mode** - Internet required for all features

---

## 🆘 Support

- View logs: `docker compose logs -f`
- Restart: `docker compose restart`
- Full reset: `docker compose down && docker compose up -d --build`
- API docs: http://localhost:9001/docs
