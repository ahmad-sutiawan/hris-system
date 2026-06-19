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

class _NavSpec {
  const _NavSpec({
    required this.index,
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.accent,
    required this.accentSoft,
  });

  final int index;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Color accent;
  final Color accentSoft;
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

  static const _leftItems = [
    _NavSpec(
      index: 0,
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
      label: 'Beranda',
      accent: AppColors.brandPurple,
      accentSoft: AppColors.chinaRedLight,
    ),
    _NavSpec(
      index: 1,
      icon: Icons.people_outline_rounded,
      selectedIcon: Icons.people_rounded,
      label: 'Karyawan',
      accent: AppColors.cyan,
      accentSoft: AppColors.cyanDim,
    ),
  ];

  static const _rightItems = [
    _NavSpec(
      index: 3,
      icon: Icons.mail_outline_rounded,
      selectedIcon: Icons.mail_rounded,
      label: 'Inbox',
      accent: AppColors.info,
      accentSoft: AppColors.infoDim,
    ),
    _NavSpec(
      index: 4,
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
      label: 'Akun',
      accent: AppColors.brandOrange,
      accentSoft: AppColors.warningDim,
    ),
  ];

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
                for (final item in _leftItems)
                  _NavItem(
                    selected: currentIndex == item.index,
                    icon: item.icon,
                    selectedIcon: item.selectedIcon,
                    label: item.label,
                    accent: item.accent,
                    accentSoft: item.accentSoft,
                    onTap: () => onTap(item.index),
                  ),
                const Expanded(child: SizedBox(width: _fabSize)),
                for (final item in _rightItems)
                  _NavItem(
                    selected: currentIndex == item.index,
                    icon: item.icon,
                    selectedIcon: item.selectedIcon,
                    label: item.label,
                    accent: item.accent,
                    accentSoft: item.accentSoft,
                    onTap: () => onTap(item.index),
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
    required this.accent,
    required this.accentSoft,
    required this.onTap,
    this.compact = false,
  });

  final bool selected;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Color accent;
  final Color accentSoft;
  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: AnimatedPress(
        onTap: onTap,
        scale: 0.92,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: compact ? 1 : 2),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                padding: EdgeInsets.symmetric(
                  horizontal: compact ? 7 : 10,
                  vertical: compact ? 5 : 6,
                ),
                decoration: BoxDecoration(
                  gradient: selected
                      ? LinearGradient(
                          colors: [
                            accent.withValues(alpha: 0.18),
                            accentSoft.withValues(alpha: 0.9),
                          ],
                        )
                      : null,
                  borderRadius: BorderRadius.circular(14),
                  border: selected
                      ? Border.all(color: accent.withValues(alpha: 0.28))
                      : null,
                  boxShadow: selected
                      ? [
                          BoxShadow(
                            color: accent.withValues(alpha: 0.16),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Icon(
                  selected ? selectedIcon : icon,
                  color: selected ? accent : AppColors.textDim,
                  size: compact ? 20 : 22,
                ),
              ),
              const SizedBox(height: 2),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  label,
                  maxLines: 1,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: compact ? 8.5 : 9,
                    fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                    color: selected ? accent : AppColors.textDim,
                    height: 1.1,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
