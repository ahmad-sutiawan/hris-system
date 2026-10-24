import 'package:flutter_test/flutter_test.dart';
import 'package:hris_mobile/features/attendance/map_radius.dart';
import 'package:latlong2/latlong.dart';

void main() {
  test('circle ring stays on the requested radius and closes', () {
    const center = LatLng(-6.16514, 106.33905);
    final ring = circleRing(center, 150);

    expect(ring.length, greaterThan(12));
    expect(ring.first.latitude, closeTo(ring.last.latitude, 0.0000001));
    expect(ring.first.longitude, closeTo(ring.last.longitude, 0.0000001));
    for (final point in ring) {
      final distance = haversineMeters(
        center.latitude,
        center.longitude,
        point.latitude,
        point.longitude,
      );
      expect(distance, closeTo(150, 2));
    }
  });

  test('a missing radius falls back to 150 meters', () {
    const center = LatLng(-6.16514, 106.33905);
    final ring = circleRing(center, 0, steps: 16);
    final distance = haversineMeters(
      center.latitude,
      center.longitude,
      ring[4].latitude,
      ring[4].longitude,
    );
    expect(distance, closeTo(fallbackAttendanceRadiusM.toDouble(), 2));
  });
}
