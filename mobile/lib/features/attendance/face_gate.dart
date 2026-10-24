import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

enum FaceGateStatus { noFace, face, smiling }

const faceGateInterval = Duration(milliseconds: 250);
const smileProbabilityThreshold = 0.7;
const stableSmileReads = 2;

String faceGateMessage(FaceGateStatus status) {
  switch (status) {
    case FaceGateStatus.noFace:
      return 'Wajah tidak terdeteksi. Arahkan wajah ke kamera.';
    case FaceGateStatus.face:
      return 'Tersenyum untuk mengambil foto.';
    case FaceGateStatus.smiling:
      return 'Wajah siap.';
  }
}

/// Counts consecutive smiling reads so the banner does not flicker.
class FaceGateTracker {
  int _smileStreak = 0;

  FaceGateStatus update(Iterable<double?> smileProbabilities) {
    final values = smileProbabilities.toList(growable: false);
    if (values.isEmpty) {
      _smileStreak = 0;
      return FaceGateStatus.noFace;
    }
    final smiling = values.any((value) => value != null && value >= smileProbabilityThreshold);
    if (smiling) {
      _smileStreak += 1;
    } else {
      _smileStreak = 0;
    }
    if (_smileStreak >= stableSmileReads) return FaceGateStatus.smiling;
    return FaceGateStatus.face;
  }

  void reset() => _smileStreak = 0;
}

/// On-device face detector. Frames are dropped while a read is in flight.
class FaceStreamSession {
  FaceStreamSession()
      : _detector = FaceDetector(
          options: FaceDetectorOptions(
            enableClassification: true,
            enableLandmarks: false,
            enableContours: false,
            enableTracking: true,
            performanceMode: FaceDetectorMode.fast,
            minFaceSize: 0.2,
          ),
        );

  final FaceDetector _detector;
  final FaceGateTracker _tracker = FaceGateTracker();
  DateTime? _lastRun;
  bool _busy = false;
  bool _closed = false;

  bool tryAcquire() {
    if (_closed || _busy) return false;
    final now = DateTime.now();
    final last = _lastRun;
    if (last != null && now.difference(last) < faceGateInterval) return false;
    _busy = true;
    _lastRun = now;
    return true;
  }

  void release() => _busy = false;

  Future<FaceGateStatus?> analyze(InputImage image) async {
    try {
      if (_closed) return null;
      final faces = await _detector.processImage(image);
      if (_closed) return null;
      return _tracker.update(faces.map((face) => face.smilingProbability));
    } catch (_) {
      return null;
    } finally {
      _busy = false;
    }
  }

  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    _tracker.reset();
    await _detector.close();
  }

  InputImage? inputImageFromCamera({
    required CameraImage image,
    required CameraDescription camera,
    required DeviceOrientation deviceOrientation,
  }) {
    final rotation = _rotationFor(camera: camera, deviceOrientation: deviceOrientation);
    if (rotation == null) return null;

    if (Platform.isAndroid) {
      final nv21 = _androidNv21(image);
      if (nv21 == null) return null;
      return InputImage.fromBytes(
        bytes: nv21.bytes,
        metadata: InputImageMetadata(
          size: Size(image.width.toDouble(), image.height.toDouble()),
          rotation: rotation,
          format: InputImageFormat.nv21,
          bytesPerRow: nv21.bytesPerRow,
        ),
      );
    }

    if (image.planes.length != 1) return null;
    final plane = image.planes.first;
    return InputImage.fromBytes(
      bytes: Uint8List.fromList(plane.bytes),
      metadata: InputImageMetadata(
        size: Size(image.width.toDouble(), image.height.toDouble()),
        rotation: rotation,
        format: InputImageFormat.bgra8888,
        bytesPerRow: plane.bytesPerRow,
      ),
    );
  }
}

class _Nv21Frame {
  const _Nv21Frame(this.bytes, this.bytesPerRow);

  final Uint8List bytes;
  final int bytesPerRow;
}

const _deviceOrientations = <DeviceOrientation, int>{
  DeviceOrientation.portraitUp: 0,
  DeviceOrientation.landscapeLeft: 90,
  DeviceOrientation.portraitDown: 180,
  DeviceOrientation.landscapeRight: 270,
};

InputImageRotation? _rotationFor({
  required CameraDescription camera,
  required DeviceOrientation deviceOrientation,
}) {
  if (Platform.isIOS) {
    return InputImageRotationValue.fromRawValue(camera.sensorOrientation);
  }
  final compensation = _deviceOrientations[deviceOrientation];
  if (compensation == null) return null;
  final adjusted = camera.lensDirection == CameraLensDirection.front
      ? (camera.sensorOrientation + compensation) % 360
      : (camera.sensorOrientation - compensation + 360) % 360;
  return InputImageRotationValue.fromRawValue(adjusted);
}

_Nv21Frame? _androidNv21(CameraImage image) {
  try {
    return _packNv21(image);
  } catch (_) {
    return null;
  }
}

_Nv21Frame? _packNv21(CameraImage image) {
  if (image.planes.length == 1) {
    final plane = image.planes.first;
    return _Nv21Frame(Uint8List.fromList(plane.bytes), plane.bytesPerRow);
  }
  if (image.planes.length < 3) return null;

  final width = image.width;
  final height = image.height;
  final yPlane = image.planes[0];
  final uPlane = image.planes[1];
  final vPlane = image.planes[2];
  final ySize = width * height;
  final out = Uint8List(ySize + (ySize ~/ 2));

  var offset = 0;
  for (var row = 0; row < height; row++) {
    final rowStart = row * yPlane.bytesPerRow;
    out.setRange(offset, offset + width, yPlane.bytes, rowStart);
    offset += width;
  }

  final uvHeight = height ~/ 2;
  final uvWidth = width ~/ 2;
  final uStride = uPlane.bytesPerPixel ?? 1;
  final vStride = vPlane.bytesPerPixel ?? 1;
  for (var row = 0; row < uvHeight; row++) {
    for (var col = 0; col < uvWidth; col++) {
      final uIndex = row * uPlane.bytesPerRow + col * uStride;
      final vIndex = row * vPlane.bytesPerRow + col * vStride;
      if (vIndex >= vPlane.bytes.length || uIndex >= uPlane.bytes.length) return null;
      out[offset++] = vPlane.bytes[vIndex];
      out[offset++] = uPlane.bytes[uIndex];
    }
  }
  return _Nv21Frame(out, width);
}
