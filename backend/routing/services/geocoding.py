"""
Geocoding service using Nominatim (OpenStreetMap).

Nominatim usage policy: max 1 request/second, custom User-Agent required.
https://nominatim.org/release-docs/develop/api/Search/
"""
import requests
import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "WeatherAwareTruckRouting/1.0 (assessment project)"
REQUEST_TIMEOUT = 10  # seconds

# Simple rate limiter: track last request time
_last_request_time = 0


def _rate_limit():
    """Ensure at least 1 second between Nominatim requests."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.time()


def geocode_address(query: str, limit: int = 5) -> List[Dict]:
    """
    Geocode a text query into candidate locations.

    Args:
        query: Address or place name to geocode.
        limit: Maximum number of results (default 5).

    Returns:
        List of dicts with keys: display_name, lat, lon, type.

    Raises:
        GeocodingError: If the request fails.
    """
    if not query or not query.strip():
        raise GeocodingError("Geocoding query cannot be empty.")

    _rate_limit()

    try:
        response = requests.get(
            "{}/search".format(NOMINATIM_BASE_URL),
            params={
                "q": query.strip(),
                "format": "json",
                "limit": limit,
                "addressdetails": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise GeocodingError("Geocoding service timed out. Please try again.")
    except requests.RequestException as e:
        logger.error("Geocoding request failed: %s", e)
        raise GeocodingError("Geocoding service unavailable: {}".format(str(e)))

    results = response.json()
    if not results:
        return []

    return [
        {
            "display_name": r.get("display_name", ""),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "type": r.get("type", "unknown"),
        }
        for r in results
    ]


class GeocodingError(Exception):
    """Raised when geocoding fails."""
    pass
