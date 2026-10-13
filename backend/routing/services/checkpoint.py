"""
Checkpoint generation service.

Generates weather checkpoints at fixed distance intervals along actual route
geometry. Uses the Haversine formula for geographic distance calculations.

Checkpoint convention:
- The first checkpoint is the route origin (cumulative_distance = 0).
- Subsequent checkpoints are placed at the sampling interval along the route.
- The final checkpoint is the route destination (may be a partial segment).
- Each checkpoint's segment_distance is the distance FROM the previous
  checkpoint TO this checkpoint (0 for the first checkpoint).
- Sum of all segment_distances equals the total route distance.
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

EARTH_RADIUS_MILES = 3958.8  # Mean Earth radius in miles


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in miles.

    Uses the Haversine formula. This is a spherical approximation; for the
    distances involved in truck routing (tens to hundreds of miles between
    geometry points), the error is negligible (<0.3%).
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_MILES * c


def interpolate_point(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> Tuple[float, float]:
    """
    Interpolate a point along the great-circle path between two points.

    Args:
        lat1, lon1: Start point coordinates.
        lat2, lon2: End point coordinates.
        fraction: Fraction of the distance from start to end (0.0 to 1.0).

    Returns:
        (lat, lon) of the interpolated point.
    """
    if fraction <= 0:
        return lat1, lon1
    if fraction >= 1:
        return lat2, lon2

    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    d = haversine_distance(lat1, lon1, lat2, lon2) / EARTH_RADIUS_MILES
    if d < 1e-10:
        return lat1, lon1

    a_coeff = math.sin((1 - fraction) * d) / math.sin(d)
    b_coeff = math.sin(fraction * d) / math.sin(d)

    x = a_coeff * math.cos(lat1_r) * math.cos(lon1_r) + b_coeff * math.cos(lat2_r) * math.cos(lon2_r)
    y = a_coeff * math.cos(lat1_r) * math.sin(lon1_r) + b_coeff * math.cos(lat2_r) * math.sin(lon2_r)
    z = a_coeff * math.sin(lat1_r) + b_coeff * math.sin(lat2_r)

    lat = math.atan2(z, math.sqrt(x ** 2 + y ** 2))
    lon = math.atan2(y, x)

    return math.degrees(lat), math.degrees(lon)


def generate_checkpoints(
    geometry: List[Tuple[float, float]],
    route_id: str,
    total_distance_m: float,
    total_duration_s: float,
    departure_time: datetime,
    sampling_interval_miles: int,
) -> List[Dict]:
    """
    Generate weather checkpoints along a route at fixed distance intervals.

    Args:
        geometry: List of (lat, lon) tuples from route geometry.
        route_id: Unique route identifier.
        total_distance_m: Total route distance in meters (from routing API).
        total_duration_s: Total route duration in seconds (from routing API).
        departure_time: Trip departure timestamp (timezone-aware).
        sampling_interval_miles: Distance between checkpoints in miles.

    Returns:
        List of checkpoint dicts with keys:
        - checkpoint_id, route_id, lat, lon
        - cumulative_distance_miles, segment_distance_miles
        - estimated_arrival_time
    """
    if not geometry or len(geometry) < 2:
        raise ValueError("Route geometry must contain at least 2 points.")

    if sampling_interval_miles <= 0:
        raise ValueError("Sampling interval must be positive.")

    # Calculate cumulative distances along the route geometry
    segment_distances = []
    cumulative_geo_distances = [0.0]

    for i in range(1, len(geometry)):
        lat1, lon1 = geometry[i - 1]
        lat2, lon2 = geometry[i]
        d = haversine_distance(lat1, lon1, lat2, lon2)
        segment_distances.append(d)
        cumulative_geo_distances.append(cumulative_geo_distances[-1] + d)

    total_geometry_distance = cumulative_geo_distances[-1]

    if total_geometry_distance < 0.01:  # Less than ~50 feet
        return _create_short_route_checkpoints(
            geometry, route_id, departure_time, total_duration_s
        )

    # Use API total distance (converted to miles) for speed/ETA calculations
    total_distance_miles = total_distance_m * 0.000621371

    # Average speed for ETA estimation
    if total_duration_s > 0:
        avg_speed_mph = total_distance_miles / (total_duration_s / 3600)
    else:
        avg_speed_mph = 55  # Fallback average speed

    # Generate checkpoint positions along the route
    checkpoints = []
    checkpoint_id = 0

    # First checkpoint: route origin
    origin_lat, origin_lon = geometry[0]
    checkpoints.append({
        "checkpoint_id": "{}_cp_{}".format(route_id, checkpoint_id),
        "route_id": route_id,
        "lat": origin_lat,
        "lon": origin_lon,
        "cumulative_distance_miles": 0.0,
        "segment_distance_miles": 0.0,
        "estimated_arrival_time": departure_time.isoformat(),
    })
    checkpoint_id += 1

    # Generate intermediate checkpoints at the sampling interval
    next_checkpoint_distance = float(sampling_interval_miles)
    geo_point_index = 0

    while next_checkpoint_distance < total_geometry_distance:
        # Find which geometry segment contains this checkpoint
        while (geo_point_index < len(cumulative_geo_distances) - 1 and
               cumulative_geo_distances[geo_point_index + 1] < next_checkpoint_distance):
            geo_point_index += 1

        if geo_point_index >= len(geometry) - 1:
            break

        # Interpolate position within the geometry segment
        seg_start_dist = cumulative_geo_distances[geo_point_index]
        seg_end_dist = cumulative_geo_distances[geo_point_index + 1]
        seg_length = seg_end_dist - seg_start_dist

        if seg_length > 0:
            fraction = (next_checkpoint_distance - seg_start_dist) / seg_length
        else:
            fraction = 0

        lat1, lon1 = geometry[geo_point_index]
        lat2, lon2 = geometry[geo_point_index + 1]
        cp_lat, cp_lon = interpolate_point(lat1, lon1, lat2, lon2, fraction)

        # Estimate arrival time
        distance_ratio = next_checkpoint_distance / total_geometry_distance
        elapsed_seconds = distance_ratio * total_duration_s
        eta = departure_time + timedelta(seconds=elapsed_seconds)

        segment_dist = next_checkpoint_distance - checkpoints[-1]["cumulative_distance_miles"]

        checkpoints.append({
            "checkpoint_id": "{}_cp_{}".format(route_id, checkpoint_id),
            "route_id": route_id,
            "lat": round(cp_lat, 6),
            "lon": round(cp_lon, 6),
            "cumulative_distance_miles": round(next_checkpoint_distance, 2),
            "segment_distance_miles": round(segment_dist, 2),
            "estimated_arrival_time": eta.isoformat(),
        })
        checkpoint_id += 1
        next_checkpoint_distance += sampling_interval_miles

    # Final checkpoint: route destination
    dest_lat, dest_lon = geometry[-1]
    last_cumulative = checkpoints[-1]["cumulative_distance_miles"]
    final_segment = total_geometry_distance - last_cumulative

    # Only add destination if it's not essentially at the last checkpoint
    if final_segment > 0.1:  # More than 0.1 miles from last checkpoint
        eta = departure_time + timedelta(seconds=total_duration_s)
        checkpoints.append({
            "checkpoint_id": "{}_cp_{}".format(route_id, checkpoint_id),
            "route_id": route_id,
            "lat": round(dest_lat, 6),
            "lon": round(dest_lon, 6),
            "cumulative_distance_miles": round(total_geometry_distance, 2),
            "segment_distance_miles": round(final_segment, 2),
            "estimated_arrival_time": eta.isoformat(),
        })
    else:
        # Update last checkpoint to be exactly at destination
        checkpoints[-1]["lat"] = round(dest_lat, 6)
        checkpoints[-1]["lon"] = round(dest_lon, 6)
        checkpoints[-1]["cumulative_distance_miles"] = round(total_geometry_distance, 2)
        checkpoints[-1]["estimated_arrival_time"] = (
            departure_time + timedelta(seconds=total_duration_s)
        ).isoformat()

    return checkpoints


def _create_short_route_checkpoints(
    geometry: List[Tuple[float, float]],
    route_id: str,
    departure_time: datetime,
    total_duration_s: float,
) -> List[Dict]:
    """Create checkpoints for a very short route (just origin and destination)."""
    origin_lat, origin_lon = geometry[0]
    dest_lat, dest_lon = geometry[-1]
    total_dist = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)

    return [
        {
            "checkpoint_id": "{}_cp_0".format(route_id),
            "route_id": route_id,
            "lat": round(origin_lat, 6),
            "lon": round(origin_lon, 6),
            "cumulative_distance_miles": 0.0,
            "segment_distance_miles": 0.0,
            "estimated_arrival_time": departure_time.isoformat(),
        },
        {
            "checkpoint_id": "{}_cp_1".format(route_id),
            "route_id": route_id,
            "lat": round(dest_lat, 6),
            "lon": round(dest_lon, 6),
            "cumulative_distance_miles": round(total_dist, 2),
            "segment_distance_miles": round(total_dist, 2),
            "estimated_arrival_time": (
                departure_time + timedelta(seconds=total_duration_s)
            ).isoformat(),
        },
    ]
