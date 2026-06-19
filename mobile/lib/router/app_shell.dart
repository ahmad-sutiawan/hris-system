import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/theme/app_colors.dart';
import '../core/widgets/animated_interactions.dart';
import '../core/widgets/hris_widgets.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return HrisPageBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: HrisSafeBody(
          bottom: false,
          child: navigationShell,
        ),
        bottomNavigationBar: _AuroraBottomNav(
          currentIndex: navigationShell.currentIndex,
          onTap: navigationShell.goBranch,
        ),
      ),
    );
  }
}

class _AuroraBottomNav extends StatelessWidget {
  const _AuroraBottomNav({
    required this.currentIndex,
    required this.onTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  static const _centerIndex = 2;
  static const _barHeight = 58.0;
  static const _fabSize = 52.0;
  static const _fabOverhang = 24.0;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return SizedBox(
      height: _barHeight + bottomInset + _fabOverhang,
      child: Stack(
        clipBehavior: Clip.none,
        alignment: Alignment.bottomCenter,
        children: [
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            height: _barHeight + bottomInset,
            child: ClipRect(
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 28, sigmaY: 28),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        AppColors.glassSurface.withValues(alpha: 0.82),
                        AppColors.glassSurface.withValues(alpha: 0.92),
                      ],
                    ),
                    border: Border(
                      top: BorderSide(
                        color: Colors.white.withValues(alpha: 0.55),
                      ),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.brandPurple.withValues(alpha: 0.08),
                        blurRadius: 24,
                        offset: const Offset(0, -6),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: bottomInset + 4,
            height: _barHeight,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _NavItem(
                  selected: currentIndex == 0,
                  icon: Icons.home_outlined,
                  selectedIcon: Icons.home_rounded,
                  label: 'Beranda',
                  onTap: () => onTap(0),
                ),
                _NavItem(
                  selected: currentIndex == 1,
                  icon: Icons.calendar_month_outlined,
                  selectedIcon: Icons.calendar_month_rounded,
                  label: 'Absensi',
                  onTap: () => onTap(1),
                ),
                const Expanded(child: SizedBox(width: _fabSize)),
                _NavItem(
                  selected: currentIndex == 3,
                  icon: Icons.mail_outline_rounded,
                  selectedIcon: Icons.mail_rounded,
                  label: 'Kotak Masuk',
                  onTap: () => onTap(3),
                ),
                _NavItem(
                  selected: currentIndex == 4,
                  icon: Icons.person_outline_rounded,
                  selectedIcon: Icons.person_rounded,
                  label: 'Akun',
                  onTap: () => onTap(4),
                ),
              ],
            ),
          ),
          Positioned(
            bottom: bottomInset + _barHeight - _fabSize + 6,
            child: _CenterFab(
              selected: currentIndex == _centerIndex,
              onTap: () => onTap(_centerIndex),
            ),
          ),
        ],
      ),
    );
  }
}

class _CenterFab extends StatelessWidget {
  const _CenterFab({
    required this.selected,
    required this.onTap,
  });

  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedPress(
      onTap: onTap,
      scale: 0.93,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              gradient: AppColors.auroraButtonGradient,
              shape: BoxShape.circle,
              border: Border.all(
                color: selected
                    ? AppColors.brandGold
                    : Colors.white.withValues(alpha: 0.85),
                width: 2.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.brandPurple.withValues(alpha: selected ? 0.42 : 0.28),
                  blurRadius: selected ? 22 : 14,
                  offset: const Offset(0, 8),
                ),
                BoxShadow(
                  color: AppColors.brandGold.withValues(alpha: selected ? 0.25 : 0.12),
                  blurRadius: 12,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: const Icon(Icons.add_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(height: 4),
          Text(
            'Pengajuan',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 9,
              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              color: selected ? AppColors.brandPurple : AppColors.textDim,
              height: 1.1,
            ),
          ),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.selected,
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.onTap,
  });

  final bool selected;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: AnimatedPress(
        onTap: onTap,
        scale: 0.92,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  gradient: selected
                      ? LinearGradient(
                          colors: [
                            AppColors.brandPurple.withValues(alpha: 0.14),
                            AppColors.brandBlue.withValues(alpha: 0.08),
                          ],
                        )
                      : null,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: selected
                      ? [
                          BoxShadow(
                            color: AppColors.brandPurple.withValues(alpha: 0.12),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Icon(
                  selected ? selectedIcon : icon,
                  color: selected ? AppColors.brandPurple : AppColors.textDim,
                  size: 22,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 9,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  color: selected ? AppColors.brandPurple : AppColors.textDim,
                  height: 1.1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
