import 'package:flutter/material.dart';

/// Palet China modern — merah, emas & dark gold luxury.
abstract final class AppColors {
  // Brand China
  static const chinaRed = Color(0xFFDE2910);
  static const chinaRedDark = Color(0xFFB91C1C);
  static const chinaRedLight = Color(0xFFFFEBEB);

  static const chinaGold = Color(0xFFF5C518);
  static const chinaGoldDark = Color(0xFFD4A017);
  static const chinaGoldLight = Color(0xFFFFF8E1);

  // Dark gold — aksen premium
  static const darkGold = Color(0xFF8B6914);
  static const darkGoldRich = Color(0xFF5C4A1E);
  static const darkGoldLight = Color(0xFFF5EDD6);
  static const darkGoldMuted = Color(0xFFE8DCC4);

  // Surfaces (tema cerah)
  static const bg = Color(0xFFF7F5F0);
  static const bgElevated = Color(0xFFFFFFFF);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceHover = Color(0xFFFAFAF8);

  static const border = Color(0xFFE8E4DC);
  static const borderStrong = Color(0xFFD4CFC4);

  static const text = Color(0xFF1F2937);
  static const textMuted = Color(0xFF6B7280);
  static const textDim = Color(0xFF9CA3AF);

  // Brand aliases
  static const accent = chinaRed;
  static const accentHover = chinaRedDark;
  static const accentGlow = Color(0x33DE2910);
  static const accentSoft = chinaRedLight;
  static const accentBorder = Color(0x66DE2910);

  static const cyan = darkGold;
  static const cyanDim = darkGoldLight;

  static const success = Color(0xFF059669);
  static const successDim = Color(0xFFECFDF5);

  static const danger = Color(0xFFDC2626);
  static const dangerDim = Color(0xFFFEF2F2);

  static const warning = darkGold;
  static const warningDim = darkGoldLight;

  static const info = Color(0xFF2563EB);
  static const infoDim = Color(0xFFEFF6FF);

  static const sidebarGradientTop = chinaRed;
  static const sidebarGradientBottom = chinaRedDark;

  static const textPrimary = text;
  static const textSecondary = textMuted;
  static const error = danger;
  static const errorSoft = dangerDim;
  static const surfaceMuted = Color(0xFFF3F0EA);
  static const navBar = surface;
  static const steel700 = textMuted;
  static const steel500 = textDim;
  static const steel300 = textDim;
  static const infoSoft = infoDim;
  static const successSoft = successDim;
  static const warningSoft = darkGoldLight;

  static const onPrimary = Color(0xFFFFFFFF);
  static const onGold = Color(0xFF422006);
  static const onDarkGold = Color(0xFFFFFDF7);

  static const cardShadow = Color(0x12000000);

  static const headerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [chinaRed, chinaRedDark],
  );

  static const goldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFF5C518), darkGold],
  );

  static const darkGoldGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [darkGold, darkGoldRich],
  );

  static const premiumGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [chinaRedDark, darkGoldRich],
  );
}
