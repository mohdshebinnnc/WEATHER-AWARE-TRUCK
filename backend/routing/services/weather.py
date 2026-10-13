"""
Weather service using Open-Meteo API.

Open-Meteo docs: https://open-meteo.com/en/docs

Variables used:
- wind_speed_10m: Wind speed at 10m height (km/h) -> convert to mph
- rain: Rain volume for the previous hour (mm) -> convert to in/hr
- snowfall: Snowfall volume for the previous hour (cm) -> convert to in/hr

Unit conversions:
- km/h to mph: multiply by 0.621371
- mm to inches: divide by 25.4
- cm to inches: divide by 2.54

IMPORTANT: Open-Meteo's hourly "rain" is in mm for the preceding hour,
making it already a rate (mm/hr). Similarly, "snowfall" is in cm for the
preceding hour (cm/hr). We convert these to in/hr directly.

Forecast horizon: Open-Meteo provides hourly forecasts for up to 16 days.
For the 0-48 hour slider requirement, this is sufficient.
"""
import requests
import logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 15  # seconds
MAX_CONCURRENT_REQUESTS = 5  # Bounded concurrency


class WeatherError(Exception):
    """Raised when weather data fetching fails."""
    pass


def fetch_weather_for_checkpoint(
    lat: float,
    lon: float,
    target_time: datetime,
) -> Dict:
    """
    Fetch weather forecast for a single checkpoint at its estimated arrival time.

    Args:
        lat: Checkpoint latitude.
        lon: Checkpoint longitude.
        target_time: Expected arrival time at the checkpoint (timezone-aware).

    Returns:
        Dict with keys:
        - wind_speed_mph: float or None
        - rain_rate_in_hr: float or None
        - snow_rate_in_hr: float or None
        - forecast_time: str (ISO format of the matched forecast hour)
        - warnings: list of warning strings
    """
    warnings = []

    # Ensure target_time is timezone-aware
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    # Convert to UTC for API consistency
    target_utc = target_time.astimezone(timezone.utc)

    # Open-Meteo needs a date range; request the specific day
    date_str = target_utc.strftime("%Y-%m-%d")

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "hourly": "wind_speed_10m,rain,snowfall",
                "start_date": date_str,
                "end_date": date_str,
                "timezone": "UTC",
                "wind_speed_unit": "kmh",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        logger.warning("Weather API timeout for (%s, %s)", lat, lon)
        return _missing_weather_result("Weather API timed out for this location.")
    except requests.RequestException as e:
        logger.error("Weather request failed for (%s, %s): %s", lat, lon, e)
        return _missing_weather_result("Weather service unavailable: {}".format(str(e)))

    if response.status_code == 429:
        logger.warning("Weather API rate limit hit")
        return _missing_weather_result("Weather API rate limit exceeded.")

    if response.status_code != 200:
        logger.error("Weather API error %s: %s", response.status_code, response.text[:200])
        return _missing_weather_result("Weather API returned an error.")

    try:
        data = response.json()
    except ValueError:
        return _missing_weather_result("Weather API returned invalid data.")

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    winds = hourly.get("wind_speed_10m", [])
    rains = hourly.get("rain", [])
    snows = hourly.get("snowfall", [])

    if not times:
        return _missing_weather_result("No forecast data available for this time.")

    # Find the nearest forecast hour to the target time
    target_hour = target_utc.hour
    best_index = None
    best_diff = float("inf")

    for i, time_str in enumerate(times):
        try:
            forecast_dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            diff = abs((forecast_dt - target_utc).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_index = i
        except (ValueError, TypeError):
            continue

    if best_index is None:
        return _missing_weather_result("Could not match forecast time.")

    # Check if the nearest forecast is reasonably close (within 1 hour)
    if best_diff > 3600:
        warnings.append(
            "Nearest forecast is {:.1f} hours from arrival time. "
            "Weather data may not be representative.".format(best_diff / 3600)
        )

    # Extract and convert values
    wind_kmh = winds[best_index] if best_index < len(winds) else None
    rain_mm = rains[best_index] if best_index < len(rains) else None
    snow_cm = snows[best_index] if best_index < len(snows) else None

    result = {
        "forecast_time": times[best_index],
        "warnings": warnings,
    }

    # Convert wind: km/h -> mph
    if wind_kmh is not None:
        result["wind_speed_mph"] = round(wind_kmh * 0.621371, 1)
    else:
        result["wind_speed_mph"] = None
        warnings.append("Wind speed data unavailable.")

    # Convert rain: mm/hr -> in/hr (already a rate)
    if rain_mm is not None:
        result["rain_rate_in_hr"] = round(rain_mm / 25.4, 4)
    else:
        result["rain_rate_in_hr"] = None
        warnings.append("Rainfall data unavailable.")

    # Convert snowfall: cm/hr -> in/hr (already a rate)
    if snow_cm is not None:
        result["snow_rate_in_hr"] = round(snow_cm / 2.54, 4)
    else:
        result["snow_rate_in_hr"] = None
        warnings.append("Snowfall data unavailable.")

    return result


def fetch_weather_for_checkpoints(checkpoints: List[Dict]) -> List[Dict]:
    """
    Fetch weather for multiple checkpoints with bounded concurrency.

    Enriches each checkpoint dict with weather data in-place and returns
    the updated list.
    """
    cache = {}

    def _cache_key(cp):
        eta = datetime.fromisoformat(cp["estimated_arrival_time"])
        return (
            round(cp["lat"], 2),
            round(cp["lon"], 2),
            eta.strftime("%Y-%m-%d %H:00"),
        )

    # Identify unique weather queries
    unique_queries = {}
    for cp in checkpoints:
        key = _cache_key(cp)
        if key not in unique_queries:
            eta = datetime.fromisoformat(cp["estimated_arrival_time"])
            unique_queries[key] = {
                "lat": cp["lat"],
                "lon": cp["lon"],
                "target_time": eta,
            }

    # Fetch unique weather data with bounded concurrency
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        future_to_key = {}
        for key, query in unique_queries.items():
            future = executor.submit(
                fetch_weather_for_checkpoint,
                query["lat"],
                query["lon"],
                query["target_time"],
            )
            future_to_key[future] = key

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                cache[key] = future.result()
            except Exception as e:
                logger.error("Weather fetch failed for %s: %s", key, e)
                cache[key] = _missing_weather_result(str(e))

    # Assign weather data to checkpoints
    for cp in checkpoints:
        key = _cache_key(cp)
        weather = cache.get(key, _missing_weather_result("Weather lookup failed."))
        cp["weather"] = weather

    return checkpoints


def fetch_forecast_at_hour(
    checkpoints: List[Dict],
    departure_time: datetime,
    forecast_hour: int,
) -> List[Dict]:
    """
    Fetch weather for checkpoints at a specific forecast hour offset.

    This is used for the 0-48 hour forecast slider, which shows weather
    at a fixed time offset from departure rather than at each checkpoint's
    individual arrival time.
    """
    forecast_time = departure_time + timedelta(hours=forecast_hour)

    results = []
    cache = {}

    for i, cp in enumerate(checkpoints):
        cache_key = (round(cp["lat"], 2), round(cp["lon"], 2))
        if cache_key not in cache:
            weather = fetch_weather_for_checkpoint(
                cp["lat"], cp["lon"], forecast_time
            )
            cache[cache_key] = weather

        results.append({
            "checkpoint_id": cp.get("checkpoint_id", i),
            "lat": cp["lat"],
            "lon": cp["lon"],
            "cumulative_distance_miles": cp.get("cumulative_distance_miles", 0),
            "segment_distance_miles": cp.get("segment_distance_miles", 0),
            "weather": cache[cache_key],
        })

    return results


def _missing_weather_result(warning_msg: str) -> Dict:
    """Create a result dict for missing/unavailable weather data."""
    return {
        "wind_speed_mph": None,
        "rain_rate_in_hr": None,
        "snow_rate_in_hr": None,
        "forecast_time": None,
        "warnings": [warning_msg],
    }
