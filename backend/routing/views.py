"""
API views for trip analysis.

Views orchestrate the service modules but contain no business logic themselves.
"""
import logging
from datetime import datetime, timezone, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripAnalysisSerializer, ForecastRequestSerializer
from .services.geocoding import geocode_address, GeocodingError
from .services.routing import get_alternative_routes, RoutingError
from .services.checkpoint import generate_checkpoints
from .services.weather import fetch_weather_for_checkpoints, fetch_forecast_at_hour
from .services.recommendation import calculate_route_risk_stats, recommend_route
from .services.risk import classify_checkpoint_risk

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health_check(request):
    """GET /api/health/ - Backend health status."""
    return Response({
        "status": "healthy",
        "service": "Weather-Aware Truck Routing API",
        "version": "1.0.0",
    })


@api_view(["GET"])
def geocode(request):
    """GET /api/geocode/?q=... - Geocode address to coordinates."""
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"error": "Query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(query) < 2:
        return Response(
            {"error": "Query must be at least 2 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        results = geocode_address(query)
    except GeocodingError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"results": results})


@api_view(["POST"])
def analyze_trip(request):
    """
    POST /api/trips/analyze/ - Full trip analysis.

    Orchestrates:
    1. Input validation
    2. Route generation (3 alternatives)
    3. Checkpoint generation along each route
    4. Weather forecast fetching at checkpoint ETAs
    5. Risk classification
    6. Risk-miles calculation
    7. Route recommendation
    """
    # 1. Validate input
    serializer = TripAnalysisSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid input.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    origin = data["origin"]
    destination = data["destination"]
    departure_time = data["departure_time"]
    load_weight_lb = data["load_weight_lb"]
    sampling_interval = data["sampling_interval_miles"]

    # Ensure departure_time is timezone-aware
    if departure_time.tzinfo is None:
        departure_time = departure_time.replace(tzinfo=timezone.utc)

    warnings = []

    # 2. Generate alternative routes
    try:
        raw_routes = get_alternative_routes(
            origin["lat"], origin["lon"],
            destination["lat"], destination["lon"],
        )
    except RoutingError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if len(raw_routes) < 3:
        warnings.append(
            f"Only {len(raw_routes)} route(s) available. "
            "The routing provider returned fewer than 3 alternatives for this trip."
        )

    # 3-6. Process each route
    processed_routes = []

    for route in raw_routes:
        try:
            # 3. Generate checkpoints
            checkpoints = generate_checkpoints(
                geometry=route["geometry"],
                route_id=route["route_id"],
                total_distance_m=route["distance_m"],
                total_duration_s=route["duration_s"],
                departure_time=departure_time,
                sampling_interval_miles=sampling_interval,
            )

            # 4. Fetch weather for all checkpoints
            checkpoints = fetch_weather_for_checkpoints(checkpoints)

            # 5-6. Calculate risk statistics (also classifies each checkpoint)
            risk_stats = calculate_route_risk_stats(checkpoints, load_weight_lb)

            # Calculate ETA
            eta = departure_time + timedelta(seconds=route["duration_s"])

            # Convert distance to miles
            distance_miles = route["distance_m"] * 0.000621371

            processed_routes.append({
                "route_id": route["route_id"],
                "name": route["name"],
                "summary": route["summary"],
                "distance_miles": round(distance_miles, 1),
                "distance_m": route["distance_m"],
                "duration_s": route["duration_s"],
                "duration_display": _format_duration(route["duration_s"]),
                "eta": eta.isoformat(),
                "encoded_polyline": route["encoded_polyline"],
                "geometry": [
                    [lat, lon] for lat, lon in route["geometry"]
                ],
                "checkpoints": checkpoints,
                "risk_stats": risk_stats,
            })

        except Exception as e:
            logger.error(f"Error processing route {route['route_id']}: {e}")
            warnings.append(
                f"Route {route['name']} could not be fully analyzed: {str(e)}"
            )
            continue

    if not processed_routes:
        return Response(
            {"error": "All routes failed during analysis. Please try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # 7. Route recommendation
    recommendation = recommend_route(processed_routes)

    # Build response
    response_data = {
        "trip": {
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time.isoformat(),
            "load_weight_lb": load_weight_lb,
            "sampling_interval_miles": sampling_interval,
        },
        "routes": processed_routes,
        "recommendation": recommendation,
        "warnings": warnings,
        "metadata": {
            "num_routes": len(processed_routes),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "forecast_horizon_note": (
                "Weather forecasts are hourly snapshots. Actual conditions may "
                "vary between forecast hours."
            ),
        },
    }

    return Response(response_data)


@api_view(["POST"])
def get_forecast(request):
    """
    POST /api/trips/forecast/ - Get forecast data for heatmap slider.

    This endpoint fetches weather data for a specific forecast hour offset
    (0-48 hours after departure). It reuses checkpoint coordinates from
    a previous analysis.
    """
    serializer = ForecastRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid input.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    departure_time = data["departure_time"]
    forecast_hour = data["forecast_hour"]
    load_weight_lb = data["load_weight_lb"]

    if departure_time.tzinfo is None:
        departure_time = departure_time.replace(tzinfo=timezone.utc)

    results = []

    for route_data in data["routes"]:
        route_id = route_data.get("route_id", "unknown")
        route_name = route_data.get("name", route_id)
        checkpoints = route_data.get("checkpoints", [])

        if not checkpoints:
            continue

        forecast_data = fetch_forecast_at_hour(
            checkpoints, departure_time, forecast_hour
        )

        # Classify risk for each forecast checkpoint
        for fc in forecast_data:
            weather = fc.get("weather", {})
            fc["risk"] = classify_checkpoint_risk(
                wind_speed_mph=weather.get("wind_speed_mph"),
                rain_rate_in_hr=weather.get("rain_rate_in_hr"),
                snow_rate_in_hr=weather.get("snow_rate_in_hr"),
                load_weight_lb=load_weight_lb,
            )

        results.append({
            "route_id": route_id,
            "name": route_name,
            "checkpoints": forecast_data,
        })

    return Response({
        "forecast_hour": forecast_hour,
        "forecast_time": (
            departure_time + timedelta(hours=forecast_hour)
        ).isoformat(),
        "routes": results,
    })


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
