import 'package:flutter/material.dart';

/// Palet identik dengan `static/css/hris.css` (:root).
abstract final class AppColors {
  static const bg = Color(0xFF0A0C10);
  static const bgElevated = Color(0xFF11151C);
  static const surface = Color(0xFF161B24);
  static const surfaceHover = Color(0xFF1C2330);

  static const border = Color(0x2E94A3B8); // rgba(148,163,184,0.18)
  static const borderStrong = Color(0x5294A3B8); // rgba(148,163,184,0.32)

  static const text = Color(0xFFF3F6FB);
  static const textMuted = Color(0xFFC4CEDA);
  static const textDim = Color(0xFFA3B0C2);

  static const accent = Color(0xFFF59E0B);
  static const accentHover = Color(0xFFFBBF24);
  static const accentGlow = Color(0x40F59E0B); // rgba(245,158,11,0.25)

  static const cyan = Color(0xFF22D3EE);
  static const cyanDim = Color(0x2622D3EE);

  static const success = Color(0xFF34D399);
  static const successDim = Color(0x1F34D399);

  static const danger = Color(0xFFFB7185);
  static const dangerDim = Color(0x1FFB7185);

  static const warning = Color(0xFFFBBF24);
  static const warningDim = Color(0x1FFBBF24);

  static const info = Color(0xFF60A5FA);
  static const infoDim = Color(0x1F60A5FA);

  static const sidebarGradientTop = Color(0xFF0E1219);
  static const sidebarGradientBottom = Color(0xFF0A0C10);

  // Alias untuk kompatibilitas widget lama
  static const textPrimary = text;
  static const textSecondary = textMuted;
  static const error = danger;
  static const errorSoft = dangerDim;
  static const accentSoft = Color(0x1FF59E0B);
  static const accentBorder = Color(0xA6F59E0B);
  static const surfaceMuted = surfaceHover;
  static const navBar = bgElevated;
  static const steel700 = textMuted;
  static const steel500 = textDim;
  static const steel300 = textDim;
  static const infoSoft = infoDim;
  static const successSoft = successDim;
  static const warningSoft = warningDim;
}
