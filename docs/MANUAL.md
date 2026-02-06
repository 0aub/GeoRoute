# GeoRoute Project Manual

**Version 2.0** | **Last Updated: February 2026**

---

## Executive Summary

GeoRoute represents a significant advancement in tactical route planning technology, combining the analytical power of Google's latest Gemini AI models with real-world satellite imagery to provide military planners and tactical analysts with an intelligent decision-support system. The platform addresses a fundamental challenge in tactical operations: the need to quickly assess and plan infantry movement routes while accounting for terrain, enemy positions, cover availability, and approach angles.

Traditional route planning relies heavily on manual map analysis and the experience of individual planners. GeoRoute augments this process by automatically analyzing satellite imagery, identifying potential cover positions, calculating exposure to enemy observation, and generating multiple route options with quantified risk assessments. The system does not replace human judgment but rather provides planners with comprehensive, data-driven analysis to inform their decisions.

This manual serves as the definitive reference for deploying, configuring, operating, and extending the GeoRoute system. It is intended for system administrators responsible for installation and maintenance, tactical analysts who will use the system operationally, and developers who may need to customize or extend its capabilities.

---

## What's New in Version 2.0

Version 2.0 introduces significant infrastructure improvements for production deployments:

**NGINX Reverse Proxy**
- All traffic now routes through NGINX on port 80
- Rate limiting protects against abuse (10 req/s API, 30 req/s general)
- Gzip compression reduces bandwidth usage
- Security headers prevent common web vulnerabilities
- Long timeouts (3 minutes) for AI operations
- SSE (Server-Sent Events) properly proxied for progress streaming

**Vertex AI Support**
- Production-recommended AI backend with higher quotas
- Service account authentication for enterprise deployments
- Better reliability and faster response times
- Seamless fallback to AI Studio for development

**Load Balancing**
- Scale backend replicas with single command: `docker compose up -d --scale georoute-backend=3`
- NGINX least-connections algorithm distributes load
- Handle more concurrent users during AI processing

**Unified Configuration**
- Single docker-compose.yml for all environments
- Consolidated .env.example with all options
- Simplified deployment process

**Error Sanitization**
- User-friendly error messages without exposing internals
- Proper HTTP status codes (429 for rate limits, 503 for unavailable)
- Detailed logging for administrators

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Configuration Reference](#3-configuration-reference)
4. [User Guide](#4-user-guide)
5. [System Architecture](#5-system-architecture)
6. [API Reference](#6-api-reference)
7. [Data Models](#7-data-models)
8. [AI Prompts & Customization](#8-ai-prompts--customization)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Backend Architecture](#10-backend-architecture)
11. [Troubleshooting](#11-troubleshooting)
12. [Extending the System](#12-extending-the-system)

---

## 1. Introduction

### 1.1 What is GeoRoute?

GeoRoute is an AI-powered tactical route planning system designed for infantry movement analysis. At its core, the system leverages Google's Gemini family of large language models, which possess the remarkable ability to understand and analyze visual imagery, to perform sophisticated tactical assessments that would traditionally require significant manual effort and expertise.

The system operates on a fundamental principle: tactical route planning is inherently a visual and spatial problem. By providing AI models with actual satellite imagery of the operational area, along with marked positions of friendly and enemy forces, the system can generate analysis that accounts for real-world terrain features such as buildings, vegetation, roads, and open ground. This approach yields results that are grounded in the actual geography of the area rather than abstract calculations.

GeoRoute integrates four primary technologies to deliver its capabilities:

**Satellite Imagery Foundation**: The system utilizes ESRI World Imagery, the same high-resolution satellite imagery used by professional GIS applications worldwide. This imagery is fetched in real-time and stitched together to create seamless maps of any area within the supported region. The use of actual satellite imagery, rather than simplified maps, allows the AI to identify terrain features, buildings, roads, and vegetation that affect tactical movement.

**Advanced AI Analysis**: Google's Gemini 3 Pro model, specifically the image-generation variant, can actually draw on images. When given a satellite image with marked start and end positions, it generates tactical routes by drawing directly on the imagery, creating visually intuitive route overlays that account for obstacles and cover. The Gemini 3 Flash model, optimized for vision analysis, then examines these routes to assess risk, identify weak points, and generate recommendations.

**Tactical Simulation Engine**: Beyond AI analysis, the system includes a geometric simulation engine that models enemy fields of view as vision cones. These cones are calculated based on realistic parameters for different enemy types (snipers with narrow but long-range vision, riflemen with wider but shorter-range observation). The AI then analyzes which portions of a route fall within these vision cones and, critically, whether terrain features provide concealment.

**Interactive Mapping Interface**: The user interface is built on Leaflet, an industry-standard mapping library, enhanced with military-specific functionality. Users can place units using NATO APP-6 standard symbology, draw movement routes, position enemies with specific facing directions, and visualize the complete tactical picture on a single integrated display.

### 1.2 Core Capabilities

The system provides five primary capabilities, each designed to address specific aspects of tactical route planning:

**AI-Powered Route Generation** allows users to simply mark friendly and enemy positions, after which the AI generates multiple tactical route options. Each route represents a different approach philosophy, from balanced routes that trade off speed and concealment, to stealth routes that prioritize maximum cover at the cost of longer travel times. The AI draws these routes directly on satellite imagery, ensuring they follow realistic paths around buildings, along walls, and through areas of natural cover.

**User Route Evaluation** enables experienced planners to draw their own proposed routes and submit them for AI analysis. This capability recognizes that human expertise remains essential and provides a way to validate planned routes against AI assessment. The system evaluates each segment of the user-drawn route, identifies optimal positions for different unit types, and provides specific recommendations for improving the approach.

**Tactical Simulation** provides the most detailed analysis by combining geometric vision cone calculations with AI-based cover assessment. Users place enemy units with specific types and facing directions, then draw a movement route. The system first calculates which route segments geometrically fall within enemy observation, then uses AI vision analysis to determine whether buildings, walls, or terrain actually block the line of sight. This dual-layer analysis prevents false positives where a route might appear exposed based on geometry alone but is actually protected by intervening structures.

**Multi-Dimensional Scoring** quantifies tactical quality across four dimensions: stealth (how hidden the approach remains), safety (survival probability), terrain usage (how effectively the route exploits available cover), and flanking (the tactical advantage gained from approach angle relative to enemy facing). These individual scores combine into an overall rating that allows direct comparison between route options.

**Verdict Classification** translates numerical scores into actionable categories. Routes rated EXCELLENT represent near-optimal approaches with minimal exposure. GOOD routes are tactically sound with minor improvements possible. ACCEPTABLE routes carry manageable risk and may be suitable when time or terrain constraints limit options. RISKY routes have significant exposure or tactical disadvantages and should only be used when no alternatives exist.

### 1.3 Geographic Scope

GeoRoute is configured to operate exclusively within the Gulf Cooperation Council region, encompassing Saudi Arabia, the United Arab Emirates, Kuwait, Bahrain, Qatar, and Oman. This geographic restriction, defined as the area between latitude 12°N to 32°N and longitude 34°E to 60°E, is implemented both as a user interface constraint and as a server-side validation.

The restriction serves multiple purposes. Operationally, it ensures the system is used within its intended context. Technically, it allows optimization of satellite imagery caching and AI model prompting for the specific terrain types common in the Gulf region, including urban environments, desert terrain, and coastal areas. The system's AI prompts and scoring algorithms have been calibrated for the building styles, vegetation patterns, and terrain features typical of this region.

When users attempt to place units or draw routes outside the permitted area, the system displays a clear notification explaining the geographic restriction. The map interface includes a subtle visual indicator showing the boundaries of the operational area, and the map cannot be panned significantly beyond these limits.

---

## 2. Installation

This section provides comprehensive guidance for deploying GeoRoute in various environments, from local development setups to production deployments. The system is containerized using Docker, which ensures consistent behavior across different operating systems and simplifies dependency management. Whether you are setting up a personal workstation for evaluation or deploying to cloud infrastructure for team use, the installation process follows the same fundamental steps.

### 2.1 Prerequisites

Before beginning installation, ensure your system meets the following requirements. The Docker-based deployment abstracts away most software dependencies, but you will need the core container runtime and access to Google Cloud services for the AI and mapping capabilities.

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Google Cloud Account | - | API access |
| Git | 2.0+ | Clone repository |

### 2.2 API Keys Required

GeoRoute requires access to Google Cloud services for both its mapping capabilities and AI analysis. You will need to obtain two types of credentials: a Google Maps API key for satellite imagery and elevation data, and either a Gemini API key (for simple deployments) or Vertex AI credentials (for production use with higher rate limits).

It is important to understand the distinction between these authentication methods. The Google Maps API key is straightforward and works the same way regardless of your AI choice. For AI services, you have two options that are mutually exclusive. AI Studio provides a simple API key that is easy to obtain and includes a free tier, making it ideal for development and evaluation. Vertex AI requires more setup, including service account creation and billing enablement, but provides significantly higher rate limits and is recommended for any production or team deployment where multiple users may be making concurrent requests.

#### Google Maps API Key

The Google Maps API key enables the system to fetch satellite imagery tiles and elevation data. This key is always required regardless of which AI authentication method you choose.

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing
3. Enable these APIs:
   - **Maps Elevation API**
   - **Maps Static API**
4. Create an API key with these APIs enabled

#### Gemini API Key (Option 1: AI Studio)
1. Go to [AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Key format: `AIzaSy...` (starts with "AIzaSy")

#### Vertex AI (Option 2: Enterprise)
See [Section 2.5 Vertex AI Setup](#25-vertex-ai-setup).

### 2.3 Basic Installation

```bash
# Clone the repository
git clone https://github.com/0aub/GeoRoute.git
cd GeoRoute

# Create environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use any text editor
```

### 2.4 Environment Variables

Create a `.env` file with these variables:

```bash
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# Backend API port (required)
BACKEND_PORT=8001

# Backend bind address
BACKEND_HOST=0.0.0.0

# Frontend port
UI_PORT=8080

# CORS origins (comma-separated)
# For development:
CORS_ORIGINS=http://localhost:8080
# For production:
# CORS_ORIGINS=http://your-domain.com,https://your-domain.com

# API URL for frontend to reach backend
VITE_API_URL=http://localhost:8001

# =============================================================================
# GOOGLE APIS (REQUIRED)
# =============================================================================

# Google Cloud Project ID
GOOGLE_CLOUD_PROJECT=your-project-id

# Google Maps API Key (needs Elevation + Static Maps APIs)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# =============================================================================
# AI SERVICE - Choose ONE option
# =============================================================================

# OPTION 1: AI Studio (simpler, free tier available)
GEMINI_API_KEY=your-gemini-api-key

# OPTION 2: Vertex AI (higher quotas, requires billing)
# USE_VERTEX_AI=true
# VERTEX_LOCATION=us-central1
```

### 2.5 Vertex AI Setup

While AI Studio provides the simplest path to getting GeoRoute running, production deployments should use Vertex AI for several important reasons. Vertex AI operates within your Google Cloud project's infrastructure, providing better security controls, audit logging, and integration with your organization's existing cloud governance. More practically, Vertex AI offers substantially higher rate limits, which becomes critical when multiple analysts are using the system simultaneously or when performing batch analysis of multiple routes.

The setup process requires creating a service account, which is Google Cloud's mechanism for giving applications their own identity and permissions. This service account will be granted permission to invoke AI models, and its credentials (in the form of a JSON key file) will be mounted into the GeoRoute container at runtime. This approach follows security best practices by avoiding the embedding of credentials in code or configuration files that might be committed to version control.

#### Step 1: Create Service Account

The first step is to create a dedicated service account for GeoRoute. This account should be used exclusively for this application to maintain clear separation of concerns and simplify permission auditing.
```bash
# In Google Cloud Console or gcloud CLI:
gcloud iam service-accounts create georoute-sa \
  --display-name="GeoRoute Service Account"
```

#### Step 2: Grant Permissions
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:georoute-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Step 3: Download JSON Key
```bash
gcloud iam service-accounts keys create service-account.json \
  --iam-account=georoute-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Step 4: Place Key File
Move `service-account.json` to the GeoRoute root directory:
```
GeoRoute/
├── service-account.json   <-- Here
├── docker-compose.yml
├── .env
└── ...
```

#### Step 5: Configure Environment
```bash
# In .env:
USE_VERTEX_AI=true
VERTEX_LOCATION=us-central1
GOOGLE_CLOUD_PROJECT=your-project-id

# GEMINI_API_KEY can be left empty or removed
```

### 2.6 Running the System

```bash
# Start all services
docker compose up --build

# Or run in background
docker compose up --build -d

# View logs
docker compose logs -f
```

### 2.7 Accessing the Application

| Service | URL | Description |
|---------|-----|-------------|
| **UI** | http://localhost:8080 | Main application interface |
| **API** | http://localhost:8001 | Backend REST API |
| **Health** | http://localhost:8001/api/health | Health check endpoint |

### 2.8 Stopping the System

```bash
# Stop and remove containers
docker compose down

# Stop, remove containers, and delete volumes
docker compose down -v
```

---

## 3. Configuration Reference

GeoRoute follows a configuration-driven design philosophy where operational parameters, AI model selections, and even the prompts used to instruct the AI are externalized into configuration files. This approach offers significant advantages: administrators can tune system behavior without modifying source code, different deployments can be customized for specific operational contexts, and AI prompts can be iteratively improved based on observed results.

The configuration is split between environment variables (for deployment-specific settings like API keys and network ports) and YAML files (for application behavior). This separation ensures that sensitive credentials remain outside the codebase while operational parameters are version-controlled and documented.

### 3.1 Application Configuration (config.yaml)

The file `georoute/config.yaml` serves as the central configuration hub for all operational parameters. This file is read fresh for each API request, meaning changes take effect immediately without requiring a system restart. This hot-reload capability is particularly valuable when tuning AI prompts or adjusting scoring thresholds based on operational feedback.

The configuration file is organized into logical sections, each controlling a specific aspect of system behavior. Understanding these sections is essential for administrators who need to customize the system for their specific operational requirements.

#### Route Generation Settings

```yaml
route_generation:
  # Method for generating routes
  # Currently only "gemini_image" is supported
  method: "gemini_image"

  # Number of routes to generate (1-3)
  # 2 is recommended: balanced + stealth
  num_routes: 2
```

#### AI Model Selection

```yaml
gemini:
  # Model for drawing routes on satellite images
  # Requires image generation capability
  image_model: "gemini-3-pro-image-preview"

  # Model for text-based analysis and scoring
  text_model: "gemini-2.5-flash"

  # Model for vision-based tactical analysis
  # Used for simulation and route evaluation
  analysis_model: "gemini-3-flash-preview"
```

#### Marker Appearance

```yaml
markers:
  size: 6  # Marker radius in pixels
  start_color: [0, 100, 255]    # RGB: Blue for soldiers
  end_color: [255, 50, 50]      # RGB: Red for enemies
  outline_color: [255, 255, 255] # RGB: White outline
  outline_width: 2
```

#### Geographic Restrictions

```yaml
geo:
  gcc_bounds:
    north: 32.0   # Northern boundary (latitude)
    south: 12.0   # Southern boundary (latitude)
    east: 60.0    # Eastern boundary (longitude)
    west: 34.0    # Western boundary (longitude)
```

### 3.2 Enemy Vision Specifications

The tactical simulation system models enemy observation capabilities through vision cones, which are triangular areas emanating from each enemy position in the direction they are facing. These vision cones represent the area an enemy could theoretically observe, though the actual detection capability is further modified by terrain and cover analysis performed by the AI.

The vision specifications are calibrated to represent realistic observation capabilities for different enemy types. Snipers, equipped with magnified optics, can effectively observe at extended ranges but have a narrow field of view due to scope limitations. Standard riflemen have a much wider field of awareness but their effective observation range is limited by the naked eye or iron sights. Observers, typically equipped with binoculars or spotting scopes, fall between these extremes.

These parameters are currently defined in the source code rather than configuration files because they require synchronized updates across both frontend (for visualization) and backend (for analysis). Future versions may externalize these to configuration.

| Enemy Type | Range | Angle | Tactical Significance |
|------------|-------|-------|----------------------|
| Sniper | 500m | 30° | Long-range precision threat; narrow but deep danger zone |
| Rifleman | 100m | 60° | Close-quarters threat; wide but shallow danger zone |
| Observer | 400m | 45° | Detection and coordination threat; triggers alerts |

### 3.3 Scoring Thresholds

The verdict system translates complex multi-dimensional tactical analysis into actionable classifications. Understanding the criteria behind each verdict helps analysts interpret results and make informed decisions about route selection.

The scoring system is intentionally conservative, meaning the AI is calibrated to be critical rather than optimistic. This design choice reflects the asymmetric consequences of tactical errors: an overly optimistic assessment that leads to a failed approach has far greater consequences than a conservative assessment that leads to selection of a longer but safer route. Most routes analyzed by the system will fall in the ACCEPTABLE to GOOD range; EXCELLENT verdicts are reserved for genuinely superior tactical approaches.

| Verdict | Score Range | Interpretation |
|---------|-------------|----------------|
| EXCELLENT | 8.5 - 10.0 | Exceptional tactical approach exploiting multiple advantages. Route maximizes cover (90%+), achieves rear or strong flanking position, and has zero exposed segments. Suitable for high-stakes operations. |
| GOOD | 6.5 - 8.4 | Solid tactical approach with good fundamentals. Route maintains substantial cover (75%+), achieves some flanking advantage, and has at most one brief exposed segment. Recommended for most operations. |
| ACCEPTABLE | 4.5 - 6.4 | Workable approach with identifiable weaknesses. Route has moderate cover (50-75%) and shows tactical consideration. May be appropriate when terrain constraints limit options. |
| RISKY | 0 - 4.4 | Approach with significant tactical disadvantages. Route has insufficient cover, critical exposure points, or frontal approach to enemy positions. Should only be used when no alternatives exist. |

### 3.4 Docker Compose Configuration

The `docker-compose.yml` defines two services:

#### Backend Service (georoute-backend)

```yaml
georoute-backend:
  build:
    context: ./georoute
    dockerfile: Dockerfile
  ports:
    - "${BACKEND_PORT}:${BACKEND_PORT}"
  environment:
    - BACKEND_PORT=${BACKEND_PORT}
    - BACKEND_HOST=${BACKEND_HOST}
    - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
    - GEMINI_API_KEY=${GEMINI_API_KEY}
    - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
    - CORS_ORIGINS=${CORS_ORIGINS}
    - RELOAD=true
    - USE_VERTEX_AI=${USE_VERTEX_AI:-false}
    - VERTEX_LOCATION=${VERTEX_LOCATION:-us-central1}
    - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
  volumes:
    - ./georoute:/app/georoute:ro  # Hot reload
    - ./service-account.json:/app/service-account.json:ro
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:${BACKEND_PORT}/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Frontend Service (georoute-ui)

```yaml
georoute-ui:
  build:
    context: ./ui
    dockerfile: Dockerfile
  ports:
    - "${UI_PORT}:8080"
  environment:
    - VITE_API_URL=${VITE_API_URL}
  volumes:
    - ./ui/src:/app/src  # Hot reload
  depends_on:
    georoute-backend:
      condition: service_healthy
```

---

## 4. User Guide

This section provides operational guidance for using GeoRoute effectively. While the system is designed to be intuitive, understanding its workflow and capabilities will help analysts extract maximum value from its AI-powered analysis. The guide progresses from basic interface orientation through each of the three primary operational modes.

### 4.1 Interface Overview

The GeoRoute interface follows a map-centric design common to geographic information systems, with the interactive satellite map occupying the central workspace and controls organized in a sidebar panel. This layout prioritizes the spatial awareness essential to tactical planning while keeping tools readily accessible.

The application presents three distinct areas that work together:

**The Map Area** dominates the center of the interface and displays high-resolution ESRI World Imagery. This is not a simplified street map but actual satellite photography, allowing analysts to identify buildings, vegetation, terrain features, and other elements relevant to tactical movement. The map supports standard pan and zoom interactions, with zoom levels ranging from regional overview (level 7) to street-level detail (level 19). For accurate tactical planning, the system requires zoom level 17 or higher when placing units, ensuring analysts work with sufficient detail to make meaningful assessments.

**The Sidebar** on the left provides all controls for the current operational mode. Rather than overwhelming users with every available option, the sidebar adapts its content based on the selected mode. In Route mode, it displays unit placement controls and route generation options. In Draw mode, it shows waypoint management and squad composition settings. In Simulate mode, it presents enemy placement, facing direction controls, and simulation parameters. This contextual approach reduces cognitive load and helps analysts focus on the task at hand.

**The Report Modal** appears as an overlay when viewing analysis results. Rather than cluttering the map interface with detailed statistics, the modal provides a comprehensive breakdown of tactical analysis including scores, cover breakdowns, flanking assessments, weak spot identification, and recommendations. Reports are automatically saved to history, allowing analysts to compare multiple approaches or revisit previous analyses.

2. **Sidebar** (left): Controls and settings
3. **Report Modal** (popup): Analysis results

### 4.2 Mode Selection

GeoRoute provides three distinct operational modes, each designed for a specific use case in the tactical planning workflow. Understanding when to use each mode is essential for effective system utilization.

**Route Mode** is the primary mode for new tactical planning when you need the AI to propose approach options. In this mode, you define the problem by placing friendly and enemy positions, and the AI generates multiple route options optimized for different tactical priorities. This mode is most valuable when you need quick options for unfamiliar terrain or want to compare AI-generated approaches against your own intuition.

**Draw Mode** serves experienced planners who have a specific route in mind and want AI validation and enhancement. Rather than generating routes, the system evaluates your proposed path, identifies potential improvements, and suggests tactical positions such as overwatch points and rally locations. This mode bridges human expertise with AI analysis, allowing planners to leverage their experience while benefiting from the AI's comprehensive terrain assessment.

**Simulate Mode** provides the deepest level of analysis by combining geometric modeling with AI vision analysis. This mode is specifically designed for scenarios where enemy positions and orientations are known or suspected. By modeling enemy fields of view and analyzing cover along your route, the simulation provides segment-by-segment assessment of exposure and concealment.

| Mode | Best Used When | Key Outputs |
|------|----------------|-------------|
| **Route** | Exploring options for an area; need AI-generated approaches | Multiple route options with scoring |
| **Draw** | Have a planned route; want validation and enhancement | Position suggestions, risk assessment |
| **Simulate** | Know enemy positions; need detailed exposure analysis | Cover analysis, flanking assessment, verdicts |

### 4.3 Route Mode (AI Generation)

Route Mode automates the initial tactical planning process by having the AI analyze satellite imagery and generate viable approach routes. This mode is particularly valuable when operating in unfamiliar terrain or when time constraints prevent detailed manual planning.

The workflow begins with defining the tactical situation. You place one or more friendly units to indicate the starting positions and one or more enemy units to indicate the objective area or threat locations. The AI uses these positions to understand the direction of approach and the areas to avoid or approach cautiously.

**Placing Units**: Click the "Place Soldier" button in the sidebar to enter placement mode, indicated by a crosshair cursor. Click on the map to position the soldier marker. The marker uses NATO APP-6 standard symbology, with a blue rounded rectangle representing friendly infantry. Repeat the process with "Place Enemy" to place red diamond-shaped hostile unit markers. Both marker types can be dragged to adjust their positions after placement.

The system enforces a minimum zoom level of 17 for unit placement. This requirement ensures that positions are specified with sufficient precision for meaningful tactical analysis. At zoom levels below 17, clicking the map displays a notification rather than placing a unit. This safeguard prevents accidentally placing units at incorrect locations due to insufficient map detail.

**Generating Routes**: Once units are placed, click "Plan Tactical Attack" to initiate AI route generation. The process typically takes 30 to 90 seconds, with a progress indicator showing the current stage. The system first fetches and stitches satellite imagery for the operational area, then sends this imagery to the Gemini AI with instructions to draw a tactical route. The AI analyzes the terrain and generates a single optimized route shown as a thin cyan line that follows streets and paths between buildings while avoiding obstacles.

**Understanding Results**: The generated route appears as an overlay on the satellite imagery. The route is drawn directly on the image by the AI, meaning it follows realistic paths around obstacles rather than simple geometric lines. The cyan line represents the recommended approach path from the friendly position to the target area.

The optional "Advanced Analytics" checkbox enables a secondary AI analysis that produces a detailed tactical report including recommended approach, optimal timing, equipment suggestions, and identified weaknesses. This additional analysis adds processing time but provides richer decision support.

### 4.4 Draw Mode (Route Evaluation)

Draw Mode recognizes that experienced tactical planners often have specific approaches in mind based on their training, doctrine, or situational knowledge that the AI cannot fully appreciate. Rather than replacing human judgment, this mode augments it by providing AI analysis of user-defined routes and suggesting enhancements based on terrain analysis.

**Drawing Your Route**: Switch to Draw mode using the mode tabs at the top of the sidebar. In this mode, clicking on the map adds waypoints that define your planned movement route. Waypoints appear as circular markers connected by a dashed blue line representing the path. The first waypoint appears green (start point) and the final waypoint appears blue (endpoint). You can adjust your route by dragging any waypoint to a new position; the connecting lines update automatically to reflect the change.

When drawing routes, consider placing waypoints at tactical decision points rather than at regular intervals. Key positions include corners where direction changes significantly, transitions between cover types, crossing points for open areas, and positions where you anticipate specific tactical actions. The AI will analyze the segments between these waypoints and provide relevant assessments.

**Configuring Your Squad**: The "Unit Composition" panel allows you to specify the composition of the unit that will execute this movement. While this information does not change the route itself, it enables the AI to provide more relevant position suggestions. A squad with snipers will receive different overwatch position recommendations than one without. A squad with a medic benefits from casualty collection point suggestions.

The composition settings include squad size (from 2 to 12), and allocation among riflemen (general-purpose infantry), snipers (long-range precision), support/MG (suppressive fire capability), and medics (casualty care). The sum of specialized roles does not need to equal squad size; the remainder is assumed to be additional riflemen.

**Evaluating the Route**: Clicking "Evaluate Route" sends your drawn route and squad composition to the AI for analysis. The AI examines the satellite imagery along your path and generates two categories of output: suggested positions and segment risk assessments.

Suggested positions are marked directly on an annotated version of the satellite image using distinct symbols. Green circles indicate cover positions where soldiers can take shelter during movement pauses. Yellow triangles mark potential overwatch or sniper positions with good sight lines. Orange squares identify rally points suitable for regrouping if the unit becomes separated. Red X marks highlight danger zones that require extra caution when traversing. White crosses with red outlines suggest medic station positions for casualty treatment.

The segment analysis provides a risk assessment for each portion of the route between waypoints, along with specific suggestions for safely traversing that segment. These suggestions might include recommendations to stay close to a particular structure, move quickly through an exposed area, or use smoke for concealment.

### 4.5 Simulate Mode (Tactical Simulation)

Simulate Mode provides the most sophisticated analysis capability in GeoRoute, combining geometric vision cone modeling with AI-based cover assessment. This mode is designed for scenarios where intelligence has provided information about enemy positions and orientations, allowing for detailed assessment of detection risk along a planned route.

The fundamental insight behind Simulate Mode is that geometric exposure does not equal actual exposure. A route segment might pass through the geometric cone of an enemy's field of view, but if a building stands between the enemy and the path, the segment is actually protected. Traditional planning tools that only calculate geometric intersection would flag this segment as exposed, leading to unnecessarily conservative route selection. By incorporating AI vision analysis of the satellite imagery, GeoRoute can distinguish between geometric exposure and actual exposure.

**Placing Enemy Units**: In Simulate Mode, enemy placement includes additional parameters beyond position. First, select the enemy type from the dropdown (Sniper, Rifleman, or Observer). Each type has different vision cone characteristics reflecting their observation capabilities. Then click on the map to place the enemy. A red circular marker appears at the clicked location, and a semi-transparent red cone extends from the marker showing the enemy's field of view.

The default facing direction is north (0°). To adjust this, click on the enemy marker to open its popup, then click "Rotate +45°" to rotate the facing direction clockwise in 45-degree increments. The vision cone rotates accordingly, allowing you to model the specific direction each enemy is watching. Getting facing directions correct is crucial for accurate simulation, as the analysis identifies flanking opportunities based on the relationship between your approach angle and enemy facing.

**Placing Friendly Units**: Optionally, you can place friendly units to represent your forces. While not required for the simulation, placing friendlies provides context in the annotated output and may influence AI recommendations. Select the friendly type (Rifleman, Sniper, or Medic) and click to place. Friendly units appear as blue rectangular markers using NATO symbology.

**Drawing the Movement Route**: With the tactical situation defined, draw your planned movement route by clicking waypoints on the map, just as in Draw Mode. The critical difference in Simulate Mode is that the route is immediately evaluated against the placed vision cones.

Before running the full AI analysis, the system provides preliminary geometric feedback by coloring route segments. Segments that pass through any enemy vision cone appear in amber, indicating they are in the "danger zone" and require analysis to determine if cover exists. Segments entirely outside all vision cones appear in green, indicating they are geometrically clear. This immediate visual feedback helps you understand the baseline exposure before committing to the more time-consuming AI analysis.

**Running the Simulation**: Clicking "Run Simulation" initiates the comprehensive analysis. The system captures the current satellite imagery with all markers and vision cones drawn, then sends this annotated image to the AI with detailed instructions for cover analysis. The AI examines each route segment and determines whether the geometric exposure translates to actual exposure or whether terrain features provide concealment.

After analysis, route segments are recolored based on actual cover status. Red indicates truly exposed segments where no cover blocks the line of sight. Amber indicates partial cover where some concealment exists but the segment is not fully protected. Green indicates fully covered segments where buildings, walls, or substantial terrain block the enemy's view entirely. Blue indicates segments outside all vision cones, confirmed clear.

**Interpreting the Report**: The simulation report provides multi-dimensional analysis. The overall verdict (EXCELLENT, GOOD, ACCEPTABLE, or RISKY) gives immediate assessment. The strategy rating (0-10) quantifies the approach quality. Tactical scores break down performance across stealth, safety, terrain usage, and flanking dimensions.

The flanking analysis deserves special attention. The system calculates the actual angle of approach relative to each enemy's facing direction. Approaches from directly in front (0° off facing) are highly detectable, while approaches from behind (180° off facing) exploit the enemy's blind spot. The report indicates whether your route achieves flanking advantage and the specific bonus points awarded.

The cover breakdown visualizes the proportion of your route that is exposed, partially covered, fully covered, or clear. This aggregate view helps assess overall approach viability at a glance.

Finally, the weak spots section identifies specific segments or positions that present the greatest risk, along with recommendations for mitigating these vulnerabilities. These recommendations might include using smoke grenades, timing movement when enemy attention is elsewhere, or modifying the route to add intermediate cover.

### 4.6 Report Modal

The report modal has two tabs:

#### Current Analysis Tab
Shows the most recent analysis with:
- **Header**: Verdict badge + rating + quick stats
- **Tactical Scores**: Radar chart showing stealth/safety/terrain/flanking
- **Cover Breakdown**: Visual bar showing covered/exposed segments
- **Flanking Analysis**: Approach angle indicator
- **Annotated Map**: AI-marked satellite image
- **Weak Spots**: Risk locations with recommendations
- **Strong Points**: Good terrain usage locations
- **Recommendations**: Tactical advice

#### History Tab
- All previous analyses saved automatically
- Click entry to load that analysis
- Clear button to remove history

### 4.7 Map Controls

| Action | Method |
|--------|--------|
| Pan | Drag the map |
| Zoom | Scroll wheel or +/- buttons |
| Place unit | Click in placement mode |
| Move unit | Drag the marker |
| Rotate enemy | Click marker → Rotate button |
| Remove waypoint | Right-click or sidebar controls |
| Layer switch | Layer control (top-right) |

---

## 5. System Architecture

Understanding the system architecture enables administrators to troubleshoot issues effectively, developers to extend functionality appropriately, and analysts to appreciate the computational processes underlying their tactical assessments. GeoRoute follows a modern microservices-inspired architecture where the frontend and backend operate as independent containerized services communicating through a well-defined API contract.

The architectural decisions reflect the system's priorities: real-time responsiveness for user interactions, scalability for concurrent analysts, and modularity for future enhancement. The separation of concerns between presentation, business logic, and external services allows each layer to evolve independently while maintaining stable interfaces.

### 5.1 High-Level Architecture

The following diagram illustrates the major components and their relationships. Data flows from user input through the React frontend, across HTTP and Server-Sent Events connections to the FastAPI backend, and out to external services including satellite imagery providers and AI models. The response path reverses this flow, with processed results propagating back to the user interface for visualization.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT BROWSER                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     React + TypeScript UI                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────┐  │ │
│  │  │ Sidebar  │  │TacticalMap│ │  Report   │  │ PlanningLoader │  │ │
│  │  │ Controls │  │ (Leaflet) │ │   Modal   │  │  (Progress)    │  │ │
│  │  └──────────┘  └──────────┘  └───────────┘  └────────────────┘  │ │
│  │                      │                                            │ │
│  │              ┌───────▼───────┐                                    │ │
│  │              │   Zustand     │  Global state management           │ │
│  │              │   Store       │                                    │ │
│  │              └───────────────┘                                    │ │
│  │                      │                                            │ │
│  │              ┌───────▼───────┐                                    │ │
│  │              │   useApi.ts   │  HTTP + SSE handling               │ │
│  │              └───────────────┘                                    │ │
│  └─────────────────────│────────────────────────────────────────────┘ │
└─────────────────────────│────────────────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼────────────────────────────────────────────┐
│                        FastAPI Backend                                 │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     API Layer (tactical.py)                       │  │
│  │  POST /api/plan-tactical-attack                                   │  │
│  │  POST /api/evaluate-route                                         │  │
│  │  POST /api/analyze-tactical-simulation                            │  │
│  │  GET  /api/progress/{request_id}  (SSE)                           │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │              BalancedTacticalPipeline                             │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 1: Acquire Imagery                                     │ │  │
│  │  │  - ESRI satellite tiles → stitched image                      │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 2: AI Processing                                       │ │  │
│  │  │  - Gemini 3 Pro Image: Draw routes                            │ │  │
│  │  │  - Gemini 3 Flash: Analyze cover/flanking                     │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 3: Score & Classify                                    │ │  │
│  │  │  - Multi-dimensional scoring                                  │ │  │
│  │  │  - Verdict determination                                      │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 4: Return Response                                     │ │  │
│  │  │  - Annotated image + analysis JSON                            │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
│   ESRI    │      │   Google    │     │   Google    │
│  World    │      │   Gemini    │     │    Maps     │
│  Imagery  │      │   3 Pro/    │     │  Elevation  │
│   Tiles   │      │   Flash     │     │    API      │
└───────────┘      └─────────────┘     └─────────────┘
```

The architecture diagram reveals several key design patterns. The React frontend maintains application state through Zustand, a lightweight state management library that provides predictable state updates without the boilerplate of larger alternatives. The frontend communicates with the backend through two channels: standard HTTP POST requests for initiating analyses, and Server-Sent Events (SSE) for receiving real-time progress updates during long-running operations.

The FastAPI backend serves as an orchestration layer, coordinating between multiple external services. When a request arrives, the backend validates inputs, fetches required imagery, invokes AI services, processes results, and assembles the response. This orchestration happens within the BalancedTacticalPipeline class, which provides a consistent workflow regardless of which specific operation (route generation, evaluation, or simulation) is being performed.

External service integration is handled through dedicated client classes, each encapsulating the specifics of a particular API. This abstraction allows the pipeline to work with different service implementations and simplifies testing through dependency injection.

### 5.2 Request Flow

The request flow diagram below traces a complete route generation operation from user click to displayed results. Understanding this flow helps troubleshoot latency issues and identify optimization opportunities. The flow is divided into frontend initiation, backend orchestration, external service calls, and response delivery.

#### Route Generation Flow

```
User clicks "Plan Tactical Attack"
         │
         ▼
┌────────────────────────┐
│ Frontend: useApi.ts    │
│ - POST /api/plan...    │
│ - Start SSE listener   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Backend: tactical.py   │
│ - Validate coordinates │
│ - Create request_id    │
│ - Start async pipeline │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 1:      │
│ - Calculate bounds     │
│ - Fetch ESRI tiles     │◄─── Progress: 5-20%
│ - Stitch into image    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 2:      │
│ - Add start/end markers│
│ - Call Gemini 3 Pro    │◄─── Progress: 25-70%
│ - Get annotated image  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 3:      │
│ - Route analysis       │
│ - Score calculation    │◄─── Progress: 75-85%
│ - Verdict assignment   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 4:      │
│ - Build response JSON  │
│ - Optional: advanced   │◄─── Progress: 90-100%
│   tactical report      │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Frontend:              │
│ - Receive response     │
│ - Update Zustand store │
│ - Overlay image on map │
│ - Populate report      │
└────────────────────────┘
```

Each stage of the pipeline emits progress updates through an SSE channel, allowing the frontend to display meaningful status information to users. The progress percentages are approximate and calibrated based on typical operation durations: imagery acquisition is usually quick (under 5 seconds), while AI processing can take 30 to 60 seconds depending on image complexity and API load. These progress updates help users understand that the system is actively working, reducing perceived latency.

The pipeline stages are designed to fail fast when possible. Coordinate validation occurs immediately, preventing wasted API calls for out-of-bounds requests. Imagery acquisition includes retry logic for transient network failures. AI processing includes timeout handling to prevent indefinite hangs. This defensive design ensures that failures are reported quickly rather than leaving users waiting.

### 5.3 Data Flow

The data flow diagram illustrates the transformation of data as it moves through the system. User input begins as simple coordinates and configuration, is validated and expanded, enriched through external service calls, and ultimately transformed into actionable tactical intelligence presented through the user interface.

```
                    ┌─────────────────────────────────┐
                    │        User Input                │
                    │  - Unit positions                │
                    │  - Route waypoints               │
                    │  - Squad composition             │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │      Request Validation          │
                    │  - Gulf region check             │
                    │  - Coordinate bounds             │
                    │  - Unit count validation         │
                    └───────────────┬─────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  ESRI Imagery   │     │   Gemini AI Models  │     │  Google Maps    │
│  - Tile fetch   │     │   - Image analysis  │     │  - Elevation    │
│  - Image stitch │     │   - Route drawing   │     │    data         │
└────────┬────────┘     │   - Cover analysis  │     └────────┬────────┘
         │              │   - Scoring         │              │
         │              └──────────┬──────────┘              │
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Response Assembly       │
                    │  - Annotated image (base64)  │
                    │  - Analysis JSON             │
                    │  - Scores & verdicts         │
                    │  - Recommendations           │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Frontend State          │
                    │  - Zustand store update      │
                    │  - Map overlay               │
                    │  - Report modal data         │
                    │  - History entry             │
                    └─────────────────────────────┘
```

A key insight from the data flow diagram is the fan-out and fan-in pattern. A single user request fans out to multiple external services (ESRI for imagery, Gemini for AI analysis, Google Maps for elevation), gathers their results, and fans back into a unified response. This pattern enables parallel service calls where possible, reducing total latency compared to sequential execution. However, it also means that the overall operation is only as reliable as the least reliable external service, which is why robust error handling and fallback strategies are essential.

The final response assembly phase merges data from multiple sources into a coherent package. The annotated satellite image (base64 encoded) provides visual context, while structured JSON data enables programmatic access to scores, coordinates, and recommendations. This dual-format response supports both human consumption through the report modal and potential integration with external systems.

---

## 6. API Reference

The GeoRoute API follows REST conventions with JSON request and response bodies. All endpoints are prefixed with `/api/` to distinguish them from potential future static file serving. The API is designed to be self-describing, with meaningful HTTP status codes, detailed error messages, and consistent response structures across all endpoints.

Authentication is not currently implemented at the application level; the assumption is that deployment environments will provide perimeter security through network configuration or reverse proxy authentication. For production deployments requiring user-level access control, an authentication middleware should be added at the FastAPI level.

All timestamps use ISO 8601 format in UTC timezone. Coordinates use the WGS84 datum (standard GPS coordinates). Distances are in meters, times in seconds or minutes as labeled, and angles in degrees with 0 representing north and increasing clockwise.

### 6.1 Health Check

The health check endpoint provides a simple mechanism for monitoring systems and load balancers to verify that the service is operational. It returns a minimal response without performing any complex operations, ensuring it responds quickly even when other services are under load.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-06T12:00:00Z"
}
```

### 6.2 Plan Tactical Attack

This is the primary endpoint for AI-powered route generation. When invoked, it triggers a multi-stage pipeline that fetches satellite imagery, invokes Gemini AI to draw tactical routes, analyzes the results, and returns a comprehensive response including route visualizations and tactical assessments. Due to the complexity of operations involved, this endpoint can take 30 to 90 seconds to complete; clients should use the progress streaming endpoint to provide user feedback during this time.

**Endpoint:** `POST /api/plan-tactical-attack`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "soldiers": [
    {
      "lat": 24.7136,
      "lon": 46.6753,
      "is_friendly": true,
      "unit_id": "optional-unit-id"
    }
  ],
  "enemies": [
    {
      "lat": 24.7146,
      "lon": 46.6763,
      "is_friendly": false,
      "unit_id": "optional-unit-id"
    }
  ],
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  },
  "zoom": 17,
  "no_go_zones": null,
  "analysis_depth": "full",
  "advanced_analytics": false
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | No | Client-provided ID for progress tracking |
| `soldiers` | array | Yes | List of friendly unit positions |
| `enemies` | array | Yes | List of enemy unit positions |
| `bounds` | object | Yes | Map bounds (north, south, east, west) |
| `zoom` | integer | No | Map zoom level (default: 14) |
| `no_go_zones` | array | No | Polygons to avoid (not implemented) |
| `analysis_depth` | string | No | "full" or "quick" |
| `advanced_analytics` | boolean | No | Enable detailed tactical report |

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "soldiers_count": 1,
  "enemies_count": 1,
  "no_go_zones_count": 0,
  "routes": [
    {
      "route_id": 1,
      "name": "Balanced Approach",
      "description": "ORANGE route - Uses cover while maintaining reasonable speed.",
      "waypoints": [...],
      "segments": [...],
      "classification": {
        "gemini_evaluation": "risk",
        "gemini_reasoning": "...",
        "scores": {
          "time_to_target": 75,
          "stealth_score": 60,
          "survival_probability": 80,
          "overall_score": 72
        },
        "simulation": {
          "detected": false,
          "detection_probability": 0.35,
          "detection_points": [],
          "safe_percentage": 65
        },
        "final_verdict": "risk",
        "final_reasoning": "...",
        "confidence": 0.7
      },
      "total_distance_m": 450.5,
      "estimated_duration_seconds": 300,
      "elevation_gain_m": 0,
      "elevation_loss_m": 0
    }
  ],
  "recommended_route_id": 2,
  "mission_assessment": "1 of 2 routes viable. Proceed with caution.",
  "key_risks": [],
  "recommendations": [...],
  "tactical_analysis_report": null,
  "detection_debug": {
    "gemini_route_image": "base64-image-data",
    "gemini_route_bounds": {
      "north": 24.716,
      "south": 24.712,
      "east": 46.678,
      "west": 46.674
    }
  }
}
```

### 6.3 Evaluate User Route

This endpoint evaluates a user-defined route rather than generating new routes. It is designed for experienced planners who have specific approach routes in mind and want AI-assisted validation and enhancement suggestions. The endpoint accepts a sequence of waypoints defining the route, along with optional squad composition information that influences position recommendations.

**Endpoint:** `POST /api/evaluate-route`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7138, "lng": 46.6756 },
    { "lat": 24.7140, "lng": 46.6758 }
  ],
  "units": {
    "squad_size": 8,
    "riflemen": 4,
    "snipers": 2,
    "support": 1,
    "medics": 1
  },
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "annotated_image": "base64-image-data",
  "annotated_image_bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  },
  "positions": [
    {
      "position_type": "overwatch",
      "lat": 24.7138,
      "lng": 46.6755,
      "description": "Rooftop corner with view of approach",
      "for_unit": "sniper",
      "icon": "crosshair"
    }
  ],
  "segment_analysis": [
    {
      "segment_index": 0,
      "start_lat": 24.7136,
      "start_lng": 46.6753,
      "end_lat": 24.7138,
      "end_lng": 46.6756,
      "risk_level": "low",
      "description": "Good cover along building wall",
      "suggestions": ["Stay close to structure", "Move in pairs"]
    }
  ],
  "overall_assessment": "Route uses available cover effectively...",
  "route_distance_m": 125.5,
  "estimated_time_minutes": 1.8
}
```

### 6.4 Analyze Tactical Simulation

The tactical simulation endpoint provides the most sophisticated analysis capability, combining geometric vision cone modeling with AI-based cover assessment. It requires detailed information about enemy positions including their types and facing directions, enabling the system to calculate fields of view and analyze whether terrain features provide concealment along the proposed route.

The response includes segment-by-segment cover analysis, flanking bonus calculations, multi-dimensional scores, and an overall verdict. This detailed breakdown enables analysts to understand exactly where and why exposure occurs, supporting informed decisions about route modification or acceptance.

**Endpoint:** `POST /api/analyze-tactical-simulation`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "enemies": [
    {
      "id": "enemy-1",
      "type": "sniper",
      "lat": 24.7146,
      "lng": 46.6763,
      "facing": 180
    },
    {
      "id": "enemy-2",
      "type": "rifleman",
      "lat": 24.7142,
      "lng": 46.6760,
      "facing": 270
    }
  ],
  "friendlies": [
    {
      "id": "friendly-1",
      "type": "rifleman",
      "lat": 24.7136,
      "lng": 46.6753
    }
  ],
  "route_waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7138, "lng": 46.6756 },
    { "lat": 24.7140, "lng": 46.6760 }
  ],
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "annotated_image": "base64-image-data",
  "annotated_image_bounds": {...},
  "strategy_rating": 7.5,
  "verdict": "GOOD",
  "tactical_scores": {
    "stealth": 80,
    "safety": 75,
    "terrain_usage": 85,
    "flanking": 90,
    "overall": 82
  },
  "flanking_analysis": {
    "is_flanking": true,
    "approach_angle": 135,
    "bonus_awarded": 2.0,
    "description": "Strong flank - approaching from 135° off enemy facing. In enemy blind spot."
  },
  "segment_cover_analysis": [
    {
      "segment_index": 0,
      "in_vision_cone": false,
      "cover_status": "clear",
      "cover_type": null,
      "exposure_percentage": 0,
      "blocking_feature": null,
      "enemy_id": null,
      "explanation": "Segment outside all enemy vision cones"
    },
    {
      "segment_index": 1,
      "in_vision_cone": true,
      "cover_status": "covered",
      "cover_type": "building",
      "exposure_percentage": 0,
      "blocking_feature": "2-story concrete building",
      "enemy_id": "sniper_1",
      "explanation": "In sniper cone but building blocks line-of-sight completely"
    }
  ],
  "cover_breakdown": {
    "total_segments": 2,
    "exposed_count": 0,
    "covered_count": 1,
    "partial_count": 0,
    "clear_count": 1,
    "overall_cover_percentage": 100,
    "cover_types_used": ["building"]
  },
  "weak_spots": [
    {
      "location": "Segment 2 midpoint",
      "description": "Brief exposure when rounding corner",
      "severity": "medium",
      "recommendation": "Move quickly through this section"
    }
  ],
  "strong_points": [
    {
      "location": "Segments 1-2",
      "description": "Excellent use of building cover",
      "benefit": "Completely hidden from sniper"
    }
  ],
  "exposure_analysis": [],
  "terrain_assessment": "Urban terrain with 80% of approach behind hard cover",
  "overall_assessment": "Good tactical approach exploiting enemy blind spots and urban cover.",
  "recommendations": [
    "Maintain current flanking approach angle",
    "Move quickly through exposed section"
  ],
  "route_distance_m": 125.5,
  "estimated_time_minutes": 1.8
}
```

### 6.5 Progress Streaming (SSE)

Long-running operations benefit from real-time progress feedback. The progress streaming endpoint uses Server-Sent Events (SSE), a standard HTTP mechanism for server-to-client push communication. When a client connects to this endpoint with a request ID obtained from one of the analysis endpoints, it receives a continuous stream of progress updates until the operation completes.

SSE was chosen over WebSockets for several reasons: it requires no special server configuration, works through standard HTTP infrastructure including proxies and load balancers, automatically reconnects after network interruptions, and is well-supported in modern browsers. The trade-off is that SSE is unidirectional (server to client only), which is perfectly suitable for progress reporting.

**Endpoint:** `GET /api/progress/{request_id}`

**Response:** Server-Sent Events stream

**Event Format:**
```
event: progress
data: {"stage": "imagery", "progress": 15, "message": "Downloading satellite tiles..."}

event: progress
data: {"stage": "routes", "progress": 50, "message": "AI generating tactical routes..."}

event: progress
data: {"stage": "complete", "progress": 100, "message": "Tactical plan ready!"}
```

**Stages:**
1. `imagery` (0-25%): Fetching satellite imagery
2. `routes` or `analysis` (25-90%): AI processing
3. `report` (90-98%): Building tactical report
4. `complete` (100%): Done
5. `error`: Error occurred

---

## 7. Data Models

Data models define the structure of information exchanged between system components. In GeoRoute, Pydantic models on the backend and TypeScript interfaces on the frontend ensure type safety and provide self-documenting data contracts. Understanding these models is essential for developers extending the system or integrating it with external tools.

The models are designed to be self-contained and serializable to JSON, enabling straightforward API communication. Optional fields use Python's Optional type or TypeScript's optional modifier, allowing graceful handling of incomplete data without runtime errors.

### 7.1 Unit Models

Unit models represent military entities placed on the map. The basic TacticalUnit model captures the essential properties common to all units, while specialized models like SimEnemyUnit add context-specific fields such as facing direction for enemies in simulation mode.

#### TacticalUnit (Backend)
```python
class TacticalUnit(BaseModel):
    lat: float          # Latitude position
    lon: float          # Longitude position
    is_friendly: bool   # True for friendly, False for enemy
    unit_id: str | None # Optional unique identifier
```

#### SimEnemyUnit (Backend)
```python
class SimEnemyUnit(BaseModel):
    id: str                                    # Unique identifier
    type: Literal["sniper", "rifleman", "observer"]
    lat: float
    lng: float
    facing: float  # 0-360 degrees, 0=North
```

### 7.2 Analysis Models

Analysis models capture the results of AI and geometric analysis. These models translate raw AI output into structured, queryable data that can be displayed in the user interface or processed programmatically. The models are designed to be comprehensive, capturing not just conclusions but also the reasoning and intermediate calculations that led to those conclusions.

#### SegmentCoverAnalysis

The SegmentCoverAnalysis model represents the AI's assessment of a single route segment's exposure status. It captures whether the segment falls within an enemy vision cone, what type of cover (if any) exists, and provides a human-readable explanation of the assessment. This granular data enables the frontend to color-code route segments and display tooltips with specific cover information.
```python
class SegmentCoverAnalysis(BaseModel):
    segment_index: int
    in_vision_cone: bool  # Geometrically in any enemy cone?
    cover_status: Literal["exposed", "covered", "partial", "clear"]
    cover_type: str | None  # "building", "vegetation", "terrain", "none"
    exposure_percentage: float  # 0-100
    blocking_feature: str | None  # What blocks LOS
    enemy_id: str | None  # Which enemy
    explanation: str  # Human-readable explanation
```

#### TacticalScores

The TacticalScores model quantifies route quality across four tactical dimensions. Each dimension is scored from 0 to 100, with higher values indicating better performance. The overall score is a weighted average of the individual dimensions, with weights calibrated based on typical tactical priorities. These scores enable direct comparison between route alternatives and provide a basis for the verdict classification.

```python
class TacticalScores(BaseModel):
    stealth: float       # 0-100: How hidden is the approach
    safety: float        # 0-100: Survival probability
    terrain_usage: float # 0-100: How well route uses cover
    flanking: float      # 0-100: Approach angle advantage
    overall: float       # 0-100: Weighted composite
```

#### FlankingAnalysis

Flanking represents a significant tactical advantage, allowing approach from an enemy's blind spot where detection probability is dramatically reduced. The FlankingAnalysis model captures whether the route achieves this advantage, the specific angle of approach relative to enemy facing direction, and the bonus points awarded to the overall rating. Approach angles greater than 90 degrees from enemy facing qualify as flanking, with rear approaches (around 180 degrees) earning the maximum bonus.

```python
class FlankingAnalysis(BaseModel):
    is_flanking: bool      # Approaching from enemy blind spot?
    approach_angle: float  # 0-360 degrees from enemy facing
    bonus_awarded: float   # 0-3 rating points bonus
    description: str       # Explanation
```

#### CoverBreakdown

The CoverBreakdown model aggregates individual segment analyses into a route-level summary. It counts segments by cover status, calculates the percentage of the route that is protected, and lists the types of cover utilized. This aggregate view is visualized in the report modal as a horizontal bar chart, giving analysts an immediate sense of overall route protection without examining each segment individually.

```python
class CoverBreakdown(BaseModel):
    total_segments: int
    exposed_count: int     # No cover, in cone
    covered_count: int     # Hard cover, in cone
    partial_count: int     # Partial cover
    clear_count: int       # Outside all cones
    overall_cover_percentage: float  # 0-100
    cover_types_used: list[str]
```

### 7.3 Response Models

See [API Reference](#6-api-reference) for complete response structures.

---

## 8. AI Prompts & Customization

The quality of GeoRoute's tactical analysis depends heavily on the prompts provided to the Gemini AI models. These prompts are essentially detailed instructions that tell the AI what to look for in satellite imagery, how to evaluate tactical situations, and what format to use for responses. Well-crafted prompts yield consistent, reliable results; poorly crafted prompts lead to unpredictable output that may not match backend expectations.

Prompts are intentionally externalized to the configuration file rather than hard-coded in source code. This design enables iterative improvement based on operational feedback without requiring code deployments. Administrators can observe how the AI responds to various scenarios, identify areas where instructions are unclear or incomplete, and refine the prompts accordingly. This feedback loop is essential for calibrating the system to specific operational contexts and terrain types.

### 8.1 Prompt Location

All AI prompts reside in the `georoute/config.yaml` file, which is read fresh for each API request. This means prompt changes take effect immediately without restarting the backend service. This hot-reload capability is invaluable during prompt development and tuning.

All AI prompts are in `georoute/config.yaml`:

| Prompt | Purpose |
|--------|---------|
| `route_prompt` | Instructions for Gemini to draw routes |
| `analysis_prompt` | Advanced tactical analysis |
| `route_evaluation_prompt` | User-drawn route analysis |
| `tactical_simulation_prompt` | Vision cone + cover analysis |

### 8.2 Route Drawing Prompt

The route drawing prompt is perhaps the most sophisticated prompt in the system. It instructs Gemini 3 Pro (an image-generation capable model) to analyze a satellite image with marked start and end positions, then draw tactical infantry movement routes directly on the image. This is a complex task requiring the AI to understand terrain features, identify obstacles, recognize cover opportunities, and generate smooth, realistic paths that a soldier could actually walk.

The prompt includes specific instructions about drawing style (smooth curves rather than straight lines), obstacle avoidance (never crossing through buildings), and route differentiation (balanced approach versus stealth approach). It also specifies the exact colors to use for each route type, ensuring visual consistency across analyses.

Controls how Gemini draws routes on satellite imagery:

```yaml
route_prompt: |
  Edit this satellite image. Draw exactly 2 infantry foot patrol routes...

  DRAWING RULES:
  - Draw smooth, curved lines that follow natural walking paths
  - NEVER cross through buildings - always go AROUND them
  - Follow roads, sidewalks, alleys, and open ground
  ...
```

**Key customizable elements:**
- Number of routes
- Line colors (ORANGE, GREEN)
- Drawing style (curved vs angular)
- Obstacle avoidance rules

### 8.3 Tactical Simulation Prompt

The tactical simulation prompt guides the AI through a complex multi-step analysis. First, it must understand the tactical scenario depicted in the annotated satellite image: where are the enemies, which direction are they facing (indicated by vision cones), and what is the proposed movement route. Then, for each segment of the route that passes through a vision cone, it must analyze whether terrain features (buildings, walls, vegetation) would actually block the enemy's line of sight.

This analysis requires spatial reasoning that combines geometric understanding with visual interpretation. The prompt provides explicit rules for how to evaluate cover: buildings completely block line of sight, vegetation provides partial concealment, and open ground offers no protection. It also includes the scoring rubric, specifying exactly how many points to deduct for exposed segments and how much bonus to award for flanking approaches.

The output format section of this prompt is critical. It specifies a JSON structure that the backend code expects to parse. Any deviation from this format can cause parsing failures, so modifications to the output format must be coordinated with corresponding backend code changes.

Controls cover analysis and scoring:

```yaml
tactical_simulation_prompt: |
  Analyze this tactical scenario satellite image...

  CRITICAL ANALYSIS RULES:
  1. Buildings BLOCK enemy vision - routes BEHIND buildings are SAFE
  2. Trees/vegetation provide PARTIAL cover (50% concealment)
  3. Only mark as EXPOSED if in cone AND no obstacles blocking line-of-sight
  4. Approaching from enemy's BACK (>90° from facing) = FLANKING BONUS

  STRICT SCORING RULES:
  AUTOMATIC DEDUCTIONS:
  - ANY exposed segment in sniper cone: -2.0 points
  - ANY exposed segment in rifleman cone: -1.5 points
  ...
```

**Key customizable elements:**
- Cover detection rules
- Scoring deductions and bonuses
- Verdict thresholds
- JSON output format

### 8.4 Modifying Prompts

Prompt modification is a powerful customization mechanism but requires careful attention to maintain system reliability. The AI interprets prompts probabilistically rather than deterministically, meaning small wording changes can have significant effects on output consistency. Testing is essential after any prompt modification.

The recommended workflow for prompt modification is:

1. Edit `georoute/config.yaml` with your proposed changes
2. Save the file (changes take effect on next API call without restart)
3. Run several test analyses with known scenarios
4. Compare AI output to expected results
5. Iterate until output is satisfactory
6. Monitor backend logs with `docker compose logs -f georoute-backend` for parsing errors

**Critical considerations when modifying prompts:**
- The JSON output format must remain consistent with backend Pydantic models. Changing field names, types, or structure in the prompt without corresponding backend changes will cause parsing failures.
- Scoring deductions and bonuses directly affect verdict classification. Test with edge cases to ensure the scoring scale produces expected verdicts.
- Preserve all required fields in JSON output. Missing fields may cause runtime errors or incorrect default values.
- Be specific and unambiguous. AI models perform best with concrete instructions rather than vague guidance.
- Include examples when introducing new concepts. The AI generalizes from examples effectively.

---

## 9. Frontend Architecture

The GeoRoute frontend is built with React and TypeScript, providing a type-safe, component-based architecture that facilitates maintenance and extension. The user interface prioritizes the map as the central workspace while providing contextual controls and comprehensive reporting capabilities.

React was chosen for its component model, which maps naturally to the distinct UI regions (sidebar, map, modals) and enables reuse of common elements. TypeScript adds compile-time type checking that catches many common programming errors before runtime, particularly valuable when working with the complex data structures returned by the API.

The frontend uses Vite as its build tool, providing fast hot module replacement during development and optimized bundles for production. Tailwind CSS handles styling through utility classes, eliminating the need for custom CSS and ensuring visual consistency throughout the application.

### 9.1 Component Hierarchy

The component hierarchy reflects the visual layout of the application. The top-level Index component orchestrates the major regions, passing state and callbacks to child components through props. Most components are purely presentational, receiving data from the centralized Zustand store and rendering it appropriately.

```
App.tsx
└── Index.tsx (Main page)
    ├── Sidebar.tsx
    │   ├── UnitPlacement.tsx
    │   ├── ActionButtons.tsx
    │   ├── SimulationControls.tsx
    │   ├── RouteDrawingControls.tsx
    │   ├── UnitCompositionPanel.tsx
    │   ├── TacticalRouteResults.tsx
    │   ├── EvaluationResults.tsx
    │   └── SimulationResults.tsx
    ├── TacticalMap.tsx
    │   └── ZoomIndicator.tsx
    ├── TacticalReportModal.tsx
    └── PlanningLoader.tsx
```

### 9.2 State Management (Zustand)

Zustand provides global state management with a minimal API that avoids the boilerplate associated with Redux while maintaining predictable state updates. The store is defined as a single hook (`useMission`) that components call to access and modify state.

The state structure is organized into logical groups: current operational mode, unit positions for route mode, simulation entities and results, analysis history, and UI state such as loading indicators and modal visibility. Actions (functions that modify state) are co-located with the state they affect, making it easy to understand what operations are available.

A key design decision is storing analysis results in history arrays rather than overwriting a single "current result" value. This enables the history tab functionality in the report modal, allowing analysts to compare multiple analyses without losing previous work. History entries include timestamps for chronological ordering.

Global state is managed in `useMission.ts`:

```typescript
interface MissionState {
  // Mode
  mapMode: MapMode;  // 'idle' | 'place-soldier' | 'place-enemy' | 'draw-route' | ...

  // Units (Route mode)
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];

  // Routes
  tacticalRoutes: TacticalRoute[];
  planImages: Record<number, { image: string; bounds: Bounds }>;

  // Simulation state
  simEnemies: SimEnemy[];
  simFriendlies: SimFriendly[];
  drawnWaypoints: DrawnWaypoint[];
  simulationResult: TacticalSimulationResult | null;

  // History
  simulationHistory: SimulationHistoryEntry[];
  tacticalReportHistory: TacticalReportEntry[];

  // UI state
  isPlanning: boolean;
  reportModalOpen: boolean;

  // Actions
  addSoldier: (unit) => void;
  addSimEnemy: (lat, lng) => void;
  setSimulationResult: (result) => void;
  // ... many more
}
```

### 9.3 API Layer (useApi.ts)

The API layer abstracts HTTP communication with the backend, providing consistent error handling and progress tracking. All API calls flow through utility functions that handle JSON serialization, error extraction, and response parsing. This centralization ensures that error handling logic is consistent throughout the application and simplifies adding new API calls.

The error handling logic specifically extracts the `detail` field from error responses, which is where FastAPI places structured error messages. This allows the backend to provide meaningful, user-friendly error messages that the frontend displays without modification. For example, when rate limits are exceeded, the backend returns a clear message about waiting and retrying, which the frontend presents directly to the user.

HTTP and SSE handling:

```typescript
// POST with error handling
async function fetchWithError(url: string, options: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || error.message || `Request failed`);
  }
  return response;
}

// SSE progress streaming
function subscribeToProgress(requestId: string, onProgress: Function) {
  const eventSource = new EventSource(`${API_URL}/api/progress/${requestId}`);
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onProgress(data);
  };
  return () => eventSource.close();
}
```

### 9.4 Map Layer (TacticalMap.tsx)

The TacticalMap component integrates the Leaflet mapping library with React, managing the complex lifecycle of map initialization, layer management, and event handling. Leaflet operates outside React's virtual DOM, requiring careful coordination to prevent conflicts and ensure proper cleanup.

The map uses a layered architecture where different types of content occupy separate layers that can be independently added, removed, and updated. Base tiles come from ESRI World Imagery. Unit markers are rendered as custom Leaflet markers with NATO symbology. Vision cones are drawn as polygon overlays. User-drawn routes appear as polylines. AI-generated route images are positioned as image overlays with precise geographic bounds.

This layered approach enables complex visualizations while maintaining performance. Each layer can be updated independently without affecting others, and layers can be toggled on/off for different viewing needs.

Leaflet integration with layers:

| Layer | Purpose |
|-------|---------|
| `tileLayers.satellite` | ESRI World Imagery base |
| `unitMarkers` | Soldier/enemy markers |
| `simEnemyMarkers` | Simulation enemy markers |
| `simEnemyVisionCones` | Red vision cone polygons |
| `drawnRoutePolyline` | User-drawn route line |
| `planOverlays` | Gemini-generated route images |

---

## 10. Backend Architecture

The GeoRoute backend is built with FastAPI, a modern Python web framework that provides automatic API documentation, request validation through Pydantic models, and native support for asynchronous operations. The backend is designed as an orchestration layer that coordinates between external services (ESRI imagery, Google Gemini AI, Google Maps elevation) to fulfill tactical analysis requests.

The codebase follows a modular architecture where each concern is handled by a dedicated module. API endpoints are thin handlers that validate input, delegate to processing logic, and format responses. Processing logic resides in pipeline classes that orchestrate multi-step operations. External service interactions are encapsulated in client classes that abstract away API specifics. This separation enables unit testing at each layer and simplifies swapping implementations.

Asynchronous programming is used throughout, allowing the server to handle multiple concurrent requests without blocking. This is particularly important given the long latency of AI model calls, which can take 30 seconds or more. While one request waits for Gemini to respond, the server can process other requests, maximizing throughput.

### 10.1 Module Structure

The module structure organizes code by functional area. The `api/` directory contains HTTP endpoint handlers. The `clients/` directory contains classes that interact with external services. The `models/` directory contains Pydantic data models used for validation and serialization. The `processing/` directory contains the business logic for tactical analysis. The `utils/` directory contains helper functions used across modules.

```
georoute/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration loading
├── config.yaml             # All settings and prompts
├── api/
│   ├── routes.py           # Health check
│   └── tactical.py         # Main API endpoints
├── clients/
│   ├── esri_imagery.py     # Satellite tile fetching
│   ├── gemini_tactical.py  # Gemini AI client
│   └── google_maps.py      # Elevation API client
├── models/
│   └── tactical.py         # Pydantic data models
├── processing/
│   ├── balanced_tactical_pipeline.py      # Main orchestration
│   └── gemini_image_route_generator.py    # Route/analysis AI
└── utils/
    └── geo_validator.py    # Gulf region validation
```

### 10.2 Pipeline Classes

Pipeline classes implement the multi-step workflows required for tactical analysis. They coordinate between imagery acquisition, AI processing, result parsing, and response assembly. The pipeline pattern provides a consistent structure for these operations while allowing each step to be independently implemented and tested.

#### BalancedTacticalPipeline

The BalancedTacticalPipeline class is the primary orchestration component. It is instantiated with configuration and client dependencies, then exposes methods for each type of analysis. The "balanced" name reflects its design philosophy of balancing AI analysis with geometric computation, using each approach where it is most effective.

Main orchestration class:

```python
class BalancedTacticalPipeline:
    def __init__(self, config):
        self.gmaps = GoogleMapsClient(config.google_maps_api_key)
        self.esri = ESRIImageryClient()
        self.gemini = TacticalGeminiClient(...)
        self.route_generator = GeminiImageRouteGenerator(...)

    async def plan_tactical_attack(self, request) -> TacticalPlanResponse:
        # 1. Validate coordinates
        # 2. Fetch satellite imagery
        # 3. Generate routes with Gemini
        # 4. Analyze and score
        # 5. Return response

    async def evaluate_user_route(self, request) -> RouteEvaluationResponse:
        # Similar flow for user-drawn routes

    async def analyze_tactical_simulation(self, request) -> TacticalSimulationResponse:
        # Draw vision cones, analyze cover, calculate flanking
```

#### GeminiImageRouteGenerator

The GeminiImageRouteGenerator class encapsulates all interactions with Google's Gemini AI models. It handles both AI Studio and Vertex AI authentication paths, manages model selection from configuration, and provides methods for different types of AI operations (route drawing, tactical analysis, route evaluation).

A key responsibility of this class is parsing AI responses. Gemini returns results as text that typically contains JSON embedded within markdown code blocks. The class extracts and validates this JSON, handling common variations in AI output format. When parsing fails, detailed error information is logged to facilitate debugging.

Gemini AI interaction:

```python
class GeminiImageRouteGenerator:
    def __init__(self, api_key, use_vertex, project_id, location):
        # Initialize Gemini client (AI Studio or Vertex)

    async def generate_route(self, satellite_image_base64, ...) -> RouteResult:
        # Add markers, call Gemini 3 Pro Image, parse result

    async def analyze_tactical_simulation(self, annotated_image, prompt) -> dict:
        # Call Gemini 3 Flash for vision analysis
```

### 10.3 Error Handling

Error handling in GeoRoute serves two purposes: providing useful feedback to users and protecting internal system details from exposure. The error sanitization function translates technical exceptions (which may contain API keys, internal paths, or implementation details) into user-friendly messages with appropriate HTTP status codes.

The sanitization logic examines exception messages for known patterns and maps them to appropriate responses. Rate limit errors (HTTP 429) tell users to wait and retry. Authentication failures (HTTP 401) indicate API key issues without revealing which key or service failed. Model availability errors (HTTP 503) suggest temporary unavailability without exposing model names. Unrecognized errors receive a generic message with HTTP 500, logged with full details for administrator review.

This approach balances transparency with security. Users receive actionable information about what went wrong and what they can do, while system internals remain protected. Backend logs retain full error details for debugging.

Errors are sanitized in `tactical.py`:

```python
def _sanitize_error(e: Exception) -> tuple[str, int]:
    """Convert exceptions to user-friendly messages with proper HTTP codes."""
    error_str = str(e).lower()

    if "resource_exhausted" in error_str or "quota" in error_str:
        return "AI service rate limit exceeded. Please wait and try again.", 429

    if "permission_denied" in error_str or "api key" in error_str:
        return "AI service authentication failed. Check API key.", 401

    if "model" in error_str and "not found" in error_str:
        return "AI model temporarily unavailable.", 503

    # ... more cases

    return "An error occurred during analysis.", 500
```

---

## 10.5 NGINX Reverse Proxy

Version 2.0 introduces NGINX as the default entry point for all traffic. This production-grade reverse proxy provides several critical capabilities that improve security, performance, and scalability.

### Why NGINX?

Direct exposure of application services to the internet introduces unnecessary risk. NGINX serves as a protective layer that:

- **Terminates external connections** before they reach application code
- **Enforces rate limits** to prevent abuse and denial-of-service attempts
- **Compresses responses** to reduce bandwidth usage
- **Adds security headers** to protect against common web vulnerabilities
- **Load balances** across multiple backend instances

### Configuration

The NGINX configuration resides in `nginx/nginx.conf`. Key settings include:

**Rate Limiting:**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```
API endpoints are limited to 10 requests per second per IP address, with a burst allowance of 20 requests. This prevents individual users from overwhelming the AI processing pipeline.

**Load Balancing:**
```nginx
upstream backend {
    least_conn;  # Send to least busy server
    server georoute-backend:9001;
    keepalive 32;
}
```
When multiple backend replicas are running, NGINX distributes requests using the least-connections algorithm, ensuring even load distribution.

**AI Operation Timeouts:**
```nginx
proxy_read_timeout 180s;
proxy_connect_timeout 60s;
```
AI operations can take up to 3 minutes. Standard timeout values would terminate these requests prematurely.

**SSE Support:**
```nginx
proxy_buffering off;
proxy_cache off;
chunked_transfer_encoding on;
```
Server-Sent Events require special handling to maintain persistent connections for progress streaming.

### Scaling Backend Replicas

To handle more concurrent users, scale the backend service:

```bash
# Scale to 3 replicas
docker compose up -d --scale georoute-backend=3

# Scale back to 1
docker compose up -d --scale georoute-backend=1
```

NGINX automatically discovers new replicas through Docker's DNS resolution and distributes load accordingly.

**When to scale:**
- Multiple analysts working simultaneously
- AI operations causing request queuing
- Response times increasing under load

**Scaling limits:**
- Gemini API rate limits remain the true bottleneck (~60 req/min)
- Each replica consumes ~500MB RAM
- More than 5 replicas rarely provides benefit

---

## 11. Troubleshooting

This section provides guidance for diagnosing and resolving common issues that may arise during GeoRoute operation. Problems generally fall into three categories: configuration issues (incorrect API keys, environment variables), external service issues (rate limits, service unavailability), and user operation issues (operating outside restrictions, insufficient zoom).

The troubleshooting approach follows a standard methodology: identify symptoms, check relevant logs, isolate the cause, and apply the appropriate fix. For each common issue listed below, we provide the typical symptoms, likely causes, and recommended solutions.

### 11.1 Common Issues

The issues below are presented in order of likelihood based on typical deployment experience. Most problems stem from API key configuration or rate limit exhaustion rather than system defects.

#### "Outside Gulf Region" Error
**Cause:** Coordinates are outside the GCC bounding box.
**Solution:** Ensure all coordinates are within:
- Latitude: 12°N to 32°N
- Longitude: 34°E to 60°E

#### "Zoom In Required" Popup
**Cause:** Map zoom level is below 17.
**Solution:** Zoom in to level 17 or higher before placing units.

#### No Routes Generated
**Causes:**
1. Invalid Gemini API key
2. Rate limit exceeded
3. Model unavailable

**Solutions:**
1. Check API key in `.env`
2. Wait 1-2 minutes and retry
3. Check `docker compose logs georoute-backend`

#### Blank/Missing Satellite Imagery
**Causes:**
1. ESRI service unavailable
2. Network timeout

**Solutions:**
1. Check internet connection
2. Retry after a few seconds
3. ESRI is generally very reliable

#### Container Won't Start
**Solutions:**
```bash
# Check logs
docker compose logs

# Rebuild from scratch
docker compose down
docker compose up --build
```

#### Port Already in Use
**Solution:** Change ports in `.env`:
```bash
BACKEND_PORT=8002
UI_PORT=8081
```

### 11.2 Log Analysis

Container logs are the primary diagnostic resource for backend issues. The Docker Compose setup directs container output to standard Docker logging, accessible through the `docker compose logs` command. Backend logs include HTTP request information, pipeline stage progress, external API call results, and any errors encountered during processing.

When troubleshooting, examine logs from the time period surrounding the reported issue. Look for error messages, stack traces, or warnings that indicate what went wrong. The `-f` flag enables following logs in real-time, useful when reproducing issues.

```bash
# View all logs
docker compose logs -f

# Backend only
docker compose logs -f georoute-backend

# Frontend only
docker compose logs -f georoute-ui

# Search for errors
docker compose logs | grep -i error
```

### 11.3 Health Checks

Health checks verify that services are operational and responding correctly. The backend provides a dedicated health endpoint that returns a simple success response if the service is functioning. Docker Compose uses this endpoint for its health check configuration, ensuring that dependent services (like the frontend) only start after the backend is ready.

For deeper diagnostics, checking container status reveals whether containers are running, restarting, or failed. Resource usage statistics help identify if containers are experiencing memory pressure or CPU saturation that might cause performance degradation.

```bash
# Check backend health
curl http://localhost:8001/api/health

# Check container status
docker compose ps

# Check resource usage
docker stats
```

---

## 12. Extending the System

GeoRoute is designed with extensibility in mind. The modular architecture, externalized configuration, and clear separation between layers facilitate adding new capabilities without disrupting existing functionality. This section provides guidance for common extension scenarios, illustrating the patterns and touch points involved.

When extending the system, follow these principles: make changes incrementally and test at each step, maintain backward compatibility where possible, coordinate frontend and backend changes for new data structures, and document new features in this manual.

### 12.1 Adding New Enemy Types

The enemy type system is designed to be extensible. Each enemy type has associated vision specifications (range and cone angle) that determine how vision cones are calculated and displayed. Adding a new enemy type requires updates in three locations: the backend enum and vision specs, and the frontend vision specs. The process is straightforward and does not require changes to core analysis logic.

1. **Backend** (`models/tactical.py`):
```python
class SimEnemyType(str, Enum):
    SNIPER = "sniper"
    RIFLEMAN = "rifleman"
    OBSERVER = "observer"
    MACHINEGUNNER = "machinegunner"  # Add new type
```

2. **Backend** (`balanced_tactical_pipeline.py`):
```python
vision_specs = {
    'sniper': {'distance': 500, 'angle': 30},
    'rifleman': {'distance': 100, 'angle': 60},
    'observer': {'distance': 400, 'angle': 45},
    'machinegunner': {'distance': 300, 'angle': 90},  # Add specs
}
```

3. **Frontend** (`useMission.ts`):
```typescript
export const ENEMY_VISION_SPECS = {
  sniper: { distance: 500, angle: 30, color: '#ef4444' },
  rifleman: { distance: 100, angle: 60, color: '#ef4444' },
  observer: { distance: 400, angle: 45, color: '#ef4444' },
  machinegunner: { distance: 300, angle: 90, color: '#ef4444' },  // Add
};
```

4. **Frontend** (`TacticalMap.tsx`):
Add icon to `createSimEnemyIcon` function.

### 12.2 Adding New Scoring Metrics

The scoring system can be extended with additional metrics to capture tactical dimensions not covered by the default set. For example, you might add a "speed" metric for time-critical missions or a "coordination" metric for multi-unit operations. Adding a metric requires model updates, prompt modifications to instruct the AI to calculate the metric, and frontend updates to display it.

Note that adding metrics also requires adjusting the overall score calculation and potentially the verdict thresholds. Consider how the new metric interacts with existing metrics and whether weights should be rebalanced.

1. **Backend** (`models/tactical.py`):
```python
class TacticalScores(BaseModel):
    stealth: float
    safety: float
    terrain_usage: float
    flanking: float
    speed: float  # Add new metric
    overall: float
```

2. **Backend** (`config.yaml`):
Update `tactical_simulation_prompt` to include new metric in JSON output.

3. **Frontend** (`useMission.ts`):
Update `TacticalScores` interface.

4. **Frontend** (`TacticalReportModal.tsx`):
Update `RadarChart` and `MiniGauge` components.

### 12.3 Adding New Analysis Modes

New analysis modes enable entirely new types of tactical assessment. For example, you might add a "defensive position evaluation" mode for assessing fortification locations, or a "convoy route planning" mode optimized for vehicle movement. Adding a mode is the most substantial extension, requiring new endpoints, processing logic, data models, and UI components.

The existing modes provide templates for implementation. Follow their patterns for request validation, progress reporting, and response formatting to maintain consistency. Consider how the new mode relates to existing modes and whether it should share UI space (as route and draw modes do in the sidebar) or require new interface elements.

1. Create new endpoint in `tactical.py`
2. Add pipeline method in `balanced_tactical_pipeline.py`
3. Add request/response models in `models/tactical.py`
4. Create frontend components
5. Add state management in `useMission.ts`
6. Connect to sidebar controls

### 12.4 Changing AI Models

Model selection is configuration-driven, allowing you to switch between different Gemini models without code changes. This flexibility is valuable as Google releases new models with improved capabilities. The image model must support image generation (drawing on images), the text model handles structured analysis, and the analysis model performs vision-based tactical assessment.

When switching models, be aware that different models may have different capabilities, latencies, and costs. Test thoroughly after any model change, as prompt effectiveness can vary between models. Some prompts that work well with one model may need adjustment for another.

Edit `georoute/config.yaml`:
```yaml
gemini:
  image_model: "gemini-3-pro-image-preview"  # For drawing
  text_model: "gemini-2.5-flash"             # For text
  analysis_model: "gemini-3-flash-preview"   # For vision
```

No code changes required - models are loaded from config.

---

## Appendix A: Glossary

This glossary defines technical and tactical terms used throughout the manual. Understanding these terms ensures clear communication and accurate interpretation of system outputs.

| Term | Definition |
|------|------------|
| **Cover** | Physical obstruction that blocks line of sight |
| **Concealment** | Visual obstruction that hides but doesn't block fire |
| **Vision Cone** | Triangle representing enemy field of view |
| **Flanking** | Approaching from enemy's blind spot (>90° from facing) |
| **LOS** | Line of Sight |
| **SSE** | Server-Sent Events (real-time progress streaming) |
| **GCC** | Gulf Cooperation Council (regional restriction) |

## Appendix B: Keyboard Shortcuts

The current version of GeoRoute relies on mouse-based interactions through the map interface. Keyboard shortcuts have not been implemented in this release but may be added in future versions based on user feedback and operational requirements. Priority shortcut candidates include mode switching, unit type selection, and report navigation.

## Appendix C: Version History

This section documents significant releases and their major changes. Minor updates and bug fixes may not be listed individually but are captured in the git commit history.

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Feb 2026 | Production infrastructure: NGINX reverse proxy with rate limiting and load balancing, Vertex AI as recommended backend, unified docker-compose.yml, backend scaling support, security headers, SSE proxy support, error sanitization. |
| 1.0 | Feb 2026 | Initial release with AI-powered route generation, user route evaluation, and tactical simulation with vision cone modeling. |

---

## Closing Notes

GeoRoute represents the application of cutting-edge AI technology to the longstanding challenge of tactical route planning. While the system provides powerful analytical capabilities, it is designed to augment rather than replace human judgment. The verdicts, scores, and recommendations should be considered as inputs to decision-making, not as directives.

Feedback from operational use is essential for continued improvement. As you work with the system, note any scenarios where the analysis seems inconsistent or where additional capabilities would be valuable. This feedback informs prompt refinement, feature prioritization, and overall system evolution.

*This manual is maintained alongside the GeoRoute codebase. For questions, issues, or contributions, see the project repository.*
