"""
Risk classification service.

Implements the exact weather risk thresholds from the assessment,
including cargo-weight-dependent wind overrides.

Risk levels (ordered by severity):
    Low (1) < Moderate (2) < High (3) < Severe (4) < No Travel (5)

All thresholds use the assessment's exact boundary definitions.
"""
from typing import Optional, Dict, List

# Risk level constants
LOW = "Low"
MODERATE = "Moderate"
HIGH = "High"
SEVERE = "Severe"
NO_TRAVEL = "No Travel"
UNKNOWN = "Unknown"

# Numeric values for average risk calculations
RISK_VALUES = {
    LOW: 1,
    MODERATE: 2,
    HIGH: 3,
    SEVERE: 4,
    NO_TRAVEL: 5,
}

RISK_ORDER = [LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL]


def classify_wind_risk(wind_speed_mph: Optional[float]) -> str:
    """
    Classify wind risk based on speed in mph.

    Thresholds:
        Below 25 mph: Low
        25 to below 35 mph: Moderate
        35 to below 45 mph: High
        45 to below 55 mph: Severe
        55 mph or higher: No Travel

    Args:
        wind_speed_mph: Wind speed in miles per hour, or None if unavailable.

    Returns:
        Risk level string.
    """
    if wind_speed_mph is None:
        return UNKNOWN

    if wind_speed_mph < 25:
        return LOW
    elif wind_speed_mph < 35:
        return MODERATE
    elif wind_speed_mph < 45:
        return HIGH
    elif wind_speed_mph < 55:
        return SEVERE
    else:
        return NO_TRAVEL


def classify_rain_risk(rain_rate_in_hr: Optional[float]) -> str:
    """
    Classify rainfall risk based on rate in inches per hour.

    Thresholds:
        Below 0.10 in/hr: Low
        0.10 to below 0.25 in/hr: Moderate
        0.25 to below 0.50 in/hr: High
        0.50 to 1.00 in/hr: Severe
        Above 1.00 in/hr: No Travel

    Note: The assessment defines Severe as "0.50 to 1.00" and No Travel as
    "Above 1.00". We interpret this as:
    - Severe: 0.50 <= rain <= 1.00
    - No Travel: rain > 1.00

    Args:
        rain_rate_in_hr: Rainfall rate in inches per hour, or None if unavailable.

    Returns:
        Risk level string.
    """
    if rain_rate_in_hr is None:
        return UNKNOWN

    if rain_rate_in_hr < 0.10:
        return LOW
    elif rain_rate_in_hr < 0.25:
        return MODERATE
    elif rain_rate_in_hr < 0.50:
        return HIGH
    elif rain_rate_in_hr <= 1.00:
        return SEVERE
    else:
        return NO_TRAVEL


def classify_snow_risk(snow_rate_in_hr: Optional[float]) -> str:
    """
    Classify snowfall risk based on rate in inches per hour.

    Thresholds:
        Below 0.5 in/hr: Low
        0.5 to below 1.0 in/hr: Moderate
        1.0 to below 2.0 in/hr: High
        2.0 to 3.0 in/hr: Severe
        Above 3.0 in/hr: No Travel

    Note: The assessment defines Severe as "2.0 to 3.0" and No Travel as
    "Above 3.0". We interpret this as:
    - Severe: 2.0 <= snow <= 3.0
    - No Travel: snow > 3.0

    Args:
        snow_rate_in_hr: Snowfall rate in inches per hour, or None if unavailable.

    Returns:
        Risk level string.
    """
    if snow_rate_in_hr is None:
        return UNKNOWN

    if snow_rate_in_hr < 0.5:
        return LOW
    elif snow_rate_in_hr < 1.0:
        return MODERATE
    elif snow_rate_in_hr < 2.0:
        return HIGH
    elif snow_rate_in_hr <= 3.0:
        return SEVERE
    else:
        return NO_TRAVEL


def apply_cargo_weight_override(
    base_wind_risk: str,
    wind_speed_mph: Optional[float],
    load_weight_lb: float,
) -> str:
    """
    Apply cargo-weight-dependent wind risk overrides.

    Override rules (applied AFTER base wind classification):
    1. Wind >= 55 mph: No Travel for every load (already handled by base).
    2. Wind 45-54 mph AND load > 30,000 lb: No Travel.
    3. Wind 35-44 mph AND load > 40,000 lb: Severe.

    Overrides can only INCREASE severity, never decrease it.

    The assessment uses strict greater-than for load thresholds:
    - "> 30,000 lb" means 30,001+ lb triggers the override
    - "> 40,000 lb" means 40,001+ lb triggers the override
    - Loads exactly at 30,000 lb or 40,000 lb do NOT trigger overrides

    Args:
        base_wind_risk: Base wind risk classification.
        wind_speed_mph: Wind speed in mph.
        load_weight_lb: Truck cargo weight in pounds.

    Returns:
        Final wind risk classification (may be elevated).
    """
    if wind_speed_mph is None or base_wind_risk == UNKNOWN:
        return base_wind_risk

    final_risk = base_wind_risk

    # Rule 2: Wind 45-54 mph AND load > 30,000 lb -> No Travel
    if 45 <= wind_speed_mph < 55 and load_weight_lb > 30000:
        final_risk = NO_TRAVEL

    # Rule 3: Wind 35-44 mph AND load > 40,000 lb -> Severe
    if 35 <= wind_speed_mph < 45 and load_weight_lb > 40000:
        # Only apply if this would INCREASE the severity
        if _risk_severity(SEVERE) > _risk_severity(final_risk):
            final_risk = SEVERE

    return final_risk


def _risk_severity(risk: str) -> int:
    """Get numeric severity for comparison. UNKNOWN is treated as 0."""
    return RISK_VALUES.get(risk, 0)


def classify_checkpoint_risk(
    wind_speed_mph: Optional[float],
    rain_rate_in_hr: Optional[float],
    snow_rate_in_hr: Optional[float],
    load_weight_lb: float,
) -> Dict:
    """
    Calculate complete risk classification for a checkpoint.

    Args:
        wind_speed_mph: Wind speed in mph.
        rain_rate_in_hr: Rainfall rate in in/hr.
        snow_rate_in_hr: Snowfall rate in in/hr.
        load_weight_lb: Truck cargo weight in pounds.

    Returns:
        Dict with keys:
        - wind_risk: str
        - rain_risk: str
        - snow_risk: str
        - overall_risk: str
        - has_missing_data: bool
        - risk_explanation: str
    """
    # Base classifications
    base_wind_risk = classify_wind_risk(wind_speed_mph)
    rain_risk = classify_rain_risk(rain_rate_in_hr)
    snow_risk = classify_snow_risk(snow_rate_in_hr)

    # Apply cargo weight overrides to wind risk
    wind_risk = apply_cargo_weight_override(
        base_wind_risk, wind_speed_mph, load_weight_lb
    )

    # Track missing data
    risks = [wind_risk, rain_risk, snow_risk]
    has_missing = UNKNOWN in risks

    # Overall risk = highest applicable severity
    known_risks = [r for r in risks if r != UNKNOWN]

    if not known_risks:
        overall_risk = UNKNOWN
    else:
        overall_risk = max(known_risks, key=lambda r: RISK_VALUES.get(r, 0))

    # Generate explanation
    explanation = _generate_risk_explanation(
        wind_risk, rain_risk, snow_risk, overall_risk,
        wind_speed_mph, rain_rate_in_hr, snow_rate_in_hr,
        load_weight_lb, base_wind_risk, has_missing
    )

    return {
        "wind_risk": wind_risk,
        "rain_risk": rain_risk,
        "snow_risk": snow_risk,
        "overall_risk": overall_risk,
        "has_missing_data": has_missing,
        "risk_explanation": explanation,
    }


def _generate_risk_explanation(
    wind_risk, rain_risk, snow_risk, overall_risk,
    wind_mph, rain_in, snow_in, load_lb,
    base_wind_risk, has_missing
) -> str:
    """Generate a human-readable risk explanation."""
    parts = []

    if overall_risk == UNKNOWN:
        return "Risk cannot be determined due to missing weather data."

    if overall_risk == LOW:
        return "All weather conditions are within safe limits."

    # Identify which conditions drive the overall risk
    if wind_risk == overall_risk and wind_risk != LOW:
        msg = "Wind: {:.0f} mph ({})".format(wind_mph, wind_risk)
        if wind_risk != base_wind_risk:
            msg += " — elevated from {} due to {:,.0f} lb load".format(base_wind_risk, load_lb)
        parts.append(msg)

    if rain_risk == overall_risk and rain_risk != LOW:
        parts.append("Rain: {:.2f} in/hr ({})".format(rain_in, rain_risk))

    if snow_risk == overall_risk and snow_risk != LOW:
        parts.append("Snow: {:.2f} in/hr ({})".format(snow_in, snow_risk))

    if has_missing:
        parts.append("Some weather data is unavailable")

    return "; ".join(parts) if parts else "Overall risk: {}".format(overall_risk)
