from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('geocode/', views.geocode, name='geocode'),
    path('trips/analyze/', views.analyze_trip, name='analyze-trip'),
    path('trips/forecast/', views.get_forecast, name='get-forecast'),
]
