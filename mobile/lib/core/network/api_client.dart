import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';

import '../config/app_config.dart';
import 'api_exception.dart';

class ApiClient {
  static const _defaultStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  ApiClient({FlutterSecureStorage? storage})
      : _storage = storage ?? _defaultStorage,
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
          final path = options.path;
          final isAuthEndpoint = path.contains('/auth/token');
          if (!isAuthEndpoint) {
            final token = await _readStorage(_accessKey);
            if (token != null && token.isNotEmpty) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final path = error.requestOptions.path;
          if (path.contains('/auth/token')) {
            handler.next(error);
            return;
          }
          if (error.response?.statusCode == 401 &&
              error.requestOptions.extra['retried'] != true) {
            final refreshed = await _refreshToken();
            if (refreshed) {
              final opts = error.requestOptions;
              opts.extra['retried'] = true;
              opts.headers['Authorization'] =
                  'Bearer ${await _readStorage(_accessKey)}';
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

  Future<String?> _readStorage(String key) async {
    try {
      return await _storage.read(key: key).timeout(const Duration(seconds: 8));
    } catch (_) {
      return null;
    }
  }

  Future<void> _writeStorage(String key, String value) async {
    await _storage.write(key: key, value: value).timeout(const Duration(seconds: 8));
  }

  Future<void> _deleteStorage(String key) async {
    try {
      await _storage.delete(key: key).timeout(const Duration(seconds: 8));
    } catch (_) {}
  }

  Future<void> init() async {
    if (kReleaseMode) {
      _dio.options.baseUrl = AppConfig.defaultBaseUrl;
      return;
    }
    final stored = await _readStorage(_baseUrlKey);
    if (stored != null && stored.isNotEmpty) {
      _dio.options.baseUrl = stored;
    }
  }

  Future<void> setBaseUrl(String url) async {
    final normalized = AppConfig.normalizeApiBaseUrl(url);
    await _writeStorage(_baseUrlKey, normalized);
    _dio.options.baseUrl = normalized;
  }

  Future<String> loadBaseUrl() async {
    await init();
    return _dio.options.baseUrl;
  }

  Future<void> setTokens({required String access, required String refresh}) async {
    await _writeStorage(_accessKey, access);
    await _writeStorage(_refreshKey, refresh);
  }

  Future<void> clearTokens() async {
    await _deleteStorage(_accessKey);
    await _deleteStorage(_refreshKey);
  }

  Future<bool> hasToken() async {
    final token = await _readStorage(_accessKey);
    return token != null && token.isNotEmpty;
  }

  Future<bool> _refreshToken() async {
    final refresh = await _readStorage(_refreshKey);
    if (refresh == null) return false;
    try {
      final res = await Dio(BaseOptions(
        baseUrl: _dio.options.baseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 30),
      )).post(
        '/auth/token/refresh/',
        data: {'refresh': refresh},
      );
      final access = res.data['access'] as String;
      await _writeStorage(_accessKey, access);
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
        options: Options(extra: {'skipAuth': true}),
      );
      final data = res.data as Map<String, dynamic>;
      await setTokens(
        access: data['access'] as String,
        refresh: data['refresh'] as String,
      );
      return data;
    } on DioException catch (e) {
      throw _wrap(e);
    } on TimeoutException {
      throw ApiException('Penyimpanan token timeout. Coba lagi.');
    }
  }

  Future<Map<String, dynamic>> getMe() async => _getMap('/auth/me/');

  Future<Map<String, dynamic>> getDashboard() async => _getMap('/mobile/dashboard/');

  Future<Map<String, dynamic>> getProfile() async => _getMap('/mobile/profile/');

  Future<List<dynamic>> getPaginated(String path, {Map<String, dynamic>? query}) async {
    return getPaginatedAll(path, query: query, pageSize: 50);
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

  /// Resolve media URL — selalu pakai origin server app (dengan port benar).
  /// API kadang mengembalikan http://host/media/... tanpa :8080.
  Future<String> resolveMediaUrl(String? urlOrPath) async {
    if (urlOrPath == null || urlOrPath.isEmpty) return '';
    if (urlOrPath.startsWith('data:image')) return urlOrPath;

    final apiBase = await loadBaseUrl();
    final origin = apiBase.replaceAll(AppConfig.apiPathSuffix, '');
    final originUri = Uri.parse(origin);

    final String path;
    if (urlOrPath.startsWith('http://') || urlOrPath.startsWith('https://')) {
      path = Uri.parse(urlOrPath).path;
    } else if (urlOrPath.startsWith('/')) {
      path = urlOrPath;
    } else {
      path = '/$urlOrPath';
    }

    return Uri(
      scheme: originUri.scheme,
      host: originUri.host,
      port: originUri.hasPort ? originUri.port : null,
      path: path,
    ).toString();
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
    final server = _dio.options.baseUrl;

    if (body is Map && body['detail'] != null) {
      return ApiException('${body['detail']}', statusCode: status);
    }
    if (body is Map) {
      for (final entry in body.entries) {
        final val = entry.value;
        if (val is List && val.isNotEmpty) {
          return ApiException('${entry.key}: ${val.first}', statusCode: status);
        }
        if (val is String && val.isNotEmpty) {
          return ApiException('${entry.key}: $val', statusCode: status);
        }
      }
    }
    if (status == 401) {
      return ApiException(
        'Username atau password salah.',
        statusCode: status,
      );
    }
    if (status == 403) {
      return ApiException(
        'Akses ditolak. Akun ini mungkin tidak diizinkan untuk mobile.',
        statusCode: status,
      );
    }
    if (status != null && status >= 500) {
      return ApiException(
        'Server error ($status). Coba lagi beberapa saat.',
        statusCode: status,
      );
    }
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      final hint = kIsWeb
          ? ' Browser memblokir koneksi (CORS). Gunakan backend lokal atau update CORS server.'
          : ' Periksa koneksi internet HP dan pastikan server bisa diakses.';
      return ApiException(
        'Tidak bisa terhubung ke $server.$hint',
        statusCode: status,
      );
    }
    return ApiException(
      e.message ?? 'Koneksi gagal ke $server.',
      statusCode: status,
    );
  }

  static String imageToBase64DataUrl(List<int> bytes) {
    return 'data:image/jpeg;base64,${base64Encode(bytes)}';
  }
}

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
