import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../home/home_screen.dart';

class PunchScreen extends ConsumerStatefulWidget {
  const PunchScreen({super.key});

  @override
  ConsumerState<PunchScreen> createState() => _PunchScreenState();
}

class _PunchScreenState extends ConsumerState<PunchScreen> {
  final _picker = ImagePicker();
  bool _loading = false;
  Uint8List? _photoBytes;

  bool get _isClockOut {
    final action = GoRouterState.of(context).uri.queryParameters['action'];
    return action == 'out';
  }

  Future<void> _capture() async {
    final photo = await _picker.pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: CameraDevice.front,
      imageQuality: 70,
      maxWidth: 1024,
    );
    if (photo != null) {
      final bytes = await photo.readAsBytes();
      setState(() {
        _photoBytes = bytes;
      });
    }
  }

  Future<void> _submit() async {
    if (_photoBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Foto selfie wajib untuk absensi.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      final encoded = ApiClient.imageToBase64DataUrl(_photoBytes!);
      final api = ref.read(apiClientProvider);
      if (_isClockOut) {
        await api.clockOut(encoded);
      } else {
        await api.clockIn(encoded);
      }
      ref.invalidate(dashboardProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_isClockOut ? 'Absen pulang berhasil.' : 'Absen masuk berhasil.'),
          ),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = _isClockOut ? 'Absen Pulang' : 'Absen Masuk';

    return HrisPageBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: Text(title)),
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HrisCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Ambil foto selfie',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Pastikan wajah terlihat jelas untuk verifikasi absensi.',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
                    ),
                    const SizedBox(height: 16),
                    AspectRatio(
                      aspectRatio: 4 / 5,
                      child: Container(
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: AppColors.surfaceMuted,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.border),
                          image: _photoBytes != null
                              ? DecorationImage(
                                  image: MemoryImage(_photoBytes!),
                                  fit: BoxFit.cover,
                                )
                              : null,
                        ),
                        child: _photoBytes == null
                            ? Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.camera_alt_outlined, size: 56, color: AppColors.steel300),
                                  const SizedBox(height: 8),
                                  const Text('Belum ada foto', style: TextStyle(color: AppColors.textMuted)),
                                ],
                              )
                            : null,
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (_photoBytes == null)
                      PrimaryButton(
                        label: 'Buka Kamera',
                        icon: Icons.camera_alt,
                        onPressed: _capture,
                      )
                    else ...[
                      PrimaryButton(
                        label: 'Ambil Ulang',
                        secondary: true,
                        onPressed: _capture,
                      ),
                      const SizedBox(height: 10),
                      PrimaryButton(
                        label: _isClockOut ? 'Konfirmasi Pulang' : 'Konfirmasi Masuk',
                        loading: _loading,
                        onPressed: _submit,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
