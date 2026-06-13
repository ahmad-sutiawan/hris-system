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
        body: navigationShell,
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

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.navBar,
        border: Border(
          top: BorderSide(color: AppColors.darkGold.withValues(alpha: 0.25)),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.darkGold.withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.only(top: 4, bottom: 2),
          child: SizedBox(
            height: 54,
            child: Stack(
              clipBehavior: Clip.none,
              alignment: Alignment.center,
              children: [
                Row(
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
                    const Expanded(child: SizedBox(width: 52)),
                    _NavItem(
                      selected: currentIndex == 3,
                      icon: Icons.mail_outline_rounded,
                      selectedIcon: Icons.mail_rounded,
                      label: 'Inbox',
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
                Positioned(
                  top: -22,
                  child: AnimatedPress(
                    onTap: () => onTap(_centerIndex),
                    scale: 0.92,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 52,
                          height: 52,
                          decoration: BoxDecoration(
                            gradient: AppColors.premiumGradient,
                            shape: BoxShape.circle,
                            border: Border.all(color: AppColors.chinaGold, width: 2.5),
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.darkGold.withValues(alpha: 0.35),
                                blurRadius: 14,
                                offset: const Offset(0, 6),
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.add_rounded,
                            color: Colors.white,
                            size: 26,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Pengajuan',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 9,
                            fontWeight: currentIndex == _centerIndex
                                ? FontWeight.w800
                                : FontWeight.w600,
                            color: currentIndex == _centerIndex
                                ? AppColors.darkGold
                                : AppColors.textDim,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
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
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: selected
                    ? AppColors.darkGoldLight.withValues(alpha: 0.8)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                selected ? selectedIcon : icon,
                color: selected ? AppColors.chinaRed : AppColors.textDim,
                size: 22,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 9,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                color: selected ? AppColors.chinaRed : AppColors.textDim,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
