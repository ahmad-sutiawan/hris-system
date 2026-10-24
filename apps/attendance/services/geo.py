"""Geo-fence validation for mobile/web punch."""

from __future__ import annotations

import math

from django.conf import settings
from django.core.cache import cache

from apps.core.models import PunchLocation, Plant


class GeoFenceError(Exception):
    pass


def _geo_cache_key(tenant_id: int, plant_id: int | None) -> str:
    return f"hris:geo_points:{tenant_id}:{plant_id or 0}"


def invalidate_geo_cache(*, tenant_id: int, plant_id: int | None) -> None:
    """Hapus cache plant ini dan cabang anaknya (karyawan cabang memakai kunci plant sendiri)."""
    keys = [_geo_cache_key(tenant_id, plant_id)]
    if plant_id:
        child_ids = Plant.objects.filter(parent_id=plant_id).values_list("pk", flat=True)
        keys.extend(_geo_cache_key(tenant_id, child_id) for child_id in child_ids)
    cache.delete_many(keys)


def punch_locations_for_employee(employee) -> list[dict]:
    """Lokasi yang sama dengan validasi absen, untuk peta di aplikasi."""
    if employee is None:
        return []
    return [
        {
            "name": label,
            "latitude": lat,
            "longitude": lng,
            "radius_m": radius,
        }
        for lat, lng, radius, label in _points_for_employee(employee)
    ]


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _resolve_pt_plant(plant) -> Plant | None:
    """Cabang karyawan → plant induk (PT); plant PT tetap dipakai."""
    if not plant:
        return None
    if plant.entity_type == Plant.EntityType.PT:
        return plant
    if plant.parent_id:
        return plant.parent
    return plant


def _points_for_employee(employee) -> list[tuple[float, float, int, str]]:
    plant = employee.plant
    tenant_id = employee.tenant_id
    plant_id = plant.pk if plant else None
    cache_key = _geo_cache_key(tenant_id, plant_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    points: list[tuple[float, float, int, str]] = []
    seen_plants: set[int] = set()
    for site in (plant, _resolve_pt_plant(plant)):
        if site is None or site.pk in seen_plants:
            continue
        seen_plants.add(site.pk)
        if site.latitude is None or site.longitude is None:
            continue
        radius = site.geo_fence_radius_m or 150
        points.append((float(site.latitude), float(site.longitude), radius, site.name))

    location_plant_ids: list[int] = []
    if plant_id:
        location_plant_ids.append(plant_id)
    pt = _resolve_pt_plant(plant)
    if pt and pt.pk not in location_plant_ids:
        location_plant_ids.append(pt.pk)
    if location_plant_ids:
        for loc in PunchLocation.objects.filter(
            tenant_id=tenant_id,
            plant_id__in=location_plant_ids,
            is_active=True,
        ).only("latitude", "longitude", "radius_m", "name"):
            points.append((float(loc.latitude), float(loc.longitude), loc.radius_m, loc.name))

    ttl = int(getattr(settings, "HRIS_GEO_CACHE_TTL", 300))
    cache.set(cache_key, points, ttl)
    return points


def validate_punch_location(employee, latitude, longitude) -> None:
    """Raise GeoFenceError if coordinates outside all allowed locations."""
    points = _points_for_employee(employee)
    if not points:
        return

    if latitude is None or longitude is None:
        raise GeoFenceError("Koordinat GPS wajib untuk absensi mobile.")

    nearest_label = ""
    nearest_radius = 0
    nearest_dist = float("inf")
    for lat, lng, radius, label in points:
        dist = _haversine_m(latitude, longitude, lat, lng)
        if dist <= radius:
            return
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_label = label
            nearest_radius = radius

    if nearest_label:
        raise GeoFenceError(
            "Anda berada di luar area absen yang diizinkan. "
            f"Lokasi terdekat: {nearest_label} (~{int(nearest_dist)} m, "
            f"radius {nearest_radius} m)."
        )
    raise GeoFenceError("Anda berada di luar area absen yang diizinkan.")
