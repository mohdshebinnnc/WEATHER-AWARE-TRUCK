"""
Tests for routing service with ORS and OSRM support.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
import polyline

from routing.services.routing import (
    get_alternative_routes,
    _fetch_ors_routes,
    _fetch_osrm_routes,
    RoutingError,
)


class RoutingServiceTests(TestCase):
    def setUp(self):
        # Sample coordinates: Chicago to Detroit
        self.origin_lat = 41.8781
        self.origin_lon = -87.6298
        self.dest_lat = 42.3314
        self.dest_lon = -83.0458
        self.sample_geom = polyline.encode([(41.8781, -87.6298), (42.0, -85.0), (42.3314, -83.0458)])

    @patch("routing.services.routing.requests.post")
    def test_fetch_ors_routes_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [
                {
                    "summary": {"distance": 450000, "duration": 18000},
                    "geometry": self.sample_geom,
                    "summary_text": "via I-94 E",
                },
                {
                    "summary": {"distance": 470000, "duration": 19500},
                    "geometry": self.sample_geom,
                    "summary_text": "via I-80 E / I-69 N",
                },
            ]
        }
        mock_post.return_value = mock_response

        routes = _fetch_ors_routes(
            self.origin_lat, self.origin_lon, self.dest_lat, self.dest_lon, "mock-key", 2
        )
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["route_id"], "route_0")
        self.assertEqual(routes[0]["name"], "Route A")
        self.assertEqual(routes[0]["distance_m"], 450000.0)
        self.assertEqual(routes[1]["route_id"], "route_1")
        self.assertEqual(routes[1]["name"], "Route B")

    @patch("routing.services.routing.requests.get")
    def test_fetch_osrm_routes_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 453228.0,
                    "duration": 19090.1,
                    "geometry": self.sample_geom,
                    "legs": [{"summary": "I-94"}],
                },
                {
                    "distance": 477316.0,
                    "duration": 20656.0,
                    "geometry": self.sample_geom,
                    "legs": [{"summary": "I-80"}],
                },
            ],
        }
        mock_get.return_value = mock_response

        routes = _fetch_osrm_routes(
            self.origin_lat, self.origin_lon, self.dest_lat, self.dest_lon, 2
        )
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["route_id"], "route_0")
        self.assertEqual(routes[0]["name"], "Route A")
        self.assertEqual(routes[0]["summary"], "via I-94")
        self.assertAlmostEqual(routes[0]["distance_m"], 453228.0)

    @override_settings(ORS_API_KEY="")
    @patch("routing.services.routing._fetch_osrm_routes")
    def test_get_alternative_routes_uses_osrm_when_no_ors_key(self, mock_osrm):
        mock_osrm.return_value = [{"route_id": "route_0", "name": "Route A", "distance_m": 100, "duration_s": 10, "geometry": [(41.0, -87.0), (42.0, -83.0)], "encoded_polyline": "abc", "summary": "Route A"}]
        routes = get_alternative_routes(self.origin_lat, self.origin_lon, self.dest_lat, self.dest_lon)
        mock_osrm.assert_called_once()
        self.assertEqual(len(routes), 1)

    @override_settings(ORS_API_KEY="test-key")
    @patch("routing.services.routing._fetch_ors_routes")
    @patch("routing.services.routing._fetch_osrm_routes")
    def test_get_alternative_routes_falls_back_to_osrm_on_ors_failure(self, mock_osrm, mock_ors):
        mock_ors.side_effect = RoutingError("ORS 429 Rate limit exceeded")
        mock_osrm.return_value = [{"route_id": "route_0", "name": "Route A", "distance_m": 100, "duration_s": 10, "geometry": [(41.0, -87.0), (42.0, -83.0)], "encoded_polyline": "abc", "summary": "Route A"}]

        routes = get_alternative_routes(self.origin_lat, self.origin_lon, self.dest_lat, self.dest_lon)
        mock_ors.assert_called_once()
        mock_osrm.assert_called_once()
        self.assertEqual(len(routes), 1)
