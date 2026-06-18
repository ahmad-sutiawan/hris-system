import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../../core/widgets/talenta_widgets.dart';
import '../home/home_screen.dart';

class MenuScreen extends ConsumerWidget {
  const MenuScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final dashboard = ref.watch(dashboardProvider);
    final employee = auth.employee;
    final unread = dashboard.maybeWhen(
      data: (d) => d['unread_notifications'] as int? ?? 0,
      orElse: () => 0,
    );
    final announcements = dashboard.maybeWhen(
      data: (d) => d['active_announcements'] as int? ?? 0,
      orElse: () => 0,
    );
    final name = employee?['full_name'] ?? auth.user?['username'] ?? '';

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(dashboardProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: HomeGreetingHeader(
                name: name,
                subtitle: employee?['employee_id'] ?? '',
                onAvatarTap: () => context.push('/profile'),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              sliver: SliverToBoxAdapter(
                child: ProfileInfoCard(
                  department: employee?['department_name'] as String? ??
                      employee?['department'] as String?,
                  jobTitle: employee?['job_title'] as String?,
                  managerName: employee?['manager_name'] as String?,
                  onTap: () => context.push('/profile'),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: HomeSectionHeader(title: 'Account Menu'),
            ),
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _MenuTile(
                    icon: Icons.person_outline_rounded,
                    label: 'Employee Profile',
                    onTap: () => context.push('/profile'),
                  ),
                  _MenuTile(
                    icon: Icons.mail_outline_rounded,
                    label: 'Inbox',
                    badge: unread > 0 ? '$unread' : null,
                    onTap: () => context.go('/inbox'),
                  ),
                  _MenuTile(
                    icon: Icons.campaign_outlined,
                    label: 'Announcements',
                    badge: announcements > 0 ? '$announcements' : null,
                    onTap: () => context.push('/announcements'),
                  ),
                  _MenuTile(
                    icon: Icons.apps_rounded,
                    label: 'All Apps',
                    onTap: () => context.push('/all-apps'),
                  ),
                  _MenuTile(
                    icon: Icons.calendar_month_outlined,
                    label: 'Attendance Summary',
                    onTap: () => context.go('/attendance'),
                  ),
                  _MenuTile(
                    icon: Icons.beach_access_outlined,
                    label: 'Leave Requests',
                    onTap: () => context.push('/leave'),
                  ),
                  _MenuTile(
                    icon: Icons.more_time_outlined,
                    label: 'Overtime Requests',
                    onTap: () => context.push('/overtime'),
                  ),
                  _MenuTile(
                    icon: Icons.receipt_long_outlined,
                    label: 'Payslips',
                    onTap: () => context.push('/payslips'),
                  ),
                  _MenuTile(
                    icon: Icons.add_circle_outline_rounded,
                    label: 'New Request',
                    onTap: () => context.go('/request'),
                  ),
                  const SizedBox(height: 20),
                  PrimaryButton(
                    label: 'Sign Out',
                    secondary: true,
                    icon: Icons.logout,
                    onPressed: () async {
                      await ref.read(authProvider.notifier).logout();
                      if (context.mounted) context.go('/login');
                    },
                  ),
                  const SizedBox(height: 100),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MenuTile extends StatelessWidget {
  const _MenuTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.badge,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.chinaRedLight,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: AppColors.chinaRed, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    label,
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                ),
                if (badge != null)
                  Container(
                    margin: const EdgeInsets.only(right: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.chinaRed,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      badge!,
                      style: const TextStyle(
                        color: AppColors.onPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                const Icon(Icons.chevron_right, color: AppColors.textMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
