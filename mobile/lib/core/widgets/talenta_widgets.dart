import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';
import '../utils/shift_utils.dart';
import 'animated_interactions.dart';
import 'aurora_background.dart';

const _cardRadius = 16.0;

String greetingForTime(DateTime now) {
  final hour = now.hour;
  if (hour < 11) return 'Selamat pagi,';
  if (hour < 15) return 'Selamat siang,';
  if (hour < 18) return 'Selamat sore,';
  return 'Selamat malam,';
}

class HomeGreetingHeader extends StatelessWidget {
  const HomeGreetingHeader({
    super.key,
    required this.name,
    this.subtitle,
    this.onAvatarTap,
  });

  final String name;
  final String? subtitle;
  final VoidCallback? onAvatarTap;

  @override
  Widget build(BuildContext context) {
    final firstName = name.split(' ').first;

    return FadeSlideIn(
      index: 0,
      child: Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      decoration: BoxDecoration(
        gradient: AppColors.auroraHeroGradient,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
        boxShadow: [
          BoxShadow(
            color: AppColors.brandPurple.withValues(alpha: 0.28),
            blurRadius: 28,
            offset: const Offset(0, 14),
          ),
          BoxShadow(
            color: AppColors.brandGold.withValues(alpha: 0.14),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            right: -30,
            top: -30,
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Colors.white.withValues(alpha: 0.18),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: -20,
            bottom: -20,
            child: Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.brandGold.withValues(alpha: 0.15),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 20, 18, 20),
            child: Row(
              children: [
                AnimatedPress(
                  onTap: onAvatarTap,
                  scale: 0.94,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: AppColors.darkGoldGradient,
                    ),
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: AppColors.goldGradient,
                      ),
                      child: CircleAvatar(
                        radius: 24,
                        backgroundColor: Colors.white,
                        child: Text(
                          firstName.isNotEmpty ? firstName[0].toUpperCase() : '?',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            color: AppColors.chinaRed,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        greetingForTime(DateTime.now()),
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.white.withValues(alpha: 0.88),
                        ),
                      ),
                      Text(
                        name,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 21,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
                      if (subtitle != null && subtitle!.isNotEmpty)
                        Container(
                          margin: const EdgeInsets.only(top: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            gradient: AppColors.darkGoldGradient,
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            subtitle!,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppColors.onDarkGold,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
    );
  }
}

class ShiftScheduleCard extends StatelessWidget {
  const ShiftScheduleCard({
    super.key,
    required this.dateLabel,
    required this.location,
    required this.timeRange,
    required this.canClockIn,
    required this.canClockOut,
    required this.onClockIn,
    required this.onClockOut,
    this.checkInLabel,
    this.checkOutLabel,
  });

  final String dateLabel;
  final String location;
  final String timeRange;
  final bool canClockIn;
  final bool canClockOut;
  final VoidCallback onClockIn;
  final VoidCallback onClockOut;
  final String? checkInLabel;
  final String? checkOutLabel;

  @override
  Widget build(BuildContext context) {
    return AuroraGlass(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: EdgeInsets.zero,
      borderRadius: 22,
      showTopShine: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              gradient: AppColors.auroraHeroGradient,
              borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.schedule_rounded, color: Colors.white, size: 16),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    dateLabel,
                    style: GoogleFonts.plusJakartaSans(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Container(
            height: 3,
            decoration: const BoxDecoration(
              gradient: AppColors.goldGradient,
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  location,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppColors.text,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  timeRange == '—' && checkInLabel != null
                      ? 'Hari ini aktif'
                      : timeRange,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: AppColors.brandPurple,
                    letterSpacing: -0.5,
                  ),
                ),
                if (checkInLabel != null || checkOutLabel != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: AppColors.brandPurple.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AppColors.brandPurple.withValues(alpha: 0.12),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.access_time_rounded, size: 16, color: AppColors.brandPurple),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            [
                              if (checkInLabel != null) 'Masuk $checkInLabel',
                              if (checkOutLabel != null) 'Pulang $checkOutLabel',
                            ].join(' · '),
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 13,
                              color: AppColors.text,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          Container(
            margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            decoration: BoxDecoration(
              color: AppColors.brandPurple.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: AppColors.brandPurple.withValues(alpha: 0.1),
              ),
            ),
            child: IntrinsicHeight(
              child: Row(
                children: [
                  Expanded(
                    child: _PunchAction(
                      icon: Icons.login_rounded,
                      label: 'Masuk',
                      color: AppColors.brandGoldDark,
                      enabled: canClockIn,
                      onTap: onClockIn,
                    ),
                  ),
                  Container(
                    width: 1,
                    height: 28,
                    color: AppColors.brandPurple.withValues(alpha: 0.12),
                  ),
                  Expanded(
                    child: _PunchAction(
                      icon: Icons.logout_rounded,
                      label: 'Pulang',
                      color: AppColors.brandPurple,
                      enabled: canClockOut,
                      onTap: onClockOut,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PunchAction extends StatelessWidget {
  const _PunchAction({
    required this.icon,
    required this.label,
    required this.color,
    required this.enabled,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedPress(
      onTap: enabled ? onTap : null,
      enabled: enabled,
      scale: 0.97,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: AppColors.text,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class TalentaAppGridItem {
  const TalentaAppGridItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
}

class TalentaAppGrid extends StatelessWidget {
  const TalentaAppGrid({
    super.key,
    required this.items,
    this.horizontalPadding = 0,
  });

  final List<TalentaAppGridItem> items;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 4,
          mainAxisSpacing: 10,
          crossAxisSpacing: 6,
          childAspectRatio: 0.92,
        ),
        itemCount: items.length,
        itemBuilder: (context, index) {
          final item = items[index];
          return FadeSlideIn(
            index: index + 4,
            delayMs: 35,
            child: _AppGridTile(
              icon: item.icon,
              label: item.label,
              color: item.color,
              onTap: item.onTap,
            ),
          );
        },
      ),
    );
  }
}

class _AppGridTile extends StatelessWidget {
  const _AppGridTile({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedPress(
      onTap: onTap,
      scale: 0.94,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Colors.white.withValues(alpha: 0.95),
                  color.withValues(alpha: 0.08),
                ],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: color.withValues(alpha: 0.18)),
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.18),
                  blurRadius: 14,
                  offset: const Offset(0, 5),
                ),
              ],
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppColors.text,
              height: 1.15,
            ),
          ),
        ],
      ),
    );
  }
}

class PromoBannerCarousel extends StatefulWidget {
  const PromoBannerCarousel({
    super.key,
    required this.items,
    this.onTap,
  });

  final List<Map<String, dynamic>> items;
  final ValueChanged<Map<String, dynamic>>? onTap;

  @override
  State<PromoBannerCarousel> createState() => _PromoBannerCarouselState();
}

class _PromoBannerCarouselState extends State<PromoBannerCarousel> {
  final _controller = PageController();
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    return Column(
      children: [
        SizedBox(
          height: 132,
          child: PageView.builder(
            controller: _controller,
            onPageChanged: (i) => setState(() => _page = i),
            itemCount: widget.items.length,
            itemBuilder: (context, i) {
              final item = widget.items[i];
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Material(
                  color: Colors.transparent,
                  child: AnimatedPress(
                    onTap: widget.onTap == null ? null : () => widget.onTap!(item),
                    scale: 0.98,
                    child: Ink(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(_cardRadius),
                        gradient: AppColors.auroraBannerGradient,
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.2),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.brandPurple.withValues(alpha: 0.28),
                            blurRadius: 20,
                            offset: const Offset(0, 10),
                          ),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    item['title'] ?? 'Pengumuman',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: GoogleFonts.plusJakartaSans(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w800,
                                      fontSize: 15,
                                      height: 1.3,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 12,
                                      vertical: 6,
                                    ),
                                    decoration: BoxDecoration(
                                      gradient: AppColors.goldGradient,
                                      borderRadius: BorderRadius.circular(999),
                                    ),
                                    child: Text(
                                      'Baca selengkapnya',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w800,
                                        color: AppColors.onGold,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 8),
                            Icon(
                              Icons.campaign_rounded,
                              size: 48,
                              color: Colors.white.withValues(alpha: 0.25),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        if (widget.items.length > 1) ...[
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(widget.items.length, (i) {
              final active = i == _page;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 280),
                curve: Curves.easeOutCubic,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: active ? 20 : 6,
                height: 6,
                decoration: BoxDecoration(
                  gradient: active ? AppColors.auroraButtonGradient : null,
                  color: active ? null : AppColors.textDim.withValues(alpha: 0.35),
                  borderRadius: BorderRadius.circular(999),
                ),
              );
            }),
          ),
        ],
      ],
    );
  }
}

class HomeSectionHeader extends StatelessWidget {
  const HomeSectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 20,
            decoration: BoxDecoration(
              gradient: AppColors.auroraButtonGradient,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: AppColors.text,
                letterSpacing: -0.3,
              ),
            ),
          ),
          if (actionLabel != null && onAction != null)
            AnimatedPress(
              onTap: onAction,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.brandPurple.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  actionLabel!,
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.w700,
                    color: AppColors.brandPurple,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class LeaveBalanceStrip extends StatelessWidget {
  const LeaveBalanceStrip({super.key, required this.balances});

  final List balances;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 84,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screenH),
        scrollDirection: Axis.horizontal,
        itemCount: balances.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final b = balances[i] as Map<String, dynamic>;
          return AnimatedPress(
            scale: 0.97,
            child: SizedBox(
              width: 136,
              child: AuroraGlass(
            padding: const EdgeInsets.all(12),
            borderRadius: _cardRadius,
            showTopShine: false,
            child: Row(
              children: [
                Container(
                  width: 4,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: AppColors.auroraButtonGradient,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${b['leave_type_code'] ?? '—'}',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.w800,
                          fontSize: 14,
                          color: AppColors.brandPurple,
                        ),
                      ),
                      Text(
                        'Sisa ${b['remaining']} hari',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppColors.text,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          ),
          );
        },
      ),
    );
  }
}

class ProfileInfoCard extends StatelessWidget {
  const ProfileInfoCard({
    super.key,
    required this.department,
    required this.jobTitle,
    this.managerName,
    this.onTap,
  });

  final String? department;
  final String? jobTitle;
  final String? managerName;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return AuroraGlass(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(16),
      borderRadius: 20,
      onTap: onTap,
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.brandBlue.withValues(alpha: 0.18),
                  AppColors.brandPurple.withValues(alpha: 0.08),
                ],
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.apartment_rounded, color: AppColors.brandBlue),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  department ?? '—',
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
                Text(
                  jobTitle ?? '',
                  style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                ),
                if (managerName != null && managerName!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Atasan: $managerName',
                      style: const TextStyle(color: AppColors.textDim, fontSize: 12),
                    ),
                  ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: AppColors.textMuted),
        ],
      ),
    );
  }
}

class AnnouncementPreviewTile extends StatelessWidget {
  const AnnouncementPreviewTile({
    super.key,
    required this.title,
    required this.summary,
    required this.onTap,
    this.isPinned = false,
  });

  final String title;
  final String summary;
  final VoidCallback onTap;
  final bool isPinned;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(_cardRadius),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_cardRadius),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(_cardRadius),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.infoDim,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.campaign_outlined, color: AppColors.info, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (isPinned)
                            const Padding(
                              padding: EdgeInsets.only(right: 6),
                              child: Icon(Icons.push_pin, size: 14, color: AppColors.accent),
                            ),
                          Expanded(
                            child: Text(
                              title,
                              style: GoogleFonts.plusJakartaSans(
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (summary.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          summary,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ],
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

class InboxPreviewTile extends StatelessWidget {
  const InboxPreviewTile({
    super.key,
    required this.title,
    required this.message,
    required this.unread,
    required this.onTap,
  });

  final String title;
  final String message;
  final bool unread;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(_cardRadius),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_cardRadius),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(_cardRadius),
              border: Border.all(
                color: unread ? AppColors.accent.withValues(alpha: 0.35) : AppColors.border,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: unread ? AppColors.accent : Colors.transparent,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: unread ? FontWeight.w800 : FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        message,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 13,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
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

class RequestActionCard extends StatelessWidget {
  const RequestActionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedPress(
      onTap: onTap,
      scale: 0.98,
      child: AuroraGlass(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        borderRadius: 20,
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    color.withValues(alpha: 0.2),
                    color.withValues(alpha: 0.06),
                  ],
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: color.withValues(alpha: 0.15),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Icon(icon, color: color, size: 26),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class TeamMemberAvatar extends StatelessWidget {
  const TeamMemberAvatar({
    super.key,
    required this.name,
    this.size = 52,
  });

  final String name;
  final double size;

  @override
  Widget build(BuildContext context) {
    final initial = name.trim().isNotEmpty ? name.trim()[0].toUpperCase() : '?';
    return Column(
      children: [
        CircleAvatar(
          radius: size / 2,
          backgroundColor: AppColors.chinaRedLight,
          child: Text(
            initial,
            style: GoogleFonts.plusJakartaSans(
              fontWeight: FontWeight.w800,
              color: AppColors.chinaRed,
              fontSize: size * 0.38,
            ),
          ),
        ),
        const SizedBox(height: 6),
        SizedBox(
          width: size + 18,
          child: Text(
            name.split(' ').first,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.text,
            ),
          ),
        ),
      ],
    );
  }
}

class DirectReportsRow extends StatelessWidget {
  const DirectReportsRow({
    super.key,
    required this.members,
    this.onTap,
  });

  final List<Map<String, dynamic>> members;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (members.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(_cardRadius),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_cardRadius),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(_cardRadius),
              border: Border.all(color: AppColors.border),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final member in members.take(8))
                    Padding(
                      padding: const EdgeInsets.only(right: 16),
                      child: TeamMemberAvatar(
                        name: member['full_name'] ?? '?',
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class UpcomingShiftsPreview extends StatelessWidget {
  const UpcomingShiftsPreview({
    super.key,
    required this.shifts,
    required this.formatTimeRange,
    this.onTap,
  });

  final List<Map<String, dynamic>> shifts;
  final String Function(Map<String, dynamic> shift) formatTimeRange;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (shifts.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: [
          for (final shift in shifts.take(3))
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Material(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(_cardRadius),
                child: InkWell(
                  onTap: onTap,
                  borderRadius: BorderRadius.circular(_cardRadius),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(_cardRadius),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            color: AppColors.cyanDim,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.event_rounded, color: AppColors.cyan),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                formatWorkDateLabel(shift['work_date'] as String?),
                                style: GoogleFonts.plusJakartaSans(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 13,
                                  color: AppColors.textMuted,
                                ),
                              ),
                              Text(
                                '${shift['shift_name'] ?? shift['shift_code'] ?? 'Shift'} · ${formatTimeRange(shift)}',
                                style: GoogleFonts.plusJakartaSans(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 14,
                                ),
                              ),
                              if ((shift['plant_name'] as String?)?.isNotEmpty ?? false)
                                Text(
                                  shift['plant_name'] as String,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.textDim,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class PendingRequestsStrip extends StatelessWidget {
  const PendingRequestsStrip({
    super.key,
    required this.leaveCount,
    required this.overtimeCount,
    required this.onLeaveTap,
    required this.onOvertimeTap,
    this.leaveLabel,
    this.overtimeLabel,
  });

  final int leaveCount;
  final int overtimeCount;
  final VoidCallback onLeaveTap;
  final VoidCallback onOvertimeTap;
  final String Function(int count)? leaveLabel;
  final String Function(int count)? overtimeLabel;

  @override
  Widget build(BuildContext context) {
    if (leaveCount == 0 && overtimeCount == 0) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: [
          if (leaveCount > 0)
            Expanded(
              child: _PendingChip(
                label: leaveLabel?.call(leaveCount) ?? '$leaveCount cuti menunggu',
                onTap: onLeaveTap,
              ),
            ),
          if (leaveCount > 0 && overtimeCount > 0) const SizedBox(width: 10),
          if (overtimeCount > 0)
            Expanded(
              child: _PendingChip(
                label: overtimeLabel?.call(overtimeCount) ?? '$overtimeCount lembur menunggu',
                onTap: onOvertimeTap,
              ),
            ),
        ],
      ),
    );
  }
}

class _PendingChip extends StatelessWidget {
  const _PendingChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.darkGoldLight,
      borderRadius: BorderRadius.circular(999),
      child: AnimatedPress(
        onTap: onTap,
        scale: 0.98,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: AppColors.darkGold.withValues(alpha: 0.35)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.notifications_active_rounded, size: 14, color: AppColors.darkGold),
              const SizedBox(width: 6),
              Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.darkGoldRich,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
