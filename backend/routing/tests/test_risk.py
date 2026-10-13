"""
Tests for the risk classification service.

Tests every threshold boundary for wind, rain, and snow.
Tests cargo-weight overrides with exact boundary values.
Tests overall checkpoint risk calculation.
"""
from django.test import TestCase
from routing.services.risk import (
    classify_wind_risk, classify_rain_risk, classify_snow_risk,
    apply_cargo_weight_override, classify_checkpoint_risk,
    LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN,
)


class WindRiskTests(TestCase):
    """Test wind risk thresholds: <25 Low, 25-<35 Moderate, 35-<45 High, 45-<55 Severe, >=55 No Travel."""

    def test_none_returns_unknown(self):
        self.assertEqual(classify_wind_risk(None), UNKNOWN)

    def test_zero_wind(self):
        self.assertEqual(classify_wind_risk(0), LOW)

    def test_below_25_low(self):
        self.assertEqual(classify_wind_risk(24.9), LOW)

    def test_at_25_moderate(self):
        self.assertEqual(classify_wind_risk(25), MODERATE)

    def test_between_25_35_moderate(self):
        self.assertEqual(classify_wind_risk(30), MODERATE)

    def test_below_35_moderate(self):
        self.assertEqual(classify_wind_risk(34.9), MODERATE)

    def test_at_35_high(self):
        self.assertEqual(classify_wind_risk(35), HIGH)

    def test_between_35_45_high(self):
        self.assertEqual(classify_wind_risk(40), HIGH)

    def test_below_45_high(self):
        self.assertEqual(classify_wind_risk(44.9), HIGH)

    def test_at_45_severe(self):
        self.assertEqual(classify_wind_risk(45), SEVERE)

    def test_between_45_55_severe(self):
        self.assertEqual(classify_wind_risk(50), SEVERE)

    def test_below_55_severe(self):
        self.assertEqual(classify_wind_risk(54.9), SEVERE)

    def test_at_55_no_travel(self):
        self.assertEqual(classify_wind_risk(55), NO_TRAVEL)

    def test_above_55_no_travel(self):
        self.assertEqual(classify_wind_risk(60), NO_TRAVEL)
        self.assertEqual(classify_wind_risk(100), NO_TRAVEL)


class RainRiskTests(TestCase):
    """Test rain risk thresholds: <0.10 Low, 0.10-<0.25 Moderate, 0.25-<0.50 High, 0.50-1.00 Severe, >1.00 No Travel."""

    def test_none_returns_unknown(self):
        self.assertEqual(classify_rain_risk(None), UNKNOWN)

    def test_zero_rain(self):
        self.assertEqual(classify_rain_risk(0), LOW)

    def test_below_010_low(self):
        self.assertEqual(classify_rain_risk(0.09), LOW)

    def test_at_010_moderate(self):
        self.assertEqual(classify_rain_risk(0.10), MODERATE)

    def test_between_010_025_moderate(self):
        self.assertEqual(classify_rain_risk(0.15), MODERATE)

    def test_below_025_moderate(self):
        self.assertEqual(classify_rain_risk(0.249), MODERATE)

    def test_at_025_high(self):
        self.assertEqual(classify_rain_risk(0.25), HIGH)

    def test_between_025_050_high(self):
        self.assertEqual(classify_rain_risk(0.35), HIGH)

    def test_below_050_high(self):
        self.assertEqual(classify_rain_risk(0.499), HIGH)

    def test_at_050_severe(self):
        self.assertEqual(classify_rain_risk(0.50), SEVERE)

    def test_between_050_100_severe(self):
        self.assertEqual(classify_rain_risk(0.75), SEVERE)

    def test_at_100_severe(self):
        """Assessment says 0.50 to 1.00 is Severe (inclusive of 1.00)."""
        self.assertEqual(classify_rain_risk(1.00), SEVERE)

    def test_above_100_no_travel(self):
        self.assertEqual(classify_rain_risk(1.01), NO_TRAVEL)
        self.assertEqual(classify_rain_risk(2.00), NO_TRAVEL)


class SnowRiskTests(TestCase):
    """Test snow risk thresholds: <0.5 Low, 0.5-<1.0 Moderate, 1.0-<2.0 High, 2.0-3.0 Severe, >3.0 No Travel."""

    def test_none_returns_unknown(self):
        self.assertEqual(classify_snow_risk(None), UNKNOWN)

    def test_zero_snow(self):
        self.assertEqual(classify_snow_risk(0), LOW)

    def test_below_05_low(self):
        self.assertEqual(classify_snow_risk(0.49), LOW)

    def test_at_05_moderate(self):
        self.assertEqual(classify_snow_risk(0.5), MODERATE)

    def test_between_05_10_moderate(self):
        self.assertEqual(classify_snow_risk(0.7), MODERATE)

    def test_below_10_moderate(self):
        self.assertEqual(classify_snow_risk(0.99), MODERATE)

    def test_at_10_high(self):
        self.assertEqual(classify_snow_risk(1.0), HIGH)

    def test_between_10_20_high(self):
        self.assertEqual(classify_snow_risk(1.5), HIGH)

    def test_below_20_high(self):
        self.assertEqual(classify_snow_risk(1.99), HIGH)

    def test_at_20_severe(self):
        self.assertEqual(classify_snow_risk(2.0), SEVERE)

    def test_between_20_30_severe(self):
        self.assertEqual(classify_snow_risk(2.5), SEVERE)

    def test_at_30_severe(self):
        """Assessment says 2.0 to 3.0 is Severe (inclusive of 3.0)."""
        self.assertEqual(classify_snow_risk(3.0), SEVERE)

    def test_above_30_no_travel(self):
        self.assertEqual(classify_snow_risk(3.01), NO_TRAVEL)
        self.assertEqual(classify_snow_risk(5.0), NO_TRAVEL)


class CargoWeightOverrideTests(TestCase):
    """
    Test cargo-weight-dependent wind risk overrides.

    Rules:
    1. Wind >= 55 mph: No Travel for any load (handled by base classification).
    2. Wind 45-54 mph AND load > 30,000 lb: No Travel.
    3. Wind 35-44 mph AND load > 40,000 lb: Severe.

    The assessment uses strict greater-than for load thresholds.
    """

    # --- Assessment examples ---

    def test_example_40mph_20000lb_high(self):
        """Assessment example: 40 mph wind, 20,000 lb -> High."""
        result = apply_cargo_weight_override(HIGH, 40, 20000)
        self.assertEqual(result, HIGH)

    def test_example_40mph_45000lb_severe(self):
        """Assessment example: 40 mph wind, 45,000 lb -> Severe."""
        result = apply_cargo_weight_override(HIGH, 40, 45000)
        self.assertEqual(result, SEVERE)

    def test_example_50mph_35000lb_no_travel(self):
        """Assessment example: 50 mph wind, 35,000 lb -> No Travel."""
        result = apply_cargo_weight_override(SEVERE, 50, 35000)
        self.assertEqual(result, NO_TRAVEL)

    def test_example_60mph_10000lb_no_travel(self):
        """Assessment example: 60 mph wind, 10,000 lb -> No Travel."""
        result = apply_cargo_weight_override(NO_TRAVEL, 60, 10000)
        self.assertEqual(result, NO_TRAVEL)

    # --- Boundary tests for load = 30,000 lb ---

    def test_50mph_exactly_30000lb_severe(self):
        """Load exactly at 30,000 lb does NOT trigger Rule 2 (strict >)."""
        result = apply_cargo_weight_override(SEVERE, 50, 30000)
        self.assertEqual(result, SEVERE)

    def test_50mph_30001lb_no_travel(self):
        """Load at 30,001 lb triggers Rule 2."""
        result = apply_cargo_weight_override(SEVERE, 50, 30001)
        self.assertEqual(result, NO_TRAVEL)

    # --- Boundary tests for load = 40,000 lb ---

    def test_40mph_exactly_40000lb_high(self):
        """Load exactly at 40,000 lb does NOT trigger Rule 3 (strict >)."""
        result = apply_cargo_weight_override(HIGH, 40, 40000)
        self.assertEqual(result, HIGH)

    def test_40mph_40001lb_severe(self):
        """Load at 40,001 lb triggers Rule 3."""
        result = apply_cargo_weight_override(HIGH, 40, 40001)
        self.assertEqual(result, SEVERE)

    # --- Wind speed boundary tests ---

    def test_45mph_35000lb_no_travel(self):
        """Wind at 45 mph (in range 45-54) with load > 30k -> No Travel."""
        result = apply_cargo_weight_override(SEVERE, 45, 35000)
        self.assertEqual(result, NO_TRAVEL)

    def test_54mph_35000lb_no_travel(self):
        """Wind at 54 mph (still in 45-54 range) with load > 30k -> No Travel."""
        result = apply_cargo_weight_override(SEVERE, 54, 35000)
        self.assertEqual(result, NO_TRAVEL)

    def test_35mph_45000lb_severe(self):
        """Wind at 35 mph (in range 35-44) with load > 40k -> Severe."""
        result = apply_cargo_weight_override(HIGH, 35, 45000)
        self.assertEqual(result, SEVERE)

    def test_44mph_45000lb_severe(self):
        """Wind at 44 mph (still in 35-44 range) with load > 40k -> Severe."""
        result = apply_cargo_weight_override(HIGH, 44, 45000)
        self.assertEqual(result, SEVERE)

    # --- No override when conditions don't match ---

    def test_30mph_50000lb_no_override(self):
        """Wind at 30 mph is in Moderate range; no cargo override applies."""
        result = apply_cargo_weight_override(MODERATE, 30, 50000)
        self.assertEqual(result, MODERATE)

    def test_40mph_20000lb_no_override(self):
        """Wind in 35-44 range but load <= 40k: no override."""
        result = apply_cargo_weight_override(HIGH, 40, 20000)
        self.assertEqual(result, HIGH)

    def test_none_wind_returns_base(self):
        """None wind speed should not crash."""
        result = apply_cargo_weight_override(UNKNOWN, None, 45000)
        self.assertEqual(result, UNKNOWN)


class OverallCheckpointRiskTests(TestCase):
    """Test overall checkpoint risk = max severity of wind, rain, snow."""

    def test_all_low(self):
        result = classify_checkpoint_risk(10, 0.05, 0.1, 10000)
        self.assertEqual(result["overall_risk"], LOW)
        self.assertEqual(result["wind_risk"], LOW)
        self.assertEqual(result["rain_risk"], LOW)
        self.assertEqual(result["snow_risk"], LOW)
        self.assertFalse(result["has_missing_data"])

    def test_wind_drives_overall(self):
        """Wind: Moderate, Rain: Low, Snow: Low -> Overall: Moderate."""
        result = classify_checkpoint_risk(30, 0.05, 0.1, 10000)
        self.assertEqual(result["overall_risk"], MODERATE)

    def test_rain_drives_overall(self):
        """Wind: Low, Rain: High, Snow: Low -> Overall: High."""
        result = classify_checkpoint_risk(10, 0.30, 0.1, 10000)
        self.assertEqual(result["overall_risk"], HIGH)

    def test_snow_drives_overall(self):
        """Wind: Low, Rain: Low, Snow: Severe -> Overall: Severe."""
        result = classify_checkpoint_risk(10, 0.05, 2.5, 10000)
        self.assertEqual(result["overall_risk"], SEVERE)

    def test_mixed_highest_wins(self):
        """Wind: Moderate, Rain: High, Snow: Low -> Overall: High."""
        result = classify_checkpoint_risk(30, 0.30, 0.1, 10000)
        self.assertEqual(result["overall_risk"], HIGH)

    def test_no_travel_wind_with_cargo(self):
        """50 mph wind + 35,000 lb load -> No Travel overall."""
        result = classify_checkpoint_risk(50, 0.05, 0.1, 35000)
        self.assertEqual(result["overall_risk"], NO_TRAVEL)
        self.assertEqual(result["wind_risk"], NO_TRAVEL)

    def test_missing_data_flagged(self):
        """None values result in UNKNOWN and has_missing_data=True."""
        result = classify_checkpoint_risk(None, 0.05, 0.1, 10000)
        self.assertTrue(result["has_missing_data"])
        self.assertEqual(result["wind_risk"], UNKNOWN)

    def test_all_missing(self):
        """All None values -> UNKNOWN overall."""
        result = classify_checkpoint_risk(None, None, None, 10000)
        self.assertEqual(result["overall_risk"], UNKNOWN)
        self.assertTrue(result["has_missing_data"])
