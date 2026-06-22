import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
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
  static const _legacyBaseUrlKey = 'api_base_url';

  final Dio _dio;
  final FlutterSecureStorage _storage;
  final Map<String, Uint8List> _mediaCache = {};
  final Map<String, Future<Uint8List?>> _mediaInflight = {};

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

  Future<String> resolveBaseUrl() async {
    _dio.options.baseUrl = AppConfig.defaultBaseUrl;
    // Hapus override lama dari versi sebelumnya (UI pengaturan server).
    await _deleteStorage(_legacyBaseUrlKey);
    return _dio.options.baseUrl;
  }

  Future<void> init() async {
    await resolveBaseUrl();
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

  Future<void> logout() async {
    final refresh = await _readStorage(_refreshKey);
    if (refresh != null && refresh.isNotEmpty) {
      try {
        await _dio.post('/auth/logout/', data: {'refresh': refresh});
      } catch (_) {
        // Token blacklist best-effort; tetap hapus lokal.
      }
    }
    await clearTokens();
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

  /// Resolve media URL — pakai proxy API (/api/v1/media/...) agar CORS + JWT jalan di web.
  Future<String> resolveMediaUrl(String? urlOrPath) async {
    if (urlOrPath == null || urlOrPath.isEmpty) return '';
    if (urlOrPath.startsWith('data:image')) return urlOrPath;

    final apiBase = await loadBaseUrl();
    final mediaPath = _mediaRelativePath(urlOrPath);
    if (mediaPath.isEmpty) return '';

    final uri = Uri.parse('$apiBase/media/$mediaPath');
    return uri.toString();
  }

  /// Unduh bytes media dengan token auth (untuk Image.memory di web & native).
  Future<Uint8List?> fetchMediaBytes(String? urlOrPath) async {
    if (urlOrPath == null || urlOrPath.isEmpty) return null;
    if (urlOrPath.startsWith('data:image')) {
      final comma = urlOrPath.indexOf(',');
      if (comma < 0) return null;
      return base64Decode(urlOrPath.substring(comma + 1));
    }

    final mediaPath = _mediaRelativePath(urlOrPath);
    if (mediaPath.isEmpty) return null;

    final query = _mediaQuery(urlOrPath);
    final requestPath = query == null ? '/media/$mediaPath' : '/media/$mediaPath?$query';
    final cacheKey = requestPath;

    final cached = _mediaCache[cacheKey];
    if (cached != null) return cached;

    final inflight = _mediaInflight[cacheKey];
    if (inflight != null) return inflight;

    final future = _downloadMediaBytes(mediaPath, query, requestPath);
    _mediaInflight[cacheKey] = future;
    try {
      final bytes = await future;
      if (bytes != null && bytes.isNotEmpty) {
        _mediaCache[cacheKey] = bytes;
      }
      return bytes;
    } finally {
      _mediaInflight.remove(cacheKey);
    }
  }

  Future<Uint8List?> _downloadMediaBytes(
    String mediaPath,
    String? query,
    String requestPath,
  ) async {
    try {
      final res = await _dio.get<List<int>>(
        requestPath,
        options: Options(responseType: ResponseType.bytes),
      );
      final data = res.data;
      if (data == null || data.isEmpty) return null;
      return Uint8List.fromList(data);
    } on DioException {
      return _fetchMediaBytesDirect(mediaPath, query);
    }
  }

  Future<Uint8List?> _fetchMediaBytesDirect(String mediaPath, String? query) async {
    try {
      final apiBase = await loadBaseUrl();
      final origin = apiBase.replaceAll(AppConfig.apiPathSuffix, '');
      final suffix = query == null ? '' : '?$query';
      final url = '$origin/media/$mediaPath$suffix';
      final token = await _readStorage(_accessKey);
      final client = Dio(
        BaseOptions(
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 30),
          headers: {
            if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
          },
        ),
      );
      final res = await client.get<List<int>>(
        url,
        options: Options(responseType: ResponseType.bytes),
      );
      final data = res.data;
      if (data == null || data.isEmpty) return null;
      return Uint8List.fromList(data);
    } on DioException {
      return null;
    }
  }

  String _mediaRelativePath(String urlOrPath) {
    late Uri parsed;
    if (urlOrPath.startsWith('http://') || urlOrPath.startsWith('https://')) {
      parsed = Uri.parse(urlOrPath);
    } else {
      parsed = Uri.parse(urlOrPath.startsWith('/') ? urlOrPath : '/$urlOrPath');
    }

    var path = parsed.path;
    if (path.startsWith('/api/v1/media/')) {
      return path.substring('/api/v1/media/'.length);
    }
    if (path.startsWith('/media/')) {
      return path.substring('/media/'.length);
    }
    if (path.startsWith('/')) {
      path = path.substring(1);
    }
    return path;
  }

  String? _mediaQuery(String urlOrPath) {
    if (!urlOrPath.startsWith('http://') && !urlOrPath.startsWith('https://')) {
      return null;
    }
    final query = Uri.parse(urlOrPath).query;
    return query.isEmpty ? null : query;
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
      return ApiException(
        'Tidak bisa terhubung ke server HRIS. Periksa koneksi internet Anda.',
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
