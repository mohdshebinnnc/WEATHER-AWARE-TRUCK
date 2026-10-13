"""
Tests for checkpoint generation service.

Tests interval placement, partial segments, short routes,
interpolation along geometry, and ETA calculation.
"""
from datetime import datetime, timezone, timedelta
from django.test import TestCase
from routing.services.checkpoint import (
    generate_checkpoints, haversine_distance, interpolate_point
)


class HaversineTests(TestCase):
    """Test geographic distance calculations."""

    def test_same_point_zero_distance(self):
        d = haversine_distance(40.0, -74.0, 40.0, -74.0)
        self.assertAlmostEqual(d, 0.0, places=5)

    def test_known_distance_nyc_to_la(self):
        """NYC to LA is approximately 2,451 miles."""
        d = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        self.assertAlmostEqual(d, 2451, delta=50)  # Within 50 miles

    def test_short_distance(self):
        """Two nearby points should give a small distance."""
        d = haversine_distance(40.0, -74.0, 40.001, -74.001)
        self.assertGreater(d, 0)
        self.assertLess(d, 1)  # Less than 1 mile


class InterpolationTests(TestCase):
    """Test point interpolation along great-circle path."""

    def test_fraction_zero(self):
        lat, lon = interpolate_point(40.0, -74.0, 41.0, -73.0, 0.0)
        self.assertAlmostEqual(lat, 40.0, places=5)
        self.assertAlmostEqual(lon, -74.0, places=5)

    def test_fraction_one(self):
        lat, lon = interpolate_point(40.0, -74.0, 41.0, -73.0, 1.0)
        self.assertAlmostEqual(lat, 41.0, places=5)
        self.assertAlmostEqual(lon, -73.0, places=5)

    def test_fraction_half(self):
        """Midpoint should be roughly between the two points."""
        lat, lon = interpolate_point(40.0, -74.0, 42.0, -72.0, 0.5)
        self.assertGreater(lat, 40.0)
        self.assertLess(lat, 42.0)
        self.assertGreater(lon, -74.0)
        self.assertLess(lon, -72.0)


class CheckpointGenerationTests(TestCase):
    """Test checkpoint generation with various intervals."""

    def _make_geometry(self, n_points, start_lat=40.0, start_lon=-74.0,
                       delta_lat=0.01, delta_lon=0.01):
        """Create a simple geometry line with n points."""
        return [
            (start_lat + i * delta_lat, start_lon + i * delta_lon)
            for i in range(n_points)
        ]

    def _departure(self):
        return datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)

    def test_10_mile_interval(self):
        """50-mile route with 10-mile interval should have ~6 checkpoints."""
        # Create a route roughly 50 miles long
        # Each degree of latitude is ~69 miles, so 0.73 degrees ≈ 50 miles
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test_route", total_dist_m, 3600,
            self._departure(), 10
        )

        # Should have origin + intermediate + destination
        self.assertGreaterEqual(len(cps), 5)

        # First checkpoint should be at origin
        self.assertEqual(cps[0]["cumulative_distance_miles"], 0.0)
        self.assertEqual(cps[0]["segment_distance_miles"], 0.0)

        # Check monotonically increasing distances
        for i in range(1, len(cps)):
            self.assertGreater(
                cps[i]["cumulative_distance_miles"],
                cps[i - 1]["cumulative_distance_miles"]
            )

    def test_25_mile_interval(self):
        """50-mile route with 25-mile interval should have ~3 checkpoints."""
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test_route", total_dist_m, 3600,
            self._departure(), 25
        )

        # Should have origin + 1 intermediate + destination
        self.assertGreaterEqual(len(cps), 3)

    def test_50_mile_interval(self):
        """50-mile route with 50-mile interval should have origin + destination."""
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test_route", total_dist_m, 3600,
            self._departure(), 50
        )

        # Should have origin + destination (final partial segment)
        self.assertGreaterEqual(len(cps), 2)

    def test_final_partial_segment(self):
        """Last segment should be shorter than the interval."""
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test_route", total_dist_m, 3600,
            self._departure(), 10
        )

        # Last checkpoint's segment distance should be <= interval
        last_seg = cps[-1]["segment_distance_miles"]
        self.assertLessEqual(last_seg, 10.5)  # Small tolerance for rounding

    def test_short_route(self):
        """Route shorter than sampling interval should have 2 checkpoints."""
        # Two points ~0.5 miles apart
        geometry = [
            (40.0, -74.0),
            (40.007, -74.0),
        ]
        total_dist = haversine_distance(40.0, -74.0, 40.007, -74.0)
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "short", total_dist_m, 60,
            self._departure(), 10
        )

        self.assertEqual(len(cps), 2)

    def test_eta_monotonically_increasing(self):
        """ETAs should increase along the route."""
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test", total_dist_m, 3600,
            self._departure(), 10
        )

        for i in range(1, len(cps)):
            eta_prev = datetime.fromisoformat(cps[i - 1]["estimated_arrival_time"])
            eta_curr = datetime.fromisoformat(cps[i]["estimated_arrival_time"])
            self.assertGreaterEqual(eta_curr, eta_prev)

    def test_first_eta_equals_departure(self):
        """First checkpoint's ETA should be the departure time."""
        geometry = self._make_geometry(50, delta_lat=0.01, delta_lon=0)
        departure = self._departure()

        cps = generate_checkpoints(
            geometry, "test", 100000, 3600,
            departure, 10
        )

        first_eta = datetime.fromisoformat(cps[0]["estimated_arrival_time"])
        self.assertEqual(first_eta, departure)

    def test_segment_distances_sum_to_total(self):
        """Sum of segment distances should approximately equal total route distance."""
        geometry = self._make_geometry(100, delta_lat=0.0073, delta_lon=0)
        total_dist = haversine_distance(
            geometry[0][0], geometry[0][1],
            geometry[-1][0], geometry[-1][1]
        )
        total_dist_m = total_dist / 0.000621371

        cps = generate_checkpoints(
            geometry, "test", total_dist_m, 3600,
            self._departure(), 10
        )

        segment_sum = sum(cp["segment_distance_miles"] for cp in cps)
        # Should be close to total geometry distance
        self.assertAlmostEqual(segment_sum, total_dist, delta=1.0)

    def test_invalid_geometry_raises(self):
        """Less than 2 geometry points should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_checkpoints(
                [(40.0, -74.0)], "test", 1000, 60,
                self._departure(), 10
            )

    def test_invalid_interval_raises(self):
        """Zero or negative interval should raise ValueError."""
        geometry = self._make_geometry(10)
        with self.assertRaises(ValueError):
            generate_checkpoints(
                geometry, "test", 1000, 60,
                self._departure(), 0
            )
