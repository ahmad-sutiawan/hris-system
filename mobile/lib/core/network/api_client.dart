import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';

import '../config/app_config.dart';
import 'api_exception.dart';

class ApiClient {
  ApiClient({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage(),
        _dio = Dio(
          BaseOptions(
            baseUrl: AppConfig.defaultBaseUrl,
            connectTimeout: const Duration(seconds: 20),
            receiveTimeout: const Duration(seconds: 30),
            headers: {'Content-Type': 'application/json'},
          ),
        ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.read(key: _accessKey);
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401 &&
              error.requestOptions.extra['retried'] != true) {
            final refreshed = await _refreshToken();
            if (refreshed) {
              final opts = error.requestOptions;
              opts.extra['retried'] = true;
              opts.headers['Authorization'] =
                  'Bearer ${await _storage.read(key: _accessKey)}';
              handler.resolve(await _dio.fetch(opts));
              return;
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _baseUrlKey = 'api_base_url';

  final Dio _dio;
  final FlutterSecureStorage _storage;

  Dio get dio => _dio;
  String get baseUrl => _dio.options.baseUrl;

  Future<void> init() async {
    final stored = await _storage.read(key: _baseUrlKey);
    if (stored != null && stored.isNotEmpty) {
      _dio.options.baseUrl = stored;
    }
  }

  Future<void> setBaseUrl(String url) async {
    final normalized = AppConfig.normalizeApiBaseUrl(url);
    await _storage.write(key: _baseUrlKey, value: normalized);
    _dio.options.baseUrl = normalized;
  }

  Future<String> loadBaseUrl() async {
    await init();
    return _dio.options.baseUrl;
  }

  Future<void> setTokens({required String access, required String refresh}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Future<bool> hasToken() async {
    final token = await _storage.read(key: _accessKey);
    return token != null && token.isNotEmpty;
  }

  Future<bool> _refreshToken() async {
    final refresh = await _storage.read(key: _refreshKey);
    if (refresh == null) return false;
    try {
      final res = await Dio(BaseOptions(baseUrl: _dio.options.baseUrl)).post(
        '/auth/token/refresh/',
        data: {'refresh': refresh},
      );
      final access = res.data['access'] as String;
      await _storage.write(key: _accessKey, value: access);
      return true;
    } catch (_) {
      await clearTokens();
      return false;
    }
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final res = await _dio.post(
        '/auth/token/',
        data: {'username': username, 'password': password},
      );
      final data = res.data as Map<String, dynamic>;
      await setTokens(
        access: data['access'] as String,
        refresh: data['refresh'] as String,
      );
      return data;
    } on DioException catch (e) {
      throw _wrap(e);
    }
  }

  Future<Map<String, dynamic>> getMe() async => _getMap('/auth/me/');

  Future<Map<String, dynamic>> getDashboard() async => _getMap('/mobile/dashboard/');

  Future<Map<String, dynamic>> getProfile() async => _getMap('/mobile/profile/');

  Future<List<dynamic>> getPaginated(String path, {Map<String, dynamic>? query}) async {
    final data = await _getDynamic(path, query: query);
    if (data is Map && data['results'] is List) {
      return data['results'] as List;
    }
    if (data is List) return data;
    return [];
  }

  /// Fetch all pages for list endpoints (e.g. timesheet history).
  Future<List<dynamic>> getPaginatedAll(
    String path, {
    Map<String, dynamic>? query,
    int pageSize = 60,
  }) async {
    final merged = <dynamic>[];
    var page = 1;
    while (true) {
      final params = {
        ...?query,
        'page': page,
        'page_size': pageSize,
      };
      final data = await _getDynamic(path, query: params);
      if (data is! Map || data['results'] is! List) {
        if (data is List) return data;
        break;
      }
      final batch = data['results'] as List;
      merged.addAll(batch);
      if (data['next'] == null || batch.isEmpty) break;
      page += 1;
      if (page > 20) break;
    }
    return merged;
  }

  /// Resolve media URL from API path or absolute URL using configured server base.
  Future<String> resolveMediaUrl(String? urlOrPath) async {
    if (urlOrPath == null || urlOrPath.isEmpty) return '';
    if (urlOrPath.startsWith('http://') || urlOrPath.startsWith('https://')) {
      return urlOrPath;
    }
    final apiBase = await loadBaseUrl();
    final origin = apiBase.replaceAll(AppConfig.apiPathSuffix, '');
    if (urlOrPath.startsWith('/')) return '$origin$urlOrPath';
    return '$origin/$urlOrPath';
  }

  Future<Map<String, dynamic>> get(String path, {Map<String, dynamic>? query}) {
    return _getMap(path, query: query);
  }

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    try {
      final res = await _dio.post(path, data: body);
      if (res.data is Map<String, dynamic>) {
        return res.data as Map<String, dynamic>;
      }
      return {'data': res.data};
    } on DioException catch (e) {
      throw _wrap(e);
    }
  }

  Future<void> postEmpty(String path, {Map<String, dynamic>? body}) async {
    try {
      await _dio.post(path, data: body);
    } on DioException catch (e) {
      throw _wrap(e);
    }
  }

  Future<Map<String, dynamic>> clockIn(
    String photoBase64, {
    double? latitude,
    double? longitude,
    String? notes,
  }) {
    return post('/attendance/clock_in/', body: {
      'photo': photoBase64,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
    });
  }

  Future<Map<String, dynamic>> clockOut(
    String photoBase64, {
    double? latitude,
    double? longitude,
    String? notes,
  }) {
    return post('/attendance/clock_out/', body: {
      'photo': photoBase64,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
    });
  }

  Future<File> downloadPdf(int payslipId, String filename) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$filename');
      await _dio.download('/payslips/$payslipId/pdf/', file.path);
      return file;
    } on DioException catch (e) {
      throw _wrap(e);
    }
  }

  Future<dynamic> _getDynamic(String path, {Map<String, dynamic>? query}) async {
    try {
      final res = await _dio.get(path, queryParameters: query);
      return res.data;
    } on DioException catch (e) {
      throw _wrap(e);
    }
  }

  Future<Map<String, dynamic>> _getMap(String path, {Map<String, dynamic>? query}) async {
    final data = await _getDynamic(path, query: query);
    if (data is Map<String, dynamic>) return data;
    return {'data': data};
  }

  ApiException _wrap(DioException e) {
    final status = e.response?.statusCode;
    final body = e.response?.data;
    if (body is Map && body['detail'] != null) {
      return ApiException('${body['detail']}', statusCode: status);
    }
    if (body is Map) {
      final first = body.values.first;
      if (first is List && first.isNotEmpty) {
        return ApiException('${first.first}', statusCode: status);
      }
    }
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return ApiException(
        'Tidak bisa terhubung ke server. Periksa alamat server dan WiFi.',
        statusCode: status,
      );
    }
    return ApiException(
      e.message ?? 'Koneksi gagal. Periksa server HRIS.',
      statusCode: status,
    );
  }

  static String imageToBase64DataUrl(List<int> bytes) {
    return 'data:image/jpeg;base64,${base64Encode(bytes)}';
  }
}

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
