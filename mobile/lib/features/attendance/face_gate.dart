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
      return 'Wajah terdeteksi. Tekan Submit.';
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
    final smiling = values
        .any((value) => value != null && value >= smileProbabilityThreshold);
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

/// Submit is allowed as soon as a face is in frame. A smile is not required.
bool faceGateReady(FaceGateStatus status) =>
    status == FaceGateStatus.face || status == FaceGateStatus.smiling;

/// On-device face detector. Frames are dropped while a read is in flight.
class FaceStreamSession {
  FaceStreamSession()
      : _detector = FaceDetector(
          options: FaceDetectorOptions(
            enableClassification: true,
            enableLandmarks: false,
            enableContours: false,
            enableTracking: false,
            performanceMode: FaceDetectorMode.accurate,
            minFaceSize: 0.1,
          ),
        );

  final FaceDetector _detector;
  final FaceGateTracker _tracker = FaceGateTracker();
  final FaceRotationSearch _rotation = FaceRotationSearch();
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
      final status =
          _tracker.update(faces.map((face) => face.smilingProbability));
      _rotation.note(status);
      return status;
    } catch (_) {
      _rotation.note(null);
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
    final rotation = _rotation.current(
      fallback:
          _rotationFor(camera: camera, deviceOrientation: deviceOrientation),
    );
    if (rotation == null) return null;

    if (Platform.isAndroid) {
      final nv21 = _androidNv21(image);
      if (nv21 == null) return null;
      return InputImage.fromBytes(
        bytes: nv21.bytes,
        metadata: InputImageMetadata(
          size: Size(nv21.width.toDouble(), nv21.height.toDouble()),
          rotation: rotation,
          format: InputImageFormat.nv21,
          bytesPerRow: nv21.width,
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
  const _Nv21Frame(this.bytes, this.width, this.height);

  final Uint8List bytes;
  final int width;
  final int height;
}

/// Tries the next quarter-turn when a clear frame still has no face.
class FaceRotationSearch {
  int? _degrees;
  int _misses = 0;
  bool _locked = false;

  InputImageRotation? current({required InputImageRotation? fallback}) {
    final initial = _degrees ?? fallback?.rawValue;
    if (initial == null) return null;
    _degrees ??= initial;
    return InputImageRotationValue.fromRawValue(_degrees!);
  }

  void note(FaceGateStatus? status) {
    if (_locked || _degrees == null) return;
    if (status == FaceGateStatus.face || status == FaceGateStatus.smiling) {
      _locked = true;
      _misses = 0;
      return;
    }
    _misses += 1;
    if (_misses < 3) return;
    _misses = 0;
    _degrees = (_degrees! + 90) % 360;
  }
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
  if (compensation == null) {
    return InputImageRotationValue.fromRawValue(camera.sensorOrientation);
  }
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

/// ML Kit only accepts a tight NV21 buffer whose row width equals the frame width.
Uint8List? compactNv21({
  required Uint8List bytes,
  required int width,
  required int height,
  required int bytesPerRow,
}) {
  if (width <= 0 || height <= 0 || height.isOdd || width.isOdd) return null;
  final tightSize = width * height * 3 ~/ 2;
  final stride = bytesPerRow < width ? width : bytesPerRow;
  if (bytes.length == tightSize && stride == width) {
    return Uint8List.fromList(bytes);
  }
  final uvOffset = height * stride;
  final uvRows = height ~/ 2;
  if (uvOffset + uvRows * stride > bytes.length && bytes.length < tightSize)
    return null;
  if (bytes.length < tightSize && uvOffset + width > bytes.length) return null;

  final out = Uint8List(tightSize);
  var dst = 0;
  for (var row = 0; row < height; row++) {
    final start = row * stride;
    if (start + width > bytes.length) return null;
    out.setRange(dst, dst + width, bytes, start);
    dst += width;
  }
  for (var row = 0; row < uvRows; row++) {
    final start = uvOffset + row * stride;
    if (start + width > bytes.length) return null;
    out.setRange(dst, dst + width, bytes, start);
    dst += width;
  }
  return out;
}

_Nv21Frame? _packNv21(CameraImage image) {
  final width = image.width.isOdd ? image.width - 1 : image.width;
  final height = image.height.isOdd ? image.height - 1 : image.height;
  if (width <= 0 || height <= 0) return null;

  if (image.planes.length == 1) {
    final plane = image.planes.first;
    final bytes = compactNv21(
      bytes: plane.bytes,
      width: width,
      height: height,
      bytesPerRow: plane.bytesPerRow,
    );
    if (bytes == null) return null;
    return _Nv21Frame(bytes, width, height);
  }
  if (image.planes.length < 3) return null;

  final yPlane = image.planes[0];
  final uPlane = image.planes[1];
  final vPlane = image.planes[2];
  final ySize = width * height;
  final out = Uint8List(ySize + (ySize ~/ 2));

  if (!_copyRows(out, 0, yPlane.bytes,
      width: width, height: height, stride: yPlane.bytesPerRow)) {
    return null;
  }

  final uvHeight = height ~/ 2;
  final uvWidth = width ~/ 2;
  final uPixel = uPlane.bytesPerPixel ?? 1;
  final vPixel = vPlane.bytesPerPixel ?? 1;
  var offset = ySize;
  for (var row = 0; row < uvHeight; row++) {
    for (var col = 0; col < uvWidth; col++) {
      final uIndex = _sampleIndex(
          uPlane.bytes.length, row, col, uPlane.bytesPerRow, uPixel, uvWidth);
      final vIndex = _sampleIndex(
          vPlane.bytes.length, row, col, vPlane.bytesPerRow, vPixel, uvWidth);
      if (uIndex == null || vIndex == null) return null;
      out[offset++] = vPlane.bytes[vIndex];
      out[offset++] = uPlane.bytes[uIndex];
    }
  }
  return _Nv21Frame(out, width, height);
}

bool _copyRows(
  Uint8List out,
  int offset,
  Uint8List bytes, {
  required int width,
  required int height,
  required int stride,
}) {
  final packed = stride < width || offset + width * height > out.length;
  final rowStride = packed ? width : stride;
  if (height * rowStride > bytes.length && width * height > bytes.length)
    return false;
  var dst = offset;
  for (var row = 0; row < height; row++) {
    final start = row * rowStride;
    if (start + width > bytes.length) {
      if (rowStride == width) return false;
      return _copyRows(out, offset, bytes,
          width: width, height: height, stride: width);
    }
    out.setRange(dst, dst + width, bytes, start);
    dst += width;
  }
  return true;
}

int? _sampleIndex(int length, int row, int col, int rowStride, int pixelStride,
    int tightWidth) {
  final stride = rowStride < pixelStride ? pixelStride : rowStride;
  final strided = row * stride + col * pixelStride;
  if (strided >= 0 && strided < length) return strided;
  final tight = (row * tightWidth + col) * pixelStride;
  if (tight >= 0 && tight < length) return tight;
  return null;
}
