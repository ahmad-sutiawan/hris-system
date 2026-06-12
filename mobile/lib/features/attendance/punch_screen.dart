import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_background.dart';
import '../../core/widgets/industrial_widgets.dart';
import '../home/home_screen.dart';

class PunchScreen extends ConsumerStatefulWidget {
  const PunchScreen({super.key});

  @override
  ConsumerState<PunchScreen> createState() => _PunchScreenState();
}

class _PunchScreenState extends ConsumerState<PunchScreen> {
  final _picker = ImagePicker();
  bool _loading = false;
  XFile? _photo;
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
        _photo = photo;
        _photoBytes = bytes;
      });
    }
  }

  Future<void> _submit() async {
    if (_photo == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selfie wajib untuk absensi.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      final bytes = await _photo!.readAsBytes();
      final encoded = ApiClient.imageToBase64DataUrl(bytes);
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
            content: Text(_isClockOut ? 'Clock out berhasil.' : 'Clock in berhasil.'),
          ),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = _isClockOut ? 'CLOCK OUT' : 'CLOCK IN';

    return IndustrialBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: Text(title)),
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              IndustrialCard(
                accentColor: _isClockOut ? AppColors.cyan : AppColors.accent,
                child: Column(
                  children: [
                    AspectRatio(
                      aspectRatio: 3 / 4,
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.bgPanel,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppColors.border),
                          image: _photoBytes != null
                              ? DecorationImage(
                                  image: MemoryImage(_photoBytes!),
                                  fit: BoxFit.cover,
                                )
                              : null,
                        ),
                        child: _photoBytes == null
                            ? const Center(
                                child: Icon(
                                  Icons.camera_front_outlined,
                                  size: 64,
                                  color: AppColors.textMuted,
                                ),
                              )
                            : null,
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (_photoBytes == null)
                      NeonButton(
                        label: 'Ambil Selfie',
                        icon: Icons.camera_alt,
                        onPressed: _capture,
                      )
                    else ...[
                      NeonButton(
                        label: 'Ulangi Foto',
                        secondary: true,
                        onPressed: _capture,
                      ),
                      const SizedBox(height: 12),
                      NeonButton(
                        label: _isClockOut ? 'Konfirmasi Pulang' : 'Konfirmasi Masuk',
                        loading: _loading,
                        onPressed: _submit,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Foto selfie wajib untuk verifikasi absensi sesuai kebijakan perusahaan.',
                style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
