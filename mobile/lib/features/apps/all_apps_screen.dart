import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../core/widgets/talenta_widgets.dart';

class AllAppsScreen extends StatelessWidget {
  const AllAppsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('All Apps')),
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
          label: 'Leave',
          color: AppColors.info,
          onTap: () => context.push('/leave'),
        ),
        TalentaAppGridItem(
          icon: Icons.more_time_rounded,
          label: 'Overtime',
          color: AppColors.accent,
          onTap: () => context.push('/overtime'),
        ),
        TalentaAppGridItem(
          icon: Icons.location_on_rounded,
          label: 'Live Punch',
          color: AppColors.danger,
          onTap: () => context.push('/punch?action=in'),
        ),
        TalentaAppGridItem(
          icon: Icons.history_rounded,
          label: 'Attendance Log',
          color: AppColors.warning,
          onTap: () => context.go('/attendance'),
        ),
        TalentaAppGridItem(
          icon: Icons.receipt_long_rounded,
          label: 'Payslips',
          color: AppColors.success,
          onTap: () => context.push('/payslips'),
        ),
        TalentaAppGridItem(
          icon: Icons.person_rounded,
          label: 'Profile',
          color: AppColors.cyan,
          onTap: () => context.push('/profile'),
        ),
        TalentaAppGridItem(
          icon: Icons.campaign_rounded,
          label: 'Announcements',
          color: AppColors.info,
          onTap: () => context.push('/announcements'),
        ),
        TalentaAppGridItem(
          icon: Icons.notifications_rounded,
          label: 'Inbox',
          color: AppColors.accent,
          onTap: () => context.go('/inbox'),
        ),
        TalentaAppGridItem(
          icon: Icons.add_circle_outline_rounded,
          label: 'Requests',
          color: AppColors.warning,
          onTap: () => context.go('/request'),
        ),
        TalentaAppGridItem(
          icon: Icons.calendar_month_rounded,
          label: 'Shift Schedule',
          color: AppColors.cyan,
          onTap: () => context.push('/calendar'),
        ),
        TalentaAppGridItem(
          icon: Icons.settings_outlined,
          label: 'My Account',
          color: AppColors.textMuted,
          onTap: () => context.go('/account'),
        ),
      ];
}
