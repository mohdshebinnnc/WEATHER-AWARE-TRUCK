"""
API view tests for trip analysis endpoints.
"""
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")


class GeocodeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_geocode_missing_query(self):
        response = self.client.get("/api/geocode/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_geocode_short_query(self):
        response = self.client.get("/api/geocode/?q=a")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("routing.views.geocode_address")
    def test_geocode_success(self, mock_geocode):
        mock_geocode.return_value = [
            {"display_name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298}
        ]
        response = self.client.get("/api/geocode/?q=Chicago")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["lat"], 41.8781)


class AnalyzeTripViewValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_analyze_empty_payload(self):
        response = self.client.post("/api/trips/analyze/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyze_invalid_coordinates(self):
        payload = {
            "origin": {"lat": 95.0, "lon": -87.6298, "name": "Invalid Lat"},
            "destination": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO"},
            "departure_time": "2026-10-15T08:00:00Z",
            "load_weight_lb": 45000,
            "sampling_interval_miles": 25,
        }
        response = self.client.post("/api/trips/analyze/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyze_invalid_interval(self):
        payload = {
            "origin": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
            "destination": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO"},
            "departure_time": "2026-10-15T08:00:00Z",
            "load_weight_lb": 45000,
            "sampling_interval_miles": 35,  # must be 10, 25, or 50
        }
        response = self.client.post("/api/trips/analyze/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ForecastViewValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_forecast_invalid_hour(self):
        payload = {
            "forecast_hour": 55,  # max is 48
            "routes": [],
            "load_weight_lb": 40000,
        }
        response = self.client.post("/api/trips/forecast/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
