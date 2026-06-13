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
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      employee: employee ?? this.employee,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._api) : super(const AuthState(isLoading: true)) {
    _bootstrap();
  }

  final ApiClient _api;

  Future<void> _bootstrap() async {
    await _api.init();
    final hasToken = await _api.hasToken();
    if (!hasToken) {
      state = const AuthState(isLoading: false, isAuthenticated: false);
      return;
    }
    await _loadMe();
  }

  Future<void> login(String username, String password, {String? serverUrl}) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      if (serverUrl != null && serverUrl.trim().isNotEmpty) {
        await _api.setBaseUrl(serverUrl);
      }
      await _api.login(username, password);
      await _loadMe();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        error: e.toString(),
      );
    }
  }

  Future<void> _loadMe() async {
    try {
      final me = await _api.getMe();
      state = AuthState(
        isLoading: false,
        isAuthenticated: true,
        user: me,
        employee: me['employee'] as Map<String, dynamic>?,
      );
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        await _api.clearTokens();
        state = const AuthState(isLoading: false, isAuthenticated: false);
        return;
      }
      final hasToken = await _api.hasToken();
      state = AuthState(
        isLoading: false,
        isAuthenticated: hasToken,
        user: state.user,
        employee: state.employee,
        error: e.message,
      );
    } catch (e) {
      final hasToken = await _api.hasToken();
      state = AuthState(
        isLoading: false,
        isAuthenticated: hasToken,
        user: state.user,
        employee: state.employee,
        error: e.toString(),
      );
    }
  }

  Future<void> logout() async {
    await _api.clearTokens();
    state = const AuthState(isLoading: false, isAuthenticated: false);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(apiClientProvider));
});
