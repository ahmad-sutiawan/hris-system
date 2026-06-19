import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

abstract final class AppTheme {
  static const _radius = 16.0;

  static ThemeData get light {
    final textTheme = GoogleFonts.plusJakartaSansTextTheme(
      ThemeData(brightness: Brightness.light).textTheme,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.auroraBgMid,
      colorScheme: const ColorScheme.light(
        primary: AppColors.brandPurple,
        onPrimary: AppColors.onPrimary,
        secondary: AppColors.brandGold,
        onSecondary: AppColors.onGold,
        tertiary: AppColors.brandBlue,
        surface: AppColors.glassSurface,
        onSurface: AppColors.text,
        error: AppColors.danger,
      ),
      dividerColor: AppColors.glassBorderMuted,
      textTheme: textTheme.apply(
        bodyColor: AppColors.text,
        displayColor: AppColors.text,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: AppColors.text,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 17,
          fontWeight: FontWeight.w800,
          color: AppColors.text,
          letterSpacing: -0.3,
        ),
        iconTheme: const IconThemeData(color: AppColors.textMuted),
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardThemeData(
        color: AppColors.glassSurface.withValues(alpha: 0.85),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(_radius),
          side: BorderSide(color: AppColors.glassBorderMuted),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.72),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(_radius),
          borderSide: BorderSide(color: AppColors.border.withValues(alpha: 0.5)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(_radius),
          borderSide: BorderSide(color: AppColors.border.withValues(alpha: 0.45)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(_radius),
          borderSide: const BorderSide(color: AppColors.brandPurple, width: 1.5),
        ),
        labelStyle: const TextStyle(color: AppColors.textMuted, fontSize: 15),
        hintStyle: const TextStyle(color: AppColors.textDim),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.brandPurple,
          foregroundColor: AppColors.onPrimary,
          elevation: 0,
          minimumSize: const Size.fromHeight(52),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_radius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.brandPurple,
          minimumSize: const Size.fromHeight(52),
          side: BorderSide(color: AppColors.brandPurple.withValues(alpha: 0.45)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_radius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: AppColors.brandGold,
        foregroundColor: AppColors.onGold,
        elevation: 4,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.brandNavy,
        contentTextStyle: GoogleFonts.plusJakartaSans(color: Colors.white),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(_radius)),
        ),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: Colors.transparent,
        selectedItemColor: AppColors.brandPurple,
        unselectedItemColor: AppColors.textDim,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
        unselectedLabelStyle: GoogleFonts.plusJakartaSans(fontSize: 11),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.brandPurple,
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: AppColors.brandGold,
        thumbColor: AppColors.brandGold,
        inactiveTrackColor: AppColors.border.withValues(alpha: 0.5),
      ),
    );
  }

  static ThemeData get dark => light;
}
