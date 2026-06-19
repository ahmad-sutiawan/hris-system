import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';

/// Logo PT BPS — sama dengan `static/img/main-logo.png` di web.
class BrandLogo extends StatelessWidget {
  const BrandLogo({
    super.key,
    this.size = BrandLogoSize.panel,
    this.showHrisLabel = false,
  });

  final BrandLogoSize size;
  final bool showHrisLabel;

  double get _width {
    switch (size) {
      case BrandLogoSize.sidebar:
        return 112;
      case BrandLogoSize.panel:
        return 136;
      case BrandLogoSize.hero:
        return 180;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset(
          'assets/images/main-logo.png',
          width: _width,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
        ),
        if (showHrisLabel) ...[
          const SizedBox(height: 10),
          Text(
            'HRIS',
            style: GoogleFonts.plusJakartaSans(
              fontSize: size == BrandLogoSize.hero ? 24 : 18,
              fontWeight: FontWeight.w600,
              letterSpacing: 8,
              color: AppColors.text.withValues(alpha: 0.92),
            ),
          ),
        ],
      ],
    );
  }
}

enum BrandLogoSize { sidebar, panel, hero }
