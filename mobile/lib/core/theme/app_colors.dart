import 'package:flutter/material.dart';

/// Palet brand — purple/blue dominan, gold aksen, orange sekunder.
abstract final class AppColors {
  // Brand core (dari palet user)
  static const brandNavy = Color(0xFF140B6E);
  static const brandPurple = Color(0xFF3428A8);
  static const brandBlue = Color(0xFF3269CC);
  static const brandGold = Color(0xFFFBD02F);
  static const brandGoldDark = Color(0xFFD4A817);
  static const brandGoldLight = Color(0xFFFFF8DC);
  static const brandOrange = Color(0xFFF67E2D);

  // Alias legacy (agar widget lama otomatis ikut tema baru)
  static const chinaRed = brandPurple;
  static const chinaRedDark = brandNavy;
  static const chinaRedLight = Color(0xFFEDE9FF);

  static const chinaGold = brandGold;
  static const chinaGoldDark = brandGoldDark;
  static const chinaGoldLight = brandGoldLight;

  static const darkGold = brandGoldDark;
  static const darkGoldRich = brandNavy;
  static const darkGoldLight = brandGoldLight;
  static const darkGoldMuted = Color(0xFFF5EAB8);

  // Surfaces — nuansa biru dingin
  static const bg = Color(0xFFF3F5FC);
  static const bgElevated = Color(0xFFFFFFFF);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceHover = Color(0xFFF8F9FE);
  static const surfaceMuted = Color(0xFFE8EDF8);

  static const border = Color(0xFFD4DCF0);
  static const borderStrong = Color(0xFFB8C4E8);

  static const text = Color(0xFF140B6E);
  static const textMuted = Color(0xFF5A6490);
  static const textDim = Color(0xFF8B94B8);

  // Brand aliases
  static const accent = brandPurple;
  static const accentHover = brandNavy;
  static const accentGlow = Color(0x333428A8);
  static const accentSoft = chinaRedLight;
  static const accentBorder = Color(0x663428A8);

  static const cyan = brandBlue;
  static const cyanDim = Color(0xFFE8F0FD);

  static const success = Color(0xFF059669);
  static const successDim = Color(0xFFECFDF5);

  static const danger = Color(0xFFDC2626);
  static const dangerDim = Color(0xFFFEF2F2);

  static const warning = brandOrange;
  static const warningDim = Color(0xFFFFF0E6);

  static const info = brandBlue;
  static const infoDim = Color(0xFFE8F0FD);

  static const sidebarGradientTop = brandNavy;
  static const sidebarGradientBottom = brandPurple;

  static const textPrimary = text;
  static const textSecondary = textMuted;
  static const error = danger;
  static const errorSoft = dangerDim;
  static const navBar = surface;
  static const steel700 = textMuted;
  static const steel500 = textDim;
  static const steel300 = textDim;
  static const infoSoft = infoDim;
  static const successSoft = successDim;
  static const warningSoft = brandGoldLight;

  static const onPrimary = Color(0xFFFFFFFF);
  static const onGold = brandNavy;
  static const onDarkGold = brandNavy;

  static const cardShadow = Color(0x14140B6E);

  static const headerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [brandNavy, brandPurple],
  );

  static const headerGradientBlue = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [brandPurple, brandBlue],
  );

  static const goldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [brandGold, brandGoldDark],
  );

  static const darkGoldGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [brandGold, brandGoldDark],
  );

  static const premiumGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [brandNavy, brandBlue],
  );
}
