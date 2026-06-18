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
        bottomNavigationBar: _ChinaBottomNav(
          currentIndex: navigationShell.currentIndex,
          onTap: navigationShell.goBranch,
        ),
      ),
    );
  }
}

class _ChinaBottomNav extends StatelessWidget {
  const _ChinaBottomNav({
    required this.currentIndex,
    required this.onTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  static const _centerIndex = 2;
  static const _barHeight = 58.0;
  static const _fabSize = 50.0;
  static const _fabOverhang = 22.0;

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
                filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.navBar.withValues(alpha: 0.88),
                    border: Border(
                      top: BorderSide(
                        color: AppColors.darkGold.withValues(alpha: 0.28),
                      ),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.brandNavy.withValues(alpha: 0.06),
                        blurRadius: 16,
                        offset: const Offset(0, -4),
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
      scale: 0.94,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              gradient: AppColors.premiumGradient,
              shape: BoxShape.circle,
              border: Border.all(
                color: selected ? AppColors.brandGold : AppColors.chinaGold,
                width: 2.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.brandNavy.withValues(alpha: selected ? 0.35 : 0.22),
                  blurRadius: selected ? 16 : 12,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: const Icon(Icons.add_rounded, color: Colors.white, size: 26),
          ),
          const SizedBox(height: 3),
          Text(
            'Pengajuan',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 9,
              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              color: selected ? AppColors.brandNavy : AppColors.textDim,
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
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOutCubic,
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: selected
                      ? AppColors.brandGoldLight.withValues(alpha: 0.85)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  selected ? selectedIcon : icon,
                  color: selected ? AppColors.brandNavy : AppColors.textDim,
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
                  color: selected ? AppColors.brandNavy : AppColors.textDim,
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
