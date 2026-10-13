from rest_framework import serializers
from datetime import datetime, timezone


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    name = serializers.CharField(required=False, allow_blank=True, default="")


class TripAnalysisSerializer(serializers.Serializer):
    origin = CoordinateSerializer()
    destination = CoordinateSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.FloatField(min_value=0)
    sampling_interval_miles = serializers.ChoiceField(choices=[10, 25, 50])

    def validate_sampling_interval_miles(self, value):
        return int(value)

    def validate(self, data):
        origin = data['origin']
        dest = data['destination']
        if (abs(origin['lat'] - dest['lat']) < 0.001 and
                abs(origin['lon'] - dest['lon']) < 0.001):
            raise serializers.ValidationError(
                "Origin and destination must be different locations."
            )
        return data


class ForecastRequestSerializer(serializers.Serializer):
    """Request forecast data for the heatmap slider."""
    routes = serializers.ListField(child=serializers.DictField())
    departure_time = serializers.DateTimeField()
    forecast_hour = serializers.IntegerField(min_value=0, max_value=48)
    load_weight_lb = serializers.FloatField(min_value=0)
