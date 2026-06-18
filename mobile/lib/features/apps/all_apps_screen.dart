import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../../core/widgets/talenta_widgets.dart';

class AllAppsScreen extends StatelessWidget {
  const AllAppsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return HrisScaffold(
      appBar: hrisAppBar(title: 'Semua Aplikasi'),
      body: ListView(
        padding: const EdgeInsets.only(top: 8, bottom: 24),
        children: [
          TalentaAppGrid(
            items: _allApps(context),
          ),
        ],
      ),
    );
  }

  static List<TalentaAppGridItem> _allApps(BuildContext context) => [
        TalentaAppGridItem(
          icon: Icons.beach_access_rounded,
          label: 'Cuti',
          color: AppColors.info,
          onTap: () => context.push('/leave'),
        ),
        TalentaAppGridItem(
          icon: Icons.more_time_rounded,
          label: 'Lembur',
          color: AppColors.accent,
          onTap: () => context.push('/overtime'),
        ),
        TalentaAppGridItem(
          icon: Icons.location_on_rounded,
          label: 'Absen Langsung',
          color: AppColors.danger,
          onTap: () => context.push('/punch?action=in'),
        ),
        TalentaAppGridItem(
          icon: Icons.history_rounded,
          label: 'Riwayat Absensi',
          color: AppColors.warning,
          onTap: () => context.go('/attendance'),
        ),
        TalentaAppGridItem(
          icon: Icons.receipt_long_rounded,
          label: 'Slip Gaji',
          color: AppColors.success,
          onTap: () => context.push('/payslips'),
        ),
        TalentaAppGridItem(
          icon: Icons.person_rounded,
          label: 'Profil',
          color: AppColors.cyan,
          onTap: () => context.push('/profile'),
        ),
        TalentaAppGridItem(
          icon: Icons.campaign_rounded,
          label: 'Pengumuman',
          color: AppColors.info,
          onTap: () => context.push('/announcements'),
        ),
        TalentaAppGridItem(
          icon: Icons.notifications_rounded,
          label: 'Kotak Masuk',
          color: AppColors.accent,
          onTap: () => context.go('/inbox'),
        ),
        TalentaAppGridItem(
          icon: Icons.add_circle_outline_rounded,
          label: 'Pengajuan',
          color: AppColors.warning,
          onTap: () => context.go('/request'),
        ),
        TalentaAppGridItem(
          icon: Icons.calendar_month_rounded,
          label: 'Jadwal Shift',
          color: AppColors.cyan,
          onTap: () => context.push('/calendar'),
        ),
        TalentaAppGridItem(
          icon: Icons.settings_outlined,
          label: 'Akun Saya',
          color: AppColors.textMuted,
          onTap: () => context.go('/account'),
        ),
      ];
}
