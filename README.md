# 🌦️ Weather-Aware Truck Routing

A full-stack web application that helps truck drivers choose the safest route between two locations by analyzing weather conditions along the route, factoring in cargo weight and estimated arrival times at each checkpoint.

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Risk Classification](#risk-classification)
- [Route Recommendation Logic](#route-recommendation-logic)
- [Testing](#testing)
- [Deployment](#deployment)
- [Assumptions & Design Decisions](#assumptions--design-decisions)
- [Project Structure](#project-structure)

---

## ✨ Features

- **Alternative Routes** — Uses OpenRouteService to generate driving alternatives, with automatic transparent OSRM fallback (zero-config, works immediately without an API key)
- **Weather-Based Risk Assessment** — Fetches hourly weather forecasts (wind, rain, snow) at each checkpoint using Open-Meteo
- **Checkpoint Sampling** — Places weather checkpoints at configurable intervals (10/25/50 miles) along the actual route geometry using Haversine interpolation
- **Arrival-Time Weather** — Evaluates weather at each checkpoint's estimated arrival time, not departure time
- **Cargo Weight Overrides** — Adjusts wind risk thresholds for heavy loads (>30,000 lb and >40,000 lb)
- **Risk-Mile Calculation** — Assigns each segment a risk level and calculates distance-weighted statistics
- **Lexicographic Recommendation** — Ranks routes by: Severe miles → High miles → Avg risk → Duration
- **Interactive Map** — Leaflet map with clean Esri Dark Canvas tiles (no watermarks), color-coded route polylines, and risk-colored checkpoint markers with weather popups
- **0-48h Forecast Slider** — Separate timeline to visualize weather conditions at any future hour with a heatmap per route
- **Checkpoint Weather Details Table** — Expandable table detailing mile marker, ETA, temperature, wind speed, rain rate, snow rate, and risk badge for every checkpoint
- **Quick Route Presets** — One-click chips for Chicago → Detroit, Denver → Kansas City, and Dallas → Atlanta
- **Responsive UI** — Glassmorphism dark theme, optimized for desktop and mobile

---

## 🛠️ Tech Stack

| Layer      | Technology                                                                 |
|------------|---------------------------------------------------------------------------|
| Backend    | Python 3.9+, Django 4.2, Django REST Framework                           |
| Frontend   | React 19, Vite, Tailwind CSS                                             |
| Maps       | Leaflet + react-leaflet, Esri World Dark Gray Canvas                      |
| Routing    | OpenRouteService API (with automatic OSRM fallback)                       |
| Weather    | Open-Meteo API (no key required)                                         |
| Geocoding  | Nominatim / OpenStreetMap (no key required)                              |
| Testing    | Django TestCase (101 unit tests, 100% pass rate)                         |

---

## 🏗️ Architecture

```
┌──────────────┐    ┌──────────────────────────────────────────┐
│   React UI   │───▶│  Django REST API                         │
│  (Vite dev)  │    │  ┌─────────────────────────────────┐     │
│              │    │  │ Services Layer                   │     │
│  - TripForm  │    │  │  ├─ geocoding.py (Nominatim)    │     │
│  - RouteMap  │    │  │  ├─ routing.py (ORS)            │     │
│  - RouteCard │    │  │  ├─ checkpoint.py (Haversine)   │     │
│  - Forecast  │    │  │  ├─ weather.py (Open-Meteo)     │     │
│    Slider    │    │  │  ├─ risk.py (Thresholds)        │     │
│              │    │  │  └─ recommendation.py (Ranking) │     │
└──────────────┘    │  └─────────────────────────────────┘     │
                    └──────────────────────────────────────────┘
```

**Data flow for trip analysis:**
1. User submits origin, destination, departure time, load weight, and sampling interval
2. Backend geocodes addresses (if needed) and requests 3 alternative routes from ORS
3. For each route, checkpoints are generated at the configured interval along the decoded polyline geometry
4. Weather is fetched for each checkpoint at its estimated arrival time (ETA)
5. Risk is classified per checkpoint using exact thresholds + cargo weight overrides
6. Risk-miles are aggregated and the recommended route is selected via lexicographic ranking

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- An [OpenRouteService API key](https://openrouteservice.org/dev/#/signup) *(Optional — if omitted, the app automatically uses the free public OSRM routing engine with zero configuration needed)*

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional ORS key)
cp .env.example .env

# Run database migrations
python manage.py migrate

# Run all 101 unit tests
python manage.py test routing.tests

# Start development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server (proxies /api to Django on port 8000)
npm run dev
```

The frontend dev server runs at `http://localhost:5173` and proxies all `/api/*` requests to the Django backend at `http://127.0.0.1:8000`.

---

## 📡 API Documentation

### `GET /api/health/`
Health check endpoint.

**Response:**
```json
{ "status": "healthy", "service": "Weather-Aware Truck Routing API", "version": "1.0.0" }
```

### `GET /api/geocode/?q=Chicago`
Geocode an address to coordinates.

**Response:**
```json
{
  "results": [
    { "display_name": "Chicago, Cook County, Illinois, US", "lat": "41.8781", "lon": "-87.6298" }
  ]
}
```

### `POST /api/trips/analyze/`
Full trip analysis — routes, weather, risk, recommendation.

**Request:**
```json
{
  "origin": { "lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL" },
  "destination": { "lat": 39.7392, "lon": -104.9903, "name": "Denver, CO" },
  "departure_time": "2026-10-15T08:00:00Z",
  "load_weight_lb": 45000,
  "sampling_interval_miles": 25
}
```

**Response:**
```json
{
  "trip": { "origin": {...}, "destination": {...}, ... },
  "routes": [
    {
      "route_id": "route_0",
      "name": "Route 1",
      "distance_miles": 1004.3,
      "duration_s": 54000,
      "duration_display": "15h 0m",
      "eta": "2026-10-15T23:00:00Z",
      "geometry": [[lat, lon], ...],
      "checkpoints": [...],
      "risk_stats": {
        "risk_miles": { "low": 800.0, "moderate": 150.0, "high": 50.0, "severe": 4.3, "no_travel": 0.0, "unknown": 0.0 },
        "total_distance_miles": 1004.3,
        "average_risk": 1.35,
        "is_eligible": true,
        "has_no_travel": false,
        "num_checkpoints": 41,
        "warnings": []
      }
    }
  ],
  "recommendation": {
    "recommended_route_id": "route_0",
    "explanation": "Route 1 is recommended because it has the fewest Severe-risk miles (4.3 mi).",
    "route_rankings": [...]
  },
  "warnings": [],
  "metadata": { "num_routes": 3, "analysis_timestamp": "..." }
}
```

### `POST /api/trips/forecast/`
Get weather forecast for a specific future hour (0-48h). Used by the forecast slider / heatmap.

**Request:**
```json
{
  "forecast_hour": 12,
  "departure_time": "2026-10-15T08:00:00Z",
  "routes": [{ "route_id": "route_0", "name": "Route 1", "checkpoints": [...] }],
  "load_weight_lb": 45000
}
```

---

## ⚠️ Risk Classification

### Base Thresholds

| Condition  | Low        | Moderate     | High         | Severe       | No Travel   |
|------------|-----------|-------------|-------------|-------------|-------------|
| Wind (mph) | < 25      | 25 – 34     | 35 – 44     | 45 – 54     | ≥ 55        |
| Rain (in/hr)| < 0.10   | 0.10 – 0.24 | 0.25 – 0.49 | 0.50 – 1.00 | > 1.00      |
| Snow (in/hr)| < 0.5    | 0.5 – 0.9   | 1.0 – 1.9   | 2.0 – 3.0   | > 3.0       |

### Cargo Weight Overrides (Wind Only)

| Condition                       | Override          |
|--------------------------------|-------------------|
| Wind 45-54 mph AND load > 30,000 lb | → No Travel    |
| Wind 35-44 mph AND load > 40,000 lb | → Severe       |

Overrides can only **increase** severity, never decrease it.

### Overall Risk
The checkpoint's overall risk is the **maximum** across wind, rain, and snow.

### Missing Data
If weather data is unavailable, the checkpoint is classified as **Unknown** (not Low).

---

## 🏆 Route Recommendation Logic

Routes are ranked using **lexicographic comparison** of eligible routes:

1. **Fewest Severe miles** (primary)
2. **Fewest High miles**
3. **Lowest average risk** (distance-weighted)
4. **Shortest travel time** (tiebreaker)

Routes containing **any No Travel** conditions are marked **ineligible** and excluded from recommendation.

If all routes are ineligible, the system returns a warning suggesting the driver delay departure.

---

## 🧪 Testing

```bash
cd backend
source venv/bin/activate
python manage.py test routing.tests
```

**101 tests** covering:

| Module                   | Tests | Coverage                                                                     |
|--------------------------|-------|------------------------------------------------------------------------------|
| `test_risk.py`           | 72    | All wind/rain/snow thresholds, boundary values, cargo overrides, overall risk|
| `test_checkpoint.py`     | 9     | Interval generation, partial segments, ETA, distance sums                    |
| `test_recommendation.py` | 8     | Lexicographic ranking, No Travel exclusion, all ineligible, explanations     |
| `test_routing.py`        | 4     | OpenRouteService routing, OSRM routing, automatic fallback behavior          |
| `test_views.py`          | 8     | Health check, geocoding, validation, serializer behavior                     |

---

## 🚢 Deployment

### Backend (Render)

1. Create a new **Web Service** on [Render](https://render.com)
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Add environment variables:
   - `ORS_API_KEY` — your OpenRouteService API key
   - `DJANGO_SECRET_KEY` — a strong random string
   - `DJANGO_DEBUG` — `False`
   - `DJANGO_ALLOWED_HOSTS` — your Render domain
   - `CORS_ALLOWED_ORIGINS` — your Vercel frontend URL

### Frontend (Vercel)

1. Create a new project on [Vercel](https://vercel.com)
2. Set framework preset to **Vite**
3. Set root directory to `frontend/`
4. Add a `vercel.json` in `frontend/`:

```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://your-backend.onrender.com/api/$1" }
  ]
}
```

---

## 📐 Assumptions & Design Decisions

1. **Arrival-time weather**: Weather is evaluated at each checkpoint's estimated arrival time based on the departure time + proportional travel duration — not at the departure time.

2. **Checkpoint interpolation**: Uses Haversine great-circle distance with linear interpolation between polyline vertices. Partial segments at the end of a route generate a final checkpoint.

3. **Risk thresholds**: Boundary values follow the assessment's exact definitions. Inclusive/exclusive boundaries are documented in `risk.py`.

4. **Cargo weight thresholds**: The assessment uses "greater than" (not "≥"), so exactly 30,000 lb does NOT trigger the override; 30,001 lb does.

5. **Missing weather = Unknown**: If the Open-Meteo API returns null for a parameter, that parameter's risk is "Unknown". Unknown values don't contribute to the weighted average but are tracked separately.

6. **No database**: This assessment doesn't require persistence. Routes are analyzed on-demand. SQLite is configured for Django but unused for application logic.

7. **Open-Meteo unit conversion**: The API returns metric units; the service layer converts wind from km/h to mph, rain from mm/hr to in/hr, and snow from cm/hr to in/hr.

8. **Forecast slider ≠ trip timeline**: The 0-48h slider shows weather at a specific future hour across all checkpoints simultaneously. The trip analysis shows weather at each checkpoint's individual arrival time. These are separate calculations per the assessment.

---

## 📁 Project Structure

```
weather-aware-truck/
├── backend/
│   ├── config/                 # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── routing/                # Django app
│   │   ├── services/           # Business logic layer
│   │   │   ├── geocoding.py    # Nominatim geocoding
│   │   │   ├── routing.py      # OpenRouteService
│   │   │   ├── checkpoint.py   # Haversine checkpoint generation
│   │   │   ├── weather.py      # Open-Meteo weather fetching
│   │   │   ├── risk.py         # Risk classification thresholds
│   │   │   └── recommendation.py # Ranking & recommendation
│   │   ├── tests/              # Unit tests (97 tests)
│   │   ├── views.py            # API endpoint handlers
│   │   ├── serializers.py      # DRF request validation
│   │   └── urls.py             # URL routing
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm.jsx        # Trip input with geocoding
│   │   │   ├── LocationInput.jsx   # Autocomplete input
│   │   │   ├── RouteCard.jsx       # Route comparison card
│   │   │   ├── RouteMap.jsx        # Leaflet map
│   │   │   ├── ResultsPanel.jsx    # Results container
│   │   │   └── ForecastSlider.jsx  # 0-48h heatmap slider
│   │   ├── services/
│   │   │   └── api.js          # Axios API layer
│   │   ├── utils/
│   │   │   └── helpers.js      # Formatting & risk utilities
│   │   ├── App.jsx             # Main application
│   │   ├── main.jsx            # Entry point
│   │   └── index.css           # Design system (Tailwind v4)
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .gitignore
└── README.md
```
