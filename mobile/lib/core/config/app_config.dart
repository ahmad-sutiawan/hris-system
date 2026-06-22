abstract final class AppConfig {
  static const apiPathSuffix = '/api/v1';

  /// Backend publik PT BPS — HTTPS via hris.besibps.com
  static const productionBaseUrl = 'https://hris.besibps.com$apiPathSuffix';

  /// Override hanya saat build khusus: --dart-define=API_BASE_URL=...
  static String get defaultBaseUrl {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return normalizeApiBaseUrl(override);
    return productionBaseUrl;
  }

  static String normalizeApiBaseUrl(String input) {
    var url = input.trim();
    if (url.isEmpty) return defaultBaseUrl;
    url = url.replaceAll(RegExp(r'/+$'), '');
    if (url.endsWith(apiPathSuffix)) return url;
    if (url.endsWith('/api')) return '$url/v1';
    return '$url$apiPathSuffix';
  }
}
