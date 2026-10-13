"""
Route recommendation service.

Calculates risk-miles, evaluates route eligibility, and ranks routes
using the assessment's exact priority order:

1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk (distance-weighted)
4. Shortest travel time

No Travel routes are marked ineligible for safe recommendation.
Missing weather data is handled conservatively.
"""
from typing import List, Dict, Optional
from .risk import (
    RISK_VALUES, LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN,
    classify_checkpoint_risk,
)


def calculate_route_risk_stats(
    checkpoints: List[Dict],
    load_weight_lb: float,
) -> Dict:
    """
    Calculate risk-mile statistics for a route's checkpoints.

    Each checkpoint's segment_distance_miles represents the distance from the
    previous checkpoint to this checkpoint. The first checkpoint has
    segment_distance = 0 (it's the origin point).

    Risk-miles are calculated by assigning each checkpoint's overall risk
    to its segment_distance.

    Args:
        checkpoints: List of checkpoint dicts with weather data and segment distances.
        load_weight_lb: Truck cargo weight for risk classification.

    Returns:
        Dict with risk statistics.
    """
    risk_miles = {
        NO_TRAVEL: 0.0,
        SEVERE: 0.0,
        HIGH: 0.0,
        MODERATE: 0.0,
        LOW: 0.0,
        UNKNOWN: 0.0,
    }

    total_distance = 0.0
    weighted_risk_sum = 0.0
    weighted_risk_distance = 0.0
    has_no_travel = False
    has_unknown = False
    all_warnings = []

    for cp in checkpoints:
        weather = cp.get("weather", {})
        segment_dist = cp.get("segment_distance_miles", 0.0)

        # Classify risk for this checkpoint
        risk_result = classify_checkpoint_risk(
            wind_speed_mph=weather.get("wind_speed_mph"),
            rain_rate_in_hr=weather.get("rain_rate_in_hr"),
            snow_rate_in_hr=weather.get("snow_rate_in_hr"),
            load_weight_lb=load_weight_lb,
        )

        # Store risk data on the checkpoint
        cp["risk"] = risk_result

        overall = risk_result["overall_risk"]
        risk_miles[overall] = risk_miles.get(overall, 0) + segment_dist
        total_distance += segment_dist

        if overall == NO_TRAVEL:
            has_no_travel = True
        if overall == UNKNOWN:
            has_unknown = True

        # Weighted risk for average calculation
        if overall in RISK_VALUES:
            weighted_risk_sum += RISK_VALUES[overall] * segment_dist
            weighted_risk_distance += segment_dist

        # Collect warnings
        warnings = weather.get("warnings", [])
        if risk_result.get("has_missing_data"):
            warnings.append(
                "Missing weather data at mile {}".format(
                    cp.get('cumulative_distance_miles', '?')
                )
            )
        all_warnings.extend(warnings)

    # Calculate distance-weighted average risk
    if weighted_risk_distance > 0:
        avg_risk = round(weighted_risk_sum / weighted_risk_distance, 2)
    else:
        avg_risk = 0

    # Determine eligibility
    is_eligible = not has_no_travel
    eligibility_reason = ""

    if has_no_travel:
        no_travel_miles = risk_miles[NO_TRAVEL]
        eligibility_reason = (
            "Route contains {:.1f} miles of No Travel conditions. "
            "This route is not safe for travel.".format(no_travel_miles)
        )
    elif has_unknown and risk_miles[UNKNOWN] > total_distance * 0.5:
        eligibility_reason = (
            "Weather data is unavailable for {:.1f} miles "
            "({:.0f}% of the route). "
            "Safety assessment may be incomplete.".format(
                risk_miles[UNKNOWN],
                risk_miles[UNKNOWN] / total_distance * 100 if total_distance > 0 else 0
            )
        )

    return {
        "risk_miles": {
            "no_travel": round(risk_miles[NO_TRAVEL], 2),
            "severe": round(risk_miles[SEVERE], 2),
            "high": round(risk_miles[HIGH], 2),
            "moderate": round(risk_miles[MODERATE], 2),
            "low": round(risk_miles[LOW], 2),
            "unknown": round(risk_miles[UNKNOWN], 2),
        },
        "total_distance_miles": round(total_distance, 2),
        "average_risk": avg_risk,
        "has_no_travel": has_no_travel,
        "has_unknown_data": has_unknown,
        "is_eligible": is_eligible,
        "eligibility_reason": eligibility_reason,
        "num_checkpoints": len(checkpoints),
        "warnings": list(set(all_warnings)),
    }


def recommend_route(routes: List[Dict]) -> Dict:
    """
    Select the best route using the assessment's priority order.

    Priority (lexicographic comparison of eligible routes):
    1. Fewest Severe miles
    2. Fewest High miles
    3. Lowest average risk (distance-weighted)
    4. Shortest travel time (duration_s)

    No Travel routes are excluded from the safe recommendation.

    Args:
        routes: List of route dicts, each containing:
            - route_id, name
            - risk_stats (from calculate_route_risk_stats)
            - duration_s

    Returns:
        Dict with recommendation result.
    """
    if not routes:
        return {
            "recommended_route_id": None,
            "explanation": "No routes available to evaluate.",
            "route_rankings": [],
        }

    # Separate eligible and ineligible routes
    eligible = []
    ineligible = []

    for route in routes:
        stats = route.get("risk_stats", {})
        if stats.get("is_eligible", False):
            eligible.append(route)
        else:
            ineligible.append(route)

    # If no eligible routes, return warning
    if not eligible:
        return {
            "recommended_route_id": None,
            "explanation": (
                "No safe route can be recommended. All available routes contain "
                "No Travel weather conditions. Consider delaying departure or "
                "choosing a different day."
            ),
            "route_rankings": _build_rankings(routes, None),
        }

    # Sort eligible routes by the priority tuple (lexicographic)
    def sort_key(route):
        stats = route["risk_stats"]
        return (
            stats["risk_miles"]["severe"],
            stats["risk_miles"]["high"],
            stats["average_risk"],
            route.get("duration_s", float("inf")),
        )

    eligible.sort(key=sort_key)
    best = eligible[0]
    best_id = best["route_id"]
    best_stats = best["risk_stats"]

    # Generate explanation
    explanation = _generate_recommendation_explanation(best, eligible)

    return {
        "recommended_route_id": best_id,
        "explanation": explanation,
        "route_rankings": _build_rankings(routes, best_id),
    }


def _generate_recommendation_explanation(best: Dict, eligible: List[Dict]) -> str:
    """Generate a clear explanation of why the recommended route was chosen."""
    name = best.get("name", best["route_id"])
    stats = best["risk_stats"]

    if len(eligible) == 1:
        return "{} is recommended as the only eligible route.".format(name)

    # Determine which criterion differentiated the winner
    parts = ["{} is recommended".format(name)]

    others = [r for r in eligible if r["route_id"] != best["route_id"]]

    # Check if Severe miles differ
    best_severe = stats["risk_miles"]["severe"]
    others_severe = [r["risk_stats"]["risk_miles"]["severe"] for r in others]

    if any(s > best_severe for s in others_severe):
        parts.append(
            "because it has the fewest Severe-risk miles ({:.1f} mi)".format(best_severe)
        )
    else:
        # Severe miles are equal; check High miles
        best_high = stats["risk_miles"]["high"]
        others_high = [r["risk_stats"]["risk_miles"]["high"] for r in others]

        if any(h > best_high for h in others_high):
            parts.append(
                "because it has the fewest High-risk miles "
                "({:.1f} mi) among routes with equal Severe exposure".format(best_high)
            )
        else:
            # Check average risk
            best_avg = stats["average_risk"]
            others_avg = [r["risk_stats"]["average_risk"] for r in others]

            if any(a > best_avg for a in others_avg):
                parts.append(
                    "because it has the lowest average risk score ({:.2f})".format(best_avg)
                )
            else:
                parts.append("because it has the shortest travel time")

    explanation = " ".join(parts) + "."

    # Add context about unknown data if present
    if stats.get("has_unknown_data"):
        unknown_mi = stats["risk_miles"]["unknown"]
        explanation += (
            " Note: {:.1f} miles have unavailable weather data.".format(unknown_mi)
        )

    return explanation


def _build_rankings(routes: List[Dict], recommended_id: Optional[str]) -> List[Dict]:
    """Build ranked route list for the response."""
    rankings = []

    def sort_key(route):
        stats = route.get("risk_stats", {})
        rm = stats.get("risk_miles", {})
        return (
            0 if stats.get("is_eligible") else 1,
            rm.get("severe", float("inf")),
            rm.get("high", float("inf")),
            stats.get("average_risk", float("inf")),
            route.get("duration_s", float("inf")),
        )

    sorted_routes = sorted(routes, key=sort_key)

    for rank, route in enumerate(sorted_routes, 1):
        rankings.append({
            "rank": rank,
            "route_id": route["route_id"],
            "name": route.get("name", route["route_id"]),
            "is_recommended": route["route_id"] == recommended_id,
            "is_eligible": route.get("risk_stats", {}).get("is_eligible", False),
        })

    return rankings
