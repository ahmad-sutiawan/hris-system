abstract final class AppConfig {
  /// Android emulator → host machine localhost
  static const defaultBaseUrl = 'http://10.0.2.2:8000/api/v1';

  /// iOS simulator / macOS desktop
  static const iosBaseUrl = 'http://127.0.0.1:8000/api/v1';

  static String baseUrl = defaultBaseUrl;
}
