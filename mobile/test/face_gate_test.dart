import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
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
    expect(faceGateMessage(FaceGateStatus.face),
        'Wajah terdeteksi. Tekan Submit.');
    expect(faceGateMessage(FaceGateStatus.smiling), 'Wajah siap.');
  });

  test('a detected face is enough to submit', () {
    expect(faceGateReady(FaceGateStatus.noFace), isFalse);
    expect(faceGateReady(FaceGateStatus.face), isTrue);
    expect(faceGateReady(FaceGateStatus.smiling), isTrue);
  });

  test('padded NV21 rows are packed to the frame width', () {
    const width = 4;
    const height = 4;
    const stride = 8;
    final bytes = Uint8List(height * stride + (height ~/ 2) * stride);
    for (var row = 0; row < height; row++) {
      for (var col = 0; col < width; col++) {
        bytes[row * stride + col] = col + 1;
      }
    }
    final uvOffset = height * stride;
    for (var row = 0; row < height ~/ 2; row++) {
      for (var col = 0; col < width; col++) {
        bytes[uvOffset + row * stride + col] = 10 + col;
      }
    }

    final packed = compactNv21(
      bytes: bytes,
      width: width,
      height: height,
      bytesPerRow: stride,
    );

    expect(packed, isNotNull);
    expect(packed!.length, width * height * 3 ~/ 2);
    expect(packed[0], 1);
    expect(packed[width * height], 10);
  });

  test('an already tight NV21 buffer keeps its pixels', () {
    const width = 4;
    const height = 4;
    final bytes = Uint8List(width * height * 3 ~/ 2);
    bytes[0] = 7;
    bytes[width * height] = 9;

    final packed = compactNv21(
      bytes: bytes,
      width: width,
      height: height,
      bytesPerRow: width,
    );

    expect(packed, isNotNull);
    expect(packed!.length, bytes.length);
    expect(packed[0], 7);
    expect(packed[width * height], 9);
  });

  test('a short NV21 buffer is rejected', () {
    final packed = compactNv21(
      bytes: Uint8List(8),
      width: 4,
      height: 4,
      bytesPerRow: 8,
    );
    expect(packed, isNull);
  });

  test('odd NV21 dimensions are rejected', () {
    final packed = compactNv21(
      bytes: Uint8List(32),
      width: 5,
      height: 4,
      bytesPerRow: 5,
    );
    expect(packed, isNull);
  });

  test('extra bytes after the luminance plane are not treated as pixels', () {
    const width = 4;
    const height = 4;
    final bytes = Uint8List(width * height + 12);
    bytes[0] = 3;
    bytes[width * height - 1] = 4;
    bytes[width * height] = 99;

    final packed = compactNv21(
      bytes: bytes,
      width: width,
      height: height,
      bytesPerRow: width,
    );

    expect(packed, isNotNull);
    expect(packed![0], 3);
    expect(packed[width * height - 1], 4);
    expect(packed[width * height], 99);
    expect(packed.length, width * height * 3 ~/ 2);
  });

  test('rotation turns only after three misses, then stays on a face', () {
    final search = FaceRotationSearch();
    expect(
      search.current(fallback: InputImageRotation.rotation270deg),
      InputImageRotation.rotation270deg,
    );
    search.note(FaceGateStatus.noFace);
    search.note(null);
    expect(
      search.current(fallback: InputImageRotation.rotation270deg),
      InputImageRotation.rotation270deg,
    );
    search.note(FaceGateStatus.noFace);
    expect(
      search.current(fallback: InputImageRotation.rotation270deg),
      InputImageRotation.rotation0deg,
    );
    search.note(FaceGateStatus.face);
    search.note(null);
    search.note(null);
    search.note(null);
    expect(
      search.current(fallback: InputImageRotation.rotation0deg),
      InputImageRotation.rotation0deg,
    );
  });

  test('detector options and camera format match the working attendance build',
      () {
    expect(faceDetectorOptions.enableClassification, isTrue);
    expect(faceDetectorOptions.minFaceSize, 0.1);
    expect(faceDetectorOptions.performanceMode, FaceDetectorMode.accurate);
    expect(androidAnalysisFormats, [
      ImageFormatGroup.nv21,
      ImageFormatGroup.yuv420,
    ]);
  });

  test('a phone YUV frame keeps luminance and interleaved chroma', () {
    const width = 4;
    const height = 4;
    final y = Uint8List(width * height)..fillRange(0, width * height, 5);
    y[0] = 8;
    final u = Uint8List.fromList([11, 0, 12, 0, 13, 0, 14, 0]);
    final v = Uint8List.fromList([21, 0, 22, 0, 23, 0, 24, 0]);
    final image = CameraImage.fromPlatformData(<dynamic, dynamic>{
      'format': 35,
      'width': width,
      'height': height,
      'planes': [
        {'bytes': y, 'bytesPerRow': width, 'bytesPerPixel': 1},
        {'bytes': u, 'bytesPerRow': width, 'bytesPerPixel': 2},
        {'bytes': v, 'bytesPerRow': width, 'bytesPerPixel': 2},
      ],
    });

    final packed = packAndroidFrameForTest(image);

    expect(packed, isNotNull);
    expect(packed!.length, width * height * 3 ~/ 2);
    expect(packed[0], 8);
    expect(packed.sublist(width * height), [21, 11, 22, 12, 23, 13, 24, 14]);
  });

  test('a phone frame with a missing chroma sample is dropped', () {
    const width = 4;
    const height = 4;
    final image = CameraImage.fromPlatformData(<dynamic, dynamic>{
      'format': 35,
      'width': width,
      'height': height,
      'planes': [
        {
          'bytes': Uint8List(width * height),
          'bytesPerRow': width,
          'bytesPerPixel': 1,
        },
        {
          'bytes': Uint8List.fromList([1]),
          'bytesPerRow': width,
          'bytesPerPixel': 2,
        },
        {
          'bytes': Uint8List(width * height ~/ 2),
          'bytesPerRow': width,
          'bytesPerPixel': 2,
        },
      ],
    });

    expect(packAndroidFrameForTest(image), isNull);
  });

  test('two camera planes are not sent to the detector', () {
    final image = CameraImage.fromPlatformData(<dynamic, dynamic>{
      'format': 35,
      'width': 4,
      'height': 4,
      'planes': [
        {'bytes': Uint8List(16), 'bytesPerRow': 4, 'bytesPerPixel': 1},
        {'bytes': Uint8List(8), 'bytesPerRow': 4, 'bytesPerPixel': 1},
      ],
    });

    expect(packAndroidFrameForTest(image), isNull);
  });
}
