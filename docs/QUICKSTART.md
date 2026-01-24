# 🚀 GeoRoute Quick Start Guide

## 5-Minute Tutorial

### 1. Start the System
```bash
cd /home/aub/boo/GeoRoute
docker compose up -d
```

### 2. Open the UI
**Navigate to:** http://localhost:9000

### 3. Set Start & End Points
Two methods:

**Method A - Click Map:**
- Left sidebar → Click **"Click Map to Set"** for Start Point
- Click anywhere on map (Green marker appears)
- Do same for End Point (Red marker)

**Method B - Enter Coordinates:**
```
Example (Colorado Mountains):
Start:  40.0150, -105.2705
End:    39.5501, -105.7821
```

### 4. Select Vehicle
Left sidebar → **Vehicle dropdown** → Choose:
- **M-ATV MRAP** (heavy, 35° max slope)
- **HMMWV** (light, 40° max slope) ← **Recommended for first try**
- Light Tactical Truck (30° max slope)
- Heavy Transporter (20° max slope)

### 5. Plan Route
Click the big **"Plan Route"** button → Wait 10-30 seconds

### 6. View Results
- **Blue line** = Your route
- **Colored triangles** = Hazards
- **Bottom chart** = Elevation profile
- **Left sidebar** = Route details, distance, time, challenges

---

## 🗺️ Map Tips

### Zoom Levels
- **Zoom 1-10:** Country/state view
- **Zoom 11-15:** City/regional view ✅ **Best for planning**
- **Zoom 16-19:** Street/building view ✅ **Most detailed**
- **Zoom 20+:** "Map data not yet available" ⚠️ **Too close - zoom out**

### Controls
- **Mouse wheel** = Zoom in/out
- **Click + drag** = Pan around
- **Top-right buttons** = Layer switch, Fullscreen

---

## 🎯 Try These Examples

### Easy Test Route (Flat Terrain)
```
Start: 34.0522, -118.2437  (Los Angeles)
End:   34.0407, -118.2468  (Downtown LA)
Vehicle: Light Tactical Truck
Expected: Easy route, mostly roads, <5 minutes
```

### Mountain Route (Challenging)
```
Start: 40.0150, -105.2705  (Boulder, CO)
End:   39.5501, -105.7821  (Leadville, CO)
Vehicle: M-ATV MRAP
Expected: Difficult route, mountain passes, ~2.5 hours
```

### Desert Route (Off-Road)
```
Start: 36.1699, -115.1398  (Las Vegas)
End:   35.0844, -114.5682  (Bullhead City, AZ)
Vehicle: HMMWV Humvee
Expected: Moderate, some off-road, ~1.5 hours
```

---

## ❌ Common Issues & Fixes

### Issue: "Configuration Error"
**Fix:**
```bash
docker compose restart georoute-backend
# Wait 10 seconds, then refresh browser
```

### Issue: Map tiles not loading
**Fix:**
- Check internet connection
- Click **layer toggle** button (satellite ↔ terrain)
- Zoom out if too close

### Issue: "Too Many Requests" / Route fails
**Fix:**
- **Gemini rate limit hit**
- Wait 60 seconds
- Try again

### Issue: Route planning is slow
**Normal:**
- First request: 20-30 seconds (warming up)
- Subsequent requests: 10-15 seconds
- Complex routes (waypoints, no-go zones): 30-60 seconds

---

## 🎮 Advanced Usage

### Add Waypoints
Force route through specific points:
1. Click **"Add Waypoint"** button
2. Click map to place blue numbered markers
3. Route will pass through these in order

### Mark No-Go Zones
Avoid specific areas:
1. Toggle **"Draw No-Go Zone"** button ON
2. Click multiple points to draw polygon
3. Close polygon (click near start)
4. Red shaded area = forbidden zone

### View Hazards
- Click any **colored triangle** on map
- See: Type, severity, description, mitigation
- Colors: 🟡 Low → 🟠 Medium → 🔴 High → 💀 Critical

### Elevation Profile
- Bottom panel shows elevation changes
- Hover to see elevation at specific points
- Orange/red = difficult terrain
- Click collapse button to hide/show

---

## 📱 Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [Settings Sidebar]           [MAP AREA]          [Controls] │
│                                                               │
│ • Start Point                 🟢 Green = Start               │
│ • End Point                   🔴 Red = End                   │
│ • Vehicle                     🔵 Blue = Waypoints            │
│ • Add Waypoint                🔺 Triangles = Hazards         │
│ • Draw No-Go                  ━━━ Blue line = Route         │
│ • [PLAN ROUTE]                                               │
│                                                               │
│ Results:                                                      │
│ • Distance                                                    │
│ • Duration                                                    │
│ • Difficulty                                                  │
│ • Challenges                                                  │
│ • Recommendations                                             │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│              [ELEVATION PROFILE CHART]                        │
│              (Collapsible bottom panel)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 Quick Links

- **UI:** http://localhost:9000
- **API:** http://localhost:9001
- **API Docs:** http://localhost:9001/docs
- **Health Check:** http://localhost:9001/api/health

---

## 📞 Need Help?

1. **Check logs:**
   ```bash
   docker compose logs georoute-backend
   docker compose logs georoute-ui
   ```

2. **Restart everything:**
   ```bash
   docker compose down
   docker compose up -d
   ```

3. **See full README:**
   ```bash
   cat /home/aub/boo/GeoRoute/README.md
   ```

---

**Happy Routing! 🗺️🚗💨**
