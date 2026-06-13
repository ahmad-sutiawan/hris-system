import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/config/app_config.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/brand_logo.dart';
import '../../core/widgets/hris_widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _serverCtrl = TextEditingController();
  bool _obscure = true;
  bool _showServer = false;
  bool _submitting = false;
  String? _validationError;
  String _activeServer = '';

  @override
  void initState() {
    super.initState();
    _loadServerUrl();
  }

  Future<void> _loadServerUrl() async {
    final url = await ref.read(apiClientProvider).loadBaseUrl();
    if (mounted) {
      setState(() {
        _activeServer = url.replaceAll(AppConfig.apiPathSuffix, '');
        _serverCtrl.text = _activeServer;
      });
    }
  }

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    _serverCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;

    final username = _userCtrl.text.trim();
    final password = _passCtrl.text;
    if (username.isEmpty || password.isEmpty) {
      setState(() => _validationError = 'Username dan password wajib diisi.');
      return;
    }
    setState(() => _validationError = null);

    setState(() => _submitting = true);
    try {
      await ref.read(authProvider.notifier).login(
            username,
            password,
            serverUrl: _showServer ? _serverCtrl.text.trim() : null,
          );
      if (!mounted) return;
      final auth = ref.read(authProvider);
      if (auth.isAuthenticated) {
        context.go('/home');
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
        await _loadServerUrl();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (prev, next) {
      final err = next.error;
      if (err != null && err != prev?.error && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(err),
            backgroundColor: AppColors.danger,
            duration: const Duration(seconds: 6),
          ),
        );
      }
    });

    return HrisPageBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: HrisSafeBody(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Hero brand — sama web login
                    ClipRect(
                      child: Stack(
                        children: [
                          Image.asset(
                            'assets/images/login-hero.jpg',
                            height: 160,
                            width: double.infinity,
                            fit: BoxFit.cover,
                          ),
                          Container(
                            height: 160,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [
                                  AppColors.bg.withValues(alpha: 0.35),
                                  AppColors.bg.withValues(alpha: 0.92),
                                ],
                              ),
                            ),
                          ),
                          SizedBox(
                            height: 160,
                            child: Center(
                              child: const BrandLogo(
                                size: BrandLogoSize.panel,
                                showHrisLabel: true,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.only(top: 20),
                      decoration: const BoxDecoration(
                        border: Border(
                          top: BorderSide(color: AppColors.accentBorder, width: 2),
                        ),
                      ),
                      child: Column(
                        children: [
                          Text(
                            'Transformasi Digital HR',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: AppColors.text,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Dukung Pertumbuhan Perusahaan.',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 14,
                              color: AppColors.textMuted,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 28),
                    HrisCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Center(child: BrandLogo(size: BrandLogoSize.sidebar)),
                          const SizedBox(height: 20),
                          Text(
                            'Masuk',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                              color: AppColors.text,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Gunakan akun yang diberikan HR atau IT',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 13,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 24),
                          TextField(
                            controller: _userCtrl,
                            style: const TextStyle(color: AppColors.text),
                            decoration: const InputDecoration(
                              labelText: 'Username',
                              prefixIcon: Icon(Icons.person_outline),
                            ),
                            textInputAction: TextInputAction.next,
                            autocorrect: false,
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _passCtrl,
                            obscureText: _obscure,
                            style: const TextStyle(color: AppColors.text),
                            decoration: InputDecoration(
                              labelText: 'Password',
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscure
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                ),
                                onPressed: () =>
                                    setState(() => _obscure = !_obscure),
                              ),
                            ),
                            onSubmitted: (_) => _submit(),
                          ),
                          const SizedBox(height: 8),
                          TextButton.icon(
                            onPressed: () => setState(() => _showServer = !_showServer),
                            icon: Icon(
                              _showServer ? Icons.expand_less : Icons.settings_outlined,
                              size: 18,
                            ),
                            label: Text(_showServer ? 'Sembunyikan server' : 'Pengaturan server'),
                          ),
                          if (!_showServer && _activeServer.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              'Server: $_activeServer',
                              style: const TextStyle(
                                color: AppColors.textDim,
                                fontSize: 11,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                          if (_showServer) ...[
                            TextField(
                              controller: _serverCtrl,
                              style: const TextStyle(color: AppColors.text),
                              decoration: const InputDecoration(
                                labelText: 'Alamat server HRIS',
                                hintText: 'http://148.230.98.125:8080',
                                prefixIcon: Icon(Icons.dns_outlined),
                                helperText:
                                    'Default: server production. Ubah hanya untuk development lokal.',
                              ),
                              keyboardType: TextInputType.url,
                              autocorrect: false,
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (_validationError != null || auth.error != null) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: AppColors.dangerDim,
                                border: Border.all(
                                  color: AppColors.danger.withValues(alpha: 0.35),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Login gagal',
                                    style: TextStyle(
                                      color: AppColors.danger,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    _validationError ?? auth.error!,
                                    style: const TextStyle(color: AppColors.danger),
                                  ),
                                  if (_activeServer.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    Text(
                                      'Server: $_activeServer',
                                      style: TextStyle(
                                        color: AppColors.danger.withValues(alpha: 0.85),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                          const SizedBox(height: 20),
                          PrimaryButton(
                            label: 'Masuk',
                            loading: _submitting,
                            onPressed: _submit,
                          ),
                          const SizedBox(height: 16),
                          Container(
                            padding: const EdgeInsets.only(top: 16),
                            decoration: const BoxDecoration(
                              border: Border(top: BorderSide(color: AppColors.border)),
                            ),
                            child: const Text(
                              'Lupa akun atau password? Hubungi tim HR plant Anda.',
                              style: TextStyle(
                                color: AppColors.textDim,
                                fontSize: 12,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
