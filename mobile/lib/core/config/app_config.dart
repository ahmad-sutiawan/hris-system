import 'package:flutter/foundation.dart';

abstract final class AppConfig {
  static const apiPathSuffix = '/api/v1';

  /// Production default — override: flutter build apk --dart-define=API_BASE_URL=https://host/api/v1
  static const productionBaseUrl = 'http://148.230.98.125:8080$apiPathSuffix';

  /// Emulator Android → host PC (Docker nginx default HTTP_PORT=8080)
  static const emulatorBaseUrl = 'http://10.0.2.2:8080$apiPathSuffix';

  /// Web / iOS simulator — Docker: 8080, runserver langsung: ganti via Pengaturan server
  static const localBaseUrl = 'http://127.0.0.1:8080$apiPathSuffix';

  static String get defaultBaseUrl {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return override;

    // APK/IPA release otomatis ke server production
    if (kReleaseMode) return productionBaseUrl;

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
