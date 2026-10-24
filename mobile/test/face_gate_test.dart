import 'package:flutter_test/flutter_test.dart';
import 'package:hris_mobile/features/attendance/face_gate.dart';

void main() {
  test('no face resets the smile streak', () {
    final tracker = FaceGateTracker();
    expect(tracker.update(const [0.9]), FaceGateStatus.face);
    expect(tracker.update(const []), FaceGateStatus.noFace);
    expect(tracker.update(const [0.95]), FaceGateStatus.face);
  });

  test('smile is ready only after two consecutive high readings', () {
    final tracker = FaceGateTracker();
    expect(tracker.update(const [0.8]), FaceGateStatus.face);
    expect(tracker.update(const [0.71]), FaceGateStatus.smiling);
    expect(tracker.update(const [0.2]), FaceGateStatus.face);
    expect(tracker.update(const [0.9]), FaceGateStatus.face);
  });

  test('a face without a smile probability still counts as a face', () {
    final tracker = FaceGateTracker();
    expect(tracker.update(const [null]), FaceGateStatus.face);
    expect(tracker.update(const [null]), FaceGateStatus.face);
  });

  test('a low smile score stays locked', () {
    final tracker = FaceGateTracker();
    for (var i = 0; i < 8; i++) {
      expect(tracker.update(const [0.2]), FaceGateStatus.face);
    }
  });

  test('banner copy follows the gate status', () {
    expect(
      faceGateMessage(FaceGateStatus.noFace),
      'Wajah tidak terdeteksi. Arahkan wajah ke kamera.',
    );
    expect(faceGateMessage(FaceGateStatus.face), 'Tersenyum untuk mengambil foto.');
    expect(faceGateMessage(FaceGateStatus.smiling), 'Wajah siap.');
  });
}
