import 'package:flutter/material.dart';

abstract final class AppColors {
  static const bgDeep = Color(0xFF070A0F);
  static const bgBase = Color(0xFF0B1017);
  static const bgElevated = Color(0xFF121A24);
  static const bgPanel = Color(0xFF182230);

  static const border = Color(0xFF2A3644);
  static const borderBright = Color(0xFF3D5066);

  static const accent = Color(0xFFFF8A00);
  static const accentGlow = Color(0xFFFFB347);
  static const cyan = Color(0xFF00E5FF);
  static const cyanDim = Color(0xFF0097A7);

  static const textPrimary = Color(0xFFE8EEF4);
  static const textSecondary = Color(0xFF8B99A8);
  static const textMuted = Color(0xFF5C6B7A);

  static const success = Color(0xFF00C853);
  static const warning = Color(0xFFFFB300);
  static const error = Color(0xFFFF5252);
  static const info = Color(0xFF448AFF);

  static const gradientHero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF141E2B), Color(0xFF0B1017), Color(0xFF101820)],
  );

  static const gradientAccent = LinearGradient(
    colors: [Color(0xFFFF8A00), Color(0xFFFF6B00)],
  );

  static const gradientCyan = LinearGradient(
    colors: [Color(0xFF00E5FF), Color(0xFF0097A7)],
  );
}
