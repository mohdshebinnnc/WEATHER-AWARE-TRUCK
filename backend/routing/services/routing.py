"""
Routing service supporting OpenRouteService (ORS) with OSRM fallback.

Requests alternative driving routes and normalizes the response.
- When ORS_API_KEY is configured, queries OpenRouteService v2 directions.
- When ORS_API_KEY is not set or ORS request fails/rate-limits, transparently
  falls back to OSRM (Open Source Routing Machine) public service.

Limitation: Driving profiles approximate car driving routes and do not enforce
truck-specific physical restrictions (height, bridge weight, hazmat).
This is documented as an architectural consideration.
"""
import requests
import logging
from typing import List, Dict
import polyline as polyline_lib
from django.conf import settings

logger = logging.getLogger(__name__)

ORS_BASE_URL = "https://api.openrouteservice.org"
OSRM_BASE_URL = "http://router.project-osrm.org"
REQUEST_TIMEOUT = 30  # seconds

ROUTE_NAMES = ["Route A", "Route B", "Route C", "Route D", "Route E"]


class RoutingError(Exception):
    """Raised when route generation fails."""
    pass


def _fetch_ors_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    api_key: str,
    num_alternatives: int = 2,
) -> List[Dict]:
    """Request driving routes from OpenRouteService."""
    coordinates = [
        [origin_lon, origin_lat],
        [dest_lon, dest_lat],
    ]

    try:
        response = requests.post(
            f"{ORS_BASE_URL}/v2/directions/driving-car",
            json={
                "coordinates": coordinates,
                "alternative_routes": {
                    "share_factor": 0.6,
                    "target_count": num_alternatives + 1,
                    "weight_factor": 1.4,
                },
                "geometry": True,
                "instructions": False,
            },
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise RoutingError("OpenRouteService request timed out.")
    except requests.RequestException as e:
        raise RoutingError(f"OpenRouteService connection failed: {e}")

    if response.status_code == 401:
        raise RoutingError("Invalid OpenRouteService API key.")
    if response.status_code == 429:
        raise RoutingError("OpenRouteService rate limit exceeded.")
    if response.status_code != 200:
        error_msg = f"OpenRouteService returned status {response.status_code}"
        try:
            err = response.json().get("error", {})
            if isinstance(err, dict):
                error_msg = err.get("message", error_msg)
            elif isinstance(err, str):
                error_msg = err
        except Exception:
            pass
        raise RoutingError(error_msg)

    data = response.json()
    raw_routes = data.get("routes", [])
    if not raw_routes:
        raise RoutingError("No routes returned by OpenRouteService.")

    routes = []
    for i, raw in enumerate(raw_routes):
        summary_obj = raw.get("summary", {})
        encoded_geom = raw.get("geometry", "")

        try:
            decoded = polyline_lib.decode(encoded_geom)
        except Exception as e:
            logger.warning("Failed to decode ORS geometry for route %d: %s", i, e)
            continue

        if len(decoded) < 2:
            continue

        route_name = ROUTE_NAMES[i] if i < len(ROUTE_NAMES) else f"Route {i + 1}"
        routes.append({
            "route_id": f"route_{i}",
            "name": route_name,
            "summary": raw.get("summary_text") or route_name,
            "distance_m": float(summary_obj.get("distance", 0)),
            "duration_s": float(summary_obj.get("duration", 0)),
            "geometry": decoded,
            "encoded_polyline": encoded_geom,
        })

    return routes


def _fetch_osrm_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    num_alternatives: int = 2,
) -> List[Dict]:
    """Request driving routes from OSRM demo server."""
    # OSRM expects coordinates as lon,lat;lon,lat
    alt_param = "true" if num_alternatives > 0 else "false"
    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        f"?overview=full&geometries=polyline&alternatives={alt_param}"
    )

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "WeatherAwareTruckRouting/1.0"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise RoutingError("OSRM routing service timed out.")
    except requests.RequestException as e:
        raise RoutingError(f"OSRM routing connection failed: {e}")

    if response.status_code != 200:
        raise RoutingError(f"OSRM returned status {response.status_code}")

    data = response.json()
    if data.get("code") != "Ok":
        raise RoutingError(data.get("message", "No routes found between locations."))

    raw_routes = data.get("routes", [])
    if not raw_routes:
        raise RoutingError("No routes returned by OSRM.")

    routes = []
    for i, raw in enumerate(raw_routes):
        encoded_geom = raw.get("geometry", "")
        try:
            decoded = polyline_lib.decode(encoded_geom)
        except Exception as e:
            logger.warning("Failed to decode OSRM geometry for route %d: %s", i, e)
            continue

        if len(decoded) < 2:
            continue

        route_name = ROUTE_NAMES[i] if i < len(ROUTE_NAMES) else f"Route {i + 1}"
        legs = raw.get("legs", [])
        summary_text = ""
        if legs and legs[0].get("summary"):
            summary_text = f"via {legs[0]['summary']}"
        if not summary_text:
            summary_text = route_name

        routes.append({
            "route_id": f"route_{i}",
            "name": route_name,
            "summary": summary_text,
            "distance_m": float(raw.get("distance", 0)),
            "duration_s": float(raw.get("duration", 0)),
            "geometry": decoded,
            "encoded_polyline": encoded_geom,
        })

    return routes


def get_alternative_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    num_alternatives: int = 2,
) -> List[Dict]:
    """
    Request driving routes with alternatives.
    
    Tries OpenRouteService first if ORS_API_KEY is configured.
    Falls back to OSRM automatically if ORS key is absent, expired, or rate-limited.

    Args:
        origin_lat, origin_lon: Origin coordinates.
        dest_lat, dest_lon: Destination coordinates.
        num_alternatives: Number of alternative routes.

    Returns:
        List of normalized route dicts.

    Raises:
        RoutingError: If all routing providers fail.
    """
    api_key = getattr(settings, "ORS_API_KEY", "")
    routes = []
    last_error = None

    # Try ORS if API key is provided
    if api_key:
        try:
            logger.info("Attempting route generation with OpenRouteService")
            routes = _fetch_ors_routes(
                origin_lat, origin_lon, dest_lat, dest_lon, api_key, num_alternatives
            )
        except RoutingError as e:
            logger.warning("OpenRouteService failed: %s. Falling back to OSRM.", e)
            last_error = e

    # Fall back to OSRM if no routes yet
    if not routes:
        logger.info("Generating routes using OSRM engine")
        try:
            routes = _fetch_osrm_routes(
                origin_lat, origin_lon, dest_lat, dest_lon, num_alternatives
            )
        except RoutingError as e:
            logger.error("OSRM failed: %s", e)
            raise RoutingError(
                f"Routing failed: {e}" if not last_error else f"Routing failed (ORS: {last_error}, OSRM: {e})"
            )

    if not routes:
        raise RoutingError("All returned routes had invalid geometry.")

    if len(routes) < 3:
        logger.info(
            "Only %d route(s) available. Provider returned fewer alternatives.",
            len(routes),
        )

    return routes
