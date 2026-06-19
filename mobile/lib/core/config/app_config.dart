abstract final class AppConfig {
  static const apiPathSuffix = '/api/v1';

  /// Backend publik PT BPS — dipakai release APK.
  static const productionBaseUrl = 'http://148.230.98.125:8080$apiPathSuffix';

  /// Dev lokal (Chrome/emulator di mesin yang sama dengan runserver).
  static const localDevBaseUrl = 'http://127.0.0.1:8000$apiPathSuffix';

  /// Override saat build: flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1
  static String get defaultBaseUrl {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return normalizeApiBaseUrl(override);
    // Emulator, Chrome, dan APK release memakai backend publik yang sama.
    return productionBaseUrl;
  }

  /// Normalisasi input user: `http://148.230.98.125:8080` → `.../api/v1`
  static String normalizeApiBaseUrl(String input) {
    var url = input.trim();
    if (url.isEmpty) return defaultBaseUrl;
    url = url.replaceAll(RegExp(r'/+$'), '');
    if (url.endsWith(apiPathSuffix)) return url;
    if (url.endsWith('/api')) return '$url/v1';
    return '$url$apiPathSuffix';
  }
}
