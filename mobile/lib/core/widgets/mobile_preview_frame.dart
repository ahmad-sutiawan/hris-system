import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Membingkai UI mobile saat dijalankan di Chrome agar tampilan menyerupai HP.
class MobilePreviewFrame extends StatelessWidget {
  const MobilePreviewFrame({super.key, required this.child});

  final Widget child;

  static const _phoneWidth = 430.0;
  static const _phoneHeight = 932.0;

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb) return child;

    return ColoredBox(
      color: const Color(0xFFEDE8DF),
      child: Center(
        child: Container(
          width: _phoneWidth,
          height: _phoneHeight,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: AppColors.bg,
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: AppColors.borderStrong, width: 1),
            boxShadow: [
              BoxShadow(
                color: AppColors.chinaRed.withValues(alpha: 0.12),
                blurRadius: 40,
                offset: const Offset(0, 20),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}
