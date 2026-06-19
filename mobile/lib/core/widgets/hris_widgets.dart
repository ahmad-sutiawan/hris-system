import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';
import 'aurora_background.dart';

/// Wrapper SafeArea standar — top selalu aman; bottom bisa dimatikan jika ada bottom nav.
class HrisSafeBody extends StatelessWidget {
  const HrisSafeBody({
    super.key,
    required this.child,
    this.bottom = true,
  });

  final Widget child;
  final bool bottom;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: bottom,
      child: child,
    );
  }
}

/// Latar aurora animasi — gradien lembut + orbs blur fluid.
class HrisPageBackground extends StatelessWidget {
  const HrisPageBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AuroraBackground(child: child);
  }
}

/// Scaffold standar — latar aurora + AppBar glass opsional.
class HrisScaffold extends StatelessWidget {
  const HrisScaffold({
    super.key,
    required this.body,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
    this.extendBodyBehindAppBar = false,
    this.withBackground = true,
  });

  final Widget body;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;
  final bool extendBodyBehindAppBar;
  final bool withBackground;

  @override
  Widget build(BuildContext context) {
    final scaffold = Scaffold(
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      appBar: appBar,
      body: body,
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: bottomNavigationBar,
    );

    if (!withBackground) {
      return ColoredBox(
        color: Colors.transparent,
        child: scaffold,
      );
    }
    return HrisPageBackground(child: scaffold);
  }
}

/// AppBar glass aurora — blur halus + highlight atas.
PreferredSizeWidget hrisAppBar({
  required String title,
  List<Widget>? actions,
  Widget? leading,
  bool centerTitle = false,
}) {
  return PreferredSize(
    preferredSize: const Size.fromHeight(kToolbarHeight),
    child: ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: AppColors.glassSurface.withValues(alpha: 0.68),
            border: Border(
              bottom: BorderSide(color: AppColors.glassBorderMuted),
            ),
          ),
          child: AppBar(
            title: Text(title),
            actions: actions,
            leading: leading,
            centerTitle: centerTitle,
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            scrolledUnderElevation: 0,
          ),
        ),
      ),
    ),
  );
}

class HrisCard extends StatelessWidget {
  const HrisCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.accentColor,
    this.onTap,
    this.showAccentBar = false,
  });

  final Widget child;
  final EdgeInsets padding;
  final Color? accentColor;
  final VoidCallback? onTap;
  final bool showAccentBar;

  @override
  Widget build(BuildContext context) {
    final accent = accentColor ?? AppColors.accent;

    Widget card = AuroraGlass(
      padding: EdgeInsets.zero,
      borderRadius: 20,
      onTap: onTap,
      child: Stack(
        children: [
          if (showAccentBar)
            Positioned(
              left: 0,
              top: 14,
              bottom: 14,
              child: Container(
                width: 4,
                decoration: BoxDecoration(
                  gradient: AppColors.auroraButtonGradient,
                  borderRadius: BorderRadius.circular(4),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withValues(alpha: 0.35),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
            ),
          Padding(padding: padding, child: child),
        ],
      ),
    );

    return card;
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  final String title;
  final String? subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          width: 4,
          height: 20,
          decoration: BoxDecoration(
            gradient: AppColors.goldGradient,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.4,
                  color: AppColors.textMuted,
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: const TextStyle(
                    color: AppColors.textDim,
                    fontSize: 13,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

String statusLabel(String status) {
  switch (status.toLowerCase()) {
    case 'approved':
      return 'Disetujui';
    case 'pending':
      return 'Menunggu';
    case 'rejected':
      return 'Ditolak';
    case 'cancelled':
      return 'Dibatalkan';
    case 'in':
      return 'Sedang kerja';
    case 'out':
      return 'Sudah pulang';
    case 'critical':
      return 'Penting';
    case 'high':
      return 'Tinggi';
    case 'normal':
      return 'Normal';
    case 'low':
      return 'Rendah';
    default:
      return status;
  }
}

class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.status});

  final String status;

  Color get _color {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'in':
        return AppColors.success;
      case 'pending':
        return AppColors.warning;
      case 'rejected':
      case 'out':
        return AppColors.danger;
      case 'cancelled':
        return AppColors.textDim;
      default:
        return AppColors.info;
    }
  }

  Color get _bg {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'in':
        return AppColors.successDim;
      case 'pending':
        return AppColors.warningDim;
      case 'rejected':
      case 'out':
        return AppColors.dangerDim;
      default:
        return AppColors.infoDim;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: _bg.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: _color.withValues(alpha: 0.22)),
      ),
      child: Text(
        statusLabel(status),
        style: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
          color: _color,
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AuroraGlass(
              padding: const EdgeInsets.all(20),
              borderRadius: 24,
              child: Icon(icon, size: 40, color: AppColors.brandPurple.withValues(alpha: 0.45)),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.textMuted,
              ),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle!,
                style: const TextStyle(color: AppColors.textDim, fontSize: 14),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.loading = false,
    this.secondary = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool loading;
  final bool secondary;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    return AuroraButton(
      label: label,
      onPressed: onPressed,
      icon: icon,
      loading: loading,
      secondary: secondary,
      expand: expand,
    );
  }
}

class QuickActionTile extends StatelessWidget {
  const QuickActionTile({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.color,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppColors.accent;
    return AnimatedPressWrapper(
      onTap: onTap,
      child: AuroraGlass(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        borderRadius: 18,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    c.withValues(alpha: 0.18),
                    c.withValues(alpha: 0.06),
                  ],
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: c.withValues(alpha: 0.15),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Icon(icon, color: c, size: 24),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: AppColors.text,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

typedef IndustrialCard = HrisCard;
typedef NeonButton = PrimaryButton;
