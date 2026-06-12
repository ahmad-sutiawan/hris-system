import 'package:flutter/foundation.dart';

abstract final class AppConfig {
  static const apiPathSuffix = '/api/v1';

  /// Emulator Android → host PC
  static const emulatorBaseUrl = 'http://10.0.2.2:8000$apiPathSuffix';

  /// Web / iOS simulator
  static const localBaseUrl = 'http://127.0.0.1:8000$apiPathSuffix';

  static String get defaultBaseUrl {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return override;

    if (kIsWeb) return localBaseUrl;
    if (defaultTargetPlatform == TargetPlatform.android) {
      return emulatorBaseUrl;
    }
    return localBaseUrl;
  }

  /// Normalisasi input user: `http://192.168.0.5:8000` → `http://192.168.0.5:8000/api/v1`
  static String normalizeApiBaseUrl(String input) {
    var url = input.trim();
    if (url.isEmpty) return defaultBaseUrl;
    url = url.replaceAll(RegExp(r'/+$'), '');
    if (url.endsWith(apiPathSuffix)) return url;
    if (url.endsWith('/api')) return '$url/v1';
    return '$url$apiPathSuffix';
  }
}
