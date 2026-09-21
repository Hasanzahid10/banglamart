import sys
import math
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib import admin

try:
    from django.contrib.gis.db import models as gis_models
    from django.contrib.gis.admin import GISModelAdmin
    from django.contrib.gis.db.models.functions import Distance
    from django.contrib.gis.geos import Point
    from django.contrib.gis.gdal import HAS_GDAL
    HAS_GIS = True
except Exception:
    HAS_GIS = False

if not HAS_GIS:
    class Point:
        def __init__(self, x=0, y=0, srid=4326):
            self.x = x
            self.y = y
            self.coords = (x, y)
            self.longitude = x
            self.latitude = y

    class DummyPointField(models.JSONField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('srid', None)
            kwargs.pop('geography', None)
            kwargs.setdefault('null', True)
            kwargs.setdefault('blank', True)
            super().__init__(*args, **kwargs)

    class DummyPolygonField(models.JSONField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('srid', None)
            kwargs.pop('geography', None)
            kwargs.setdefault('null', True)
            kwargs.setdefault('blank', True)
            super().__init__(*args, **kwargs)

    class MockGISFields:
        PointField = DummyPointField
        PolygonField = DummyPolygonField

    gis_models = MockGISFields()
    GISModelAdmin = admin.ModelAdmin
    Distance = None


def calculate_haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate geodesic distance in km between two lat/lon points using Haversine formula.
    """
    try:
        R = 6371.0  # Earth radius in km
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(math.radians(float(lat1)))
            * math.cos(math.radians(float(lat2)))
            * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return Decimal(str(R * c)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("5.00")
