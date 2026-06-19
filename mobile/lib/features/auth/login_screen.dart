import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/config/app_config.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/animated_interactions.dart';
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
  bool _submitting = false;
  bool _showServer = false;
  String? _validationError;
  String _serverUrl = AppConfig.defaultBaseUrl;
  bool? _serverReachable;

  @override
  void initState() {
    super.initState();
    _resolveServerUrl();
  }

  Future<void> _resolveServerUrl() async {
    final client = ref.read(apiClientProvider);
    final url = await client.resolveBaseUrl();
    final reachable = await client.probeHealth(url);
    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      _serverReachable = reachable;
      _serverCtrl.text = url.replaceAll(AppConfig.apiPathSuffix, '');
    });
  }

  Future<void> _saveServerUrl() async {
    final raw = _serverCtrl.text.trim();
    if (raw.isEmpty) return;
    final normalized = AppConfig.normalizeApiBaseUrl(raw);
    await ref.read(apiClientProvider).setBaseUrl(normalized);
    final reachable = await ref.read(apiClientProvider).probeHealth(normalized);
    if (!mounted) return;
    setState(() {
      _serverUrl = normalized;
      _serverReachable = reachable;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Server disimpan: $normalized'),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  Future<void> _resetServerUrl() async {
    await ref.read(apiClientProvider).resetBaseUrl();
    await _resolveServerUrl();
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

    final nik = _userCtrl.text.trim();
    final employeeId = _passCtrl.text.trim();
    if (nik.isEmpty || employeeId.isEmpty) {
      setState(() => _validationError = 'NIK dan Employee ID wajib diisi.');
      return;
    }
    setState(() => _validationError = null);

    setState(() => _submitting = true);
    try {
      await ref.read(apiClientProvider).resolveBaseUrl();
      await ref
          .read(authProvider.notifier)
          .login(nik, employeeId)
          .timeout(const Duration(seconds: 45));
      if (!mounted) return;
      final auth = ref.read(authProvider);
      if (auth.isAuthenticated) {
        context.go('/home');
      }
    } on TimeoutException {
      if (mounted) {
        setState(() {
          _validationError =
              'Login timeout. Periksa koneksi internet dan server HRIS.';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
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
                    FadeSlideIn(
                      index: 0,
                      child: HrisCard(
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
                            'Masuk dengan NIK dan Employee ID Anda',
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
                              labelText: 'NIK',
                              hintText: 'Nomor Induk Kependudukan',
                              prefixIcon: Icon(Icons.badge_outlined),
                            ),
                            textInputAction: TextInputAction.next,
                            autocorrect: false,
                            keyboardType: TextInputType.number,
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _passCtrl,
                            style: const TextStyle(color: AppColors.text),
                            decoration: const InputDecoration(
                              labelText: 'Employee ID',
                              hintText: 'Nomor Employee ID',
                              prefixIcon: Icon(Icons.fingerprint_outlined),
                            ),
                            textInputAction: TextInputAction.done,
                            autocorrect: false,
                            onSubmitted: (_) => _submit(),
                          ),
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
                            child: Column(
                              children: [
                                if (!kReleaseMode) ...[
                                  InkWell(
                                    onTap: () => setState(() => _showServer = !_showServer),
                                    child: Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Icon(
                                          _showServer ? Icons.expand_less : Icons.settings_outlined,
                                          size: 16,
                                          color: AppColors.textMuted,
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          'Pengaturan server',
                                          style: GoogleFonts.plusJakartaSans(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            color: AppColors.textMuted,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  if (_showServer) ...[
                                    const SizedBox(height: 10),
                                    Text(
                                      _serverReachable == true
                                          ? 'Terhubung: $_serverUrl'
                                          : _serverReachable == false
                                              ? 'Server tidak terjangkau. Dev lokal: http://127.0.0.1:8000'
                                              : 'Mencari backend…',
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: _serverReachable == true
                                            ? AppColors.success
                                            : AppColors.textDim,
                                      ),
                                      textAlign: TextAlign.center,
                                    ),
                                    const SizedBox(height: 8),
                                    TextField(
                                      controller: _serverCtrl,
                                      decoration: const InputDecoration(
                                        labelText: 'URL server',
                                        hintText: 'http://148.230.98.125:8080',
                                        prefixIcon: Icon(Icons.dns_outlined),
                                      ),
                                      autocorrect: false,
                                      keyboardType: TextInputType.url,
                                    ),
                                    const SizedBox(height: 8),
                                    OutlinedButton(
                                      onPressed: _saveServerUrl,
                                      child: const Text('Simpan server'),
                                    ),
                                    TextButton(
                                      onPressed: _resetServerUrl,
                                      child: const Text('Reset ke default'),
                                    ),
                                    const Padding(
                                      padding: EdgeInsets.only(top: 8),
                                      child: Text(
                                        'Backend default: 148.230.98.125:8080 (dev & release pakai server yang sama)',
                                        style: TextStyle(fontSize: 11, color: AppColors.textDim),
                                        textAlign: TextAlign.center,
                                      ),
                                    ),
                                  ],
                                  const SizedBox(height: 12),
                                ],
                                const Text(
                                  'Lupa akun atau password? Hubungi tim HR plant Anda.',
                                  style: TextStyle(
                                    color: AppColors.textDim,
                                    fontSize: 12,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
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
