from django.urls import path

from app.api import views

urlpatterns = [
    path("plates/", views.plates, name="api-plates"),
    path("plates/<str:plate_text>/", views.plate_detail, name="api-plate-detail"),
    path("detections/", views.detections, name="api-detections"),
    path("stats/", views.stats, name="api-stats"),
]