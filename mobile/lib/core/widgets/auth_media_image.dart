import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/api_client.dart';
import '../theme/app_colors.dart';

/// Loads protected media via authenticated API (works on Flutter web + native).
class AuthMediaImage extends ConsumerWidget {
  const AuthMediaImage({
    super.key,
    required this.url,
    this.fit = BoxFit.cover,
    this.loading,
    this.error,
  });

  final String? url;
  final BoxFit fit;
  final Widget? loading;
  final Widget? error;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (url == null || url!.isEmpty) {
      return error ??
          const Center(
            child: Icon(Icons.no_photography_outlined, color: AppColors.textDim, size: 28),
          );
    }

    return FutureBuilder<Uint8List?>(
      future: ref.read(apiClientProvider).fetchMediaBytes(url),
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return loading ??
              const Center(child: CircularProgressIndicator(strokeWidth: 2));
        }
        final bytes = snap.data;
        if (bytes == null || bytes.isEmpty) {
          return error ??
              const Center(
                child: Icon(Icons.broken_image_outlined, color: AppColors.textDim),
              );
        }
        return Image.memory(bytes, fit: fit);
      },
    );
  }
}
