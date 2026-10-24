import 'dart:math' as math;

import 'package:latlong2/latlong.dart';

const fallbackAttendanceRadiusM = 150;

/// Closed ring around [center], about [radiusM] meters from it.
List<LatLng> circleRing(LatLng center, int radiusM, {int steps = 72}) {
  final safeRadius = radiusM <= 0 ? fallbackAttendanceRadiusM : radiusM;
  final safeSteps = steps < 12 ? 12 : steps;
  const earth = 6378137.0;
  final lat = center.latitude * math.pi / 180;
  final lng = center.longitude * math.pi / 180;
  final angular = safeRadius / earth;
  final ring = <LatLng>[];
  for (var i = 0; i <= safeSteps; i++) {
    final bearing = 2 * math.pi * i / safeSteps;
    final lat2 = math.asin(
      math.sin(lat) * math.cos(angular) +
          math.cos(lat) * math.sin(angular) * math.cos(bearing),
    );
    final lng2 = lng +
        math.atan2(
          math.sin(bearing) * math.sin(angular) * math.cos(lat),
          math.cos(angular) - math.sin(lat) * math.sin(lat2),
        );
    ring.add(LatLng(lat2 * 180 / math.pi, lng2 * 180 / math.pi));
  }
  return ring;
}

double haversineMeters(double lat1, double lon1, double lat2, double lon2) {
  const earth = 6371000.0;
  final p1 = lat1 * math.pi / 180;
  final p2 = lat2 * math.pi / 180;
  final dLat = (lat2 - lat1) * math.pi / 180;
  final dLon = (lon2 - lon1) * math.pi / 180;
  final a = math.pow(math.sin(dLat / 2), 2) +
      math.cos(p1) * math.cos(p2) * math.pow(math.sin(dLon / 2), 2);
  return 2 * earth * math.asin(math.sqrt(a.toDouble()));
}
