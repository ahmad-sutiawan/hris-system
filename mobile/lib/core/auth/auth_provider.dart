import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/api_client.dart';
import '../network/api_exception.dart';

class AuthState {
  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.employee,
    this.error,
  });

  final bool isLoading;
  final bool isAuthenticated;
  final Map<String, dynamic>? user;
  final Map<String, dynamic>? employee;
  final String? error;

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    Map<String, dynamic>? user,
    Map<String, dynamic>? employee,
    String? error,
    bool clearError = false,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      employee: employee ?? this.employee,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._api) : super(const AuthState(isLoading: true)) {
    _bootstrap();
  }

  final ApiClient _api;

  Future<void> _bootstrap() async {
    try {
      await _api.init();
      final hasToken = await _api.hasToken();
      if (!hasToken) {
        state = const AuthState(isLoading: false, isAuthenticated: false);
        return;
      }
      await _loadMe();
    } catch (_) {
      state = const AuthState(isLoading: false, isAuthenticated: false);
    } finally {
      if (state.isLoading) {
        state = state.copyWith(isLoading: false);
      }
    }
  }

  Future<void> login(String username, String password) async {
    state = state.copyWith(clearError: true);
    try {
      await _api.login(username, password).timeout(const Duration(seconds: 30));
      final ok = await _loadMe().timeout(const Duration(seconds: 30));
      if (!ok) {
        await _api.clearTokens();
        state = state.copyWith(
          isAuthenticated: false,
          error: state.error ??
              'Login gagal. Periksa username, password, dan alamat server.',
        );
      }
    } on ApiException catch (e) {
      state = state.copyWith(
        isAuthenticated: false,
        error: e.message,
      );
    } on TimeoutException {
      state = state.copyWith(
        isAuthenticated: false,
        error: 'Login timeout. Periksa koneksi internet dan server HRIS.',
      );
    } catch (e) {
      state = state.copyWith(
        isAuthenticated: false,
        error: 'Terjadi kesalahan: $e',
      );
    }
  }

  Future<bool> _loadMe() async {
    try {
      final me = await _api.getMe();
      state = AuthState(
        isLoading: false,
        isAuthenticated: true,
        user: me,
        employee: me['employee'] as Map<String, dynamic>?,
      );
      return true;
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        await _api.clearTokens();
        state = AuthState(
          isLoading: false,
          isAuthenticated: false,
          error: e.message.isNotEmpty
              ? e.message
              : 'Username atau password salah.',
        );
        return false;
      }
      state = AuthState(
        isLoading: false,
        isAuthenticated: false,
        error: e.message,
      );
      return false;
    } catch (e) {
      state = AuthState(
        isLoading: false,
        isAuthenticated: false,
        error: 'Gagal memuat profil: $e',
      );
      return false;
    }
  }

  Future<void> logout() async {
    await _api.logout();
    state = const AuthState(isLoading: false, isAuthenticated: false);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(apiClientProvider));
});
