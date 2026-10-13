"""
Tests for route recommendation service.

Verifies:
1. Lexicographic priority order (Severe miles -> High miles -> Avg risk -> Duration)
2. Ineligibility of routes containing No Travel conditions
3. Graceful handling when all routes are ineligible
4. Distance-weighted average risk and risk-mile calculations
5. Unknown weather data handling and warning generation
6. Explanation generation accuracy
"""
from django.test import TestCase
from routing.services.recommendation import (
    calculate_route_risk_stats,
    recommend_route,
)
from routing.services.risk import (
    LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN,
)


class RecommendationStatsTests(TestCase):
    """Test calculate_route_risk_stats calculation accuracy."""

    def test_basic_risk_stats(self):
        checkpoints = [
            {
                "cumulative_distance_miles": 0.0,
                "segment_distance_miles": 0.0,
                "weather": {"wind_speed_mph": 10, "rain_rate_in_hr": 0.0, "snow_rate_in_hr": 0.0},
            },
            {
                "cumulative_distance_miles": 25.0,
                "segment_distance_miles": 25.0,
                "weather": {"wind_speed_mph": 15, "rain_rate_in_hr": 0.0, "snow_rate_in_hr": 0.0},
            },
            {
                "cumulative_distance_miles": 50.0,
                "segment_distance_miles": 25.0,
                "weather": {"wind_speed_mph": 30, "rain_rate_in_hr": 0.0, "snow_rate_in_hr": 0.0},
            },
        ]
        # load_weight 40,000 lb:
        # cp 0 (dist 0): Low
        # cp 1 (dist 25): Low (wind 15 <= 20)
        # cp 2 (dist 25): Moderate (wind 35 in (20, 35])
        stats = calculate_route_risk_stats(checkpoints, load_weight_lb=40000)

        self.assertEqual(stats["total_distance_miles"], 50.0)
        self.assertEqual(stats["risk_miles"]["low"], 25.0)
        self.assertEqual(stats["risk_miles"]["moderate"], 25.0)
        self.assertEqual(stats["risk_miles"]["high"], 0.0)
        self.assertEqual(stats["risk_miles"]["severe"], 0.0)
        self.assertEqual(stats["risk_miles"]["no_travel"], 0.0)
        self.assertTrue(stats["is_eligible"])
        self.assertFalse(stats["has_no_travel"])
        # avg risk: (25*1 + 25*2) / 50 = 75 / 50 = 1.5
        self.assertEqual(stats["average_risk"], 1.5)

    def test_no_travel_marks_ineligible(self):
        checkpoints = [
            {
                "cumulative_distance_miles": 0.0,
                "segment_distance_miles": 0.0,
                "weather": {"wind_speed_mph": 10, "rain_rate_in_hr": 0.0, "snow_rate_in_hr": 0.0},
            },
            {
                "cumulative_distance_miles": 30.0,
                "segment_distance_miles": 30.0,
                "weather": {"wind_speed_mph": 65, "rain_rate_in_hr": 0.0, "snow_rate_in_hr": 0.0},
            },
        ]
        stats = calculate_route_risk_stats(checkpoints, load_weight_lb=50000)
        self.assertFalse(stats["is_eligible"])
        self.assertTrue(stats["has_no_travel"])
        self.assertEqual(stats["risk_miles"]["no_travel"], 30.0)
        self.assertIn("No Travel", stats["eligibility_reason"])

    def test_missing_weather_handled_as_unknown(self):
        checkpoints = [
            {
                "cumulative_distance_miles": 0.0,
                "segment_distance_miles": 0.0,
                "weather": {"wind_speed_mph": None, "rain_rate_in_hr": None, "snow_rate_in_hr": None},
            },
            {
                "cumulative_distance_miles": 20.0,
                "segment_distance_miles": 20.0,
                "weather": {"wind_speed_mph": None, "rain_rate_in_hr": None, "snow_rate_in_hr": None},
            },
        ]
        stats = calculate_route_risk_stats(checkpoints, load_weight_lb=40000)
        self.assertTrue(stats["has_unknown_data"])
        self.assertEqual(stats["risk_miles"]["unknown"], 20.0)


class RecommendationRankingTests(TestCase):
    """Test lexicographic priority order."""

    def test_priority_1_fewest_severe_miles(self):
        # Route 1: 5 severe miles, travel time 3000s
        # Route 2: 15 severe miles, travel time 2000s (faster)
        route_1 = {
            "route_id": "route_1",
            "name": "Route 1",
            "duration_s": 3000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 5.0, "high": 10.0, "moderate": 0.0, "low": 0.0},
                "average_risk": 3.5,
            },
        }
        route_2 = {
            "route_id": "route_2",
            "name": "Route 2",
            "duration_s": 2000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 15.0, "high": 0.0, "moderate": 0.0, "low": 0.0},
                "average_risk": 3.0,
            },
        }
        res = recommend_route([route_1, route_2])
        self.assertEqual(res["recommended_route_id"], "route_1")
        self.assertIn("fewest Severe-risk miles", res["explanation"])

    def test_priority_2_fewest_high_miles(self):
        # Severe miles are equal (0)
        # Route 1: 5 high miles, duration 3000s
        # Route 2: 20 high miles, duration 2000s (faster)
        route_1 = {
            "route_id": "route_1",
            "name": "Route 1",
            "duration_s": 3000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 5.0, "moderate": 10.0, "low": 0.0},
                "average_risk": 2.5,
            },
        }
        route_2 = {
            "route_id": "route_2",
            "name": "Route 2",
            "duration_s": 2000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 20.0, "moderate": 0.0, "low": 0.0},
                "average_risk": 2.2,
            },
        }
        res = recommend_route([route_1, route_2])
        self.assertEqual(res["recommended_route_id"], "route_1")
        self.assertIn("fewest High-risk miles", res["explanation"])

    def test_priority_3_lowest_average_risk(self):
        # Severe miles equal (0), High miles equal (0)
        # Route 1 has lower avg risk (more Low miles than Moderate)
        route_1 = {
            "route_id": "route_1",
            "name": "Route 1",
            "duration_s": 3500,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 0.0, "moderate": 5.0, "low": 45.0},
                "average_risk": 1.1,
            },
        }
        route_2 = {
            "route_id": "route_2",
            "name": "Route 2",
            "duration_s": 3000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 0.0, "moderate": 25.0, "low": 25.0},
                "average_risk": 1.5,
            },
        }
        res = recommend_route([route_1, route_2])
        self.assertEqual(res["recommended_route_id"], "route_1")
        self.assertIn("lowest average risk", res["explanation"])

    def test_priority_4_shortest_duration(self):
        # Severe, High, and Avg Risk identical -> Shortest travel time wins
        route_1 = {
            "route_id": "route_1",
            "name": "Route 1",
            "duration_s": 3600,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 0.0, "moderate": 0.0, "low": 50.0},
                "average_risk": 1.0,
            },
        }
        route_2 = {
            "route_id": "route_2",
            "name": "Route 2",
            "duration_s": 3000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 0.0, "moderate": 0.0, "low": 50.0},
                "average_risk": 1.0,
            },
        }
        res = recommend_route([route_1, route_2])
        self.assertEqual(res["recommended_route_id"], "route_2")
        self.assertIn("shortest travel time", res["explanation"])

    def test_ineligible_route_never_recommended(self):
        # Route 1 has No Travel conditions, but is super fast
        route_1 = {
            "route_id": "route_1",
            "name": "Dangerous Fast Route",
            "duration_s": 1000,
            "risk_stats": {
                "is_eligible": False,
                "risk_miles": {"severe": 0.0, "high": 0.0, "moderate": 0.0, "low": 40.0, "no_travel": 10.0},
                "average_risk": 1.5,
            },
        }
        # Route 2 is eligible, though has some moderate risk
        route_2 = {
            "route_id": "route_2",
            "name": "Safe Slower Route",
            "duration_s": 3000,
            "risk_stats": {
                "is_eligible": True,
                "risk_miles": {"severe": 0.0, "high": 2.0, "moderate": 10.0, "low": 40.0},
                "average_risk": 1.6,
            },
        }
        res = recommend_route([route_1, route_2])
        self.assertEqual(res["recommended_route_id"], "route_2")

    def test_all_routes_ineligible(self):
        route_1 = {
            "route_id": "route_1",
            "name": "Route 1",
            "duration_s": 2000,
            "risk_stats": {"is_eligible": False, "risk_miles": {"no_travel": 5.0}},
        }
        route_2 = {
            "route_id": "route_2",
            "name": "Route 2",
            "duration_s": 2500,
            "risk_stats": {"is_eligible": False, "risk_miles": {"no_travel": 12.0}},
        }
        res = recommend_route([route_1, route_2])
        self.assertIsNone(res["recommended_route_id"])
        self.assertIn("No safe route can be recommended", res["explanation"])

    def test_empty_route_list(self):
        res = recommend_route([])
        self.assertIsNone(res["recommended_route_id"])
