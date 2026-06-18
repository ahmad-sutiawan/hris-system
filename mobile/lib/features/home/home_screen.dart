import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/shift_utils.dart';
import '../../core/widgets/animated_interactions.dart';
import '../../core/widgets/hris_widgets.dart';
import '../../core/widgets/talenta_widgets.dart';

final dashboardProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getDashboard();
});

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final dashboard = ref.watch(dashboardProvider);
    final employee = auth.employee;
    final name = employee?['full_name'] ?? auth.user?['username'] ?? 'Karyawan';
    final employeeId = employee?['employee_id'] ?? '';

    return RefreshIndicator(
      color: AppColors.chinaRed,
      backgroundColor: AppColors.surface,
      onRefresh: () async => ref.invalidate(dashboardProvider),
      child: dashboard.when(
        loading: () => const CustomScrollView(
          physics: AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            ),
          ],
        ),
        error: (e, _) => CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverFillRemaining(
              child: EmptyState(
                icon: Icons.cloud_off,
                title: 'Gagal memuat dashboard',
                subtitle: '$e',
              ),
            ),
          ],
        ),
        data: (data) {
          final punchUi = data['punch_ui'] as Map<String, dynamic>? ?? {};
          final shift = data['today_shift'] as Map<String, dynamic>?;
          final record = data['today_record'] as Map<String, dynamic>?;
          final fmt = DateFormat('HH:mm');
          final dateFmt = DateFormat('EEE, dd MMM yyyy');

          String? checkInLabel;
          String? checkOutLabel;
          if (record?['check_in'] != null) {
            checkInLabel = fmt.format(
              DateTime.parse(record!['check_in'] as String).toLocal(),
            );
          }
          if (record?['check_out'] != null) {
            checkOutLabel = fmt.format(
              DateTime.parse(record!['check_out'] as String).toLocal(),
            );
          }

          final announcementItems =
              (data['featured_announcements'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          final directReports =
              (data['direct_reports'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          final teamColleagues =
              (data['team_colleagues'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          final teamMembers = directReports.isNotEmpty ? directReports : teamColleagues;
          final teamTitle =
              directReports.isNotEmpty ? 'Bawahan langsung' : 'Rekan tim';
          final upcomingShifts =
              (data['upcoming_shifts'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          final pending = data['pending_requests'] as Map<String, dynamic>? ?? {};
          final pendingLeave = pending['leave'] as int? ?? 0;
          final pendingOvertime = pending['overtime'] as int? ?? 0;
          final pendingApprovals = data['pending_approvals'] as Map<String, dynamic>? ?? {};
          final approvalLeave = pendingApprovals['leave'] as int? ?? 0;
          final approvalOvertime = pendingApprovals['overtime'] as int? ?? 0;
            final leaveBalances = data['leave_balances'] as List? ?? [];
          final statsExtra = data['stats_extra'] as Map<String, dynamic>? ?? {};
          final attendanceRate = data['attendance_rate'];
          final onLeaveToday =
              (data['on_leave_today'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          var sectionIndex = 0;

          Widget section(Widget child) {
            final index = sectionIndex++;
            return SliverToBoxAdapter(
              child: FadeSlideIn(index: index, child: child),
            );
          }

          return CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverToBoxAdapter(
                child: HomeGreetingHeader(
                  name: name,
                  subtitle: employeeId.isNotEmpty ? employeeId : null,
                  onAvatarTap: () => context.push('/profile'),
                ),
              ),
              section(
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.section),
                  child: _OpsStatsStrip(
                    stats: statsExtra,
                    attendanceRate: attendanceRate,
                  ),
                ),
              ),
              section(
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.item),
                  child: ShiftScheduleCard(
                    dateLabel: 'Jadwal shift ${dateFmt.format(DateTime.now())}',
                    location: shiftLocationLabel(shift, employee: employee),
                    timeRange: formatShiftTimeRange(shift),
                    canClockIn: punchUi['can_clock_in'] as bool? ?? true,
                    canClockOut: punchUi['can_clock_out'] as bool? ?? true,
                    checkInLabel: checkInLabel,
                    checkOutLabel: checkOutLabel,
                    onClockIn: () => context.push('/punch?action=in'),
                    onClockOut: () => context.push('/punch?action=out'),
                  ),
                ),
              ),
              if (approvalLeave > 0 || approvalOvertime > 0)
                section(
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.item),
                    child: PendingRequestsStrip(
                      leaveCount: approvalLeave,
                      overtimeCount: approvalOvertime,
                      onLeaveTap: () => context.push('/leave'),
                      onOvertimeTap: () => context.push('/overtime'),
                      leaveLabel: (c) => 'Setujui $c cuti',
                      overtimeLabel: (c) => 'Setujui $c lembur',
                    ),
                  ),
                ),
              if (pendingLeave > 0 || pendingOvertime > 0)
                section(
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.item),
                    child: PendingRequestsStrip(
                      leaveCount: pendingLeave,
                      overtimeCount: pendingOvertime,
                      onLeaveTap: () => context.push('/leave'),
                      onOvertimeTap: () => context.push('/overtime'),
                      leaveLabel: (c) => '$c cuti menunggu',
                      overtimeLabel: (c) => '$c lembur menunggu',
                    ),
                  ),
                ),
              section(
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const GoldSectionTitle(title: 'Quick Menu'),
                    GoldPanel(
                      padding: const EdgeInsets.fromLTRB(8, 12, 8, 8),
                      child: TalentaAppGrid(items: _homeQuickApps(context)),
                    ),
                  ],
                ),
              ),
              if (onLeaveToday.isNotEmpty)
                section(
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const GoldSectionTitle(title: 'Sedang cuti hari ini'),
                      ...onLeaveToday.map((item) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: HrisCard(
                            child: ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: CircleAvatar(
                                backgroundColor: AppColors.chinaRedLight,
                                child: Text(
                                  (item['full_name'] as String? ?? '?')
                                      .split(' ')
                                      .map((p) => p.isNotEmpty ? p[0] : '')
                                      .take(2)
                                      .join()
                                      .toUpperCase(),
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w800,
                                    color: AppColors.chinaRed,
                                  ),
                                ),
                              ),
                              title: Text(
                                item['full_name'] as String? ?? '—',
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              subtitle: Text(
                                [
                                  item['leave_type'],
                                  item['department'],
                                ].whereType<String>().where((s) => s.isNotEmpty).join(' · '),
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              if (leaveBalances.isNotEmpty)
                section(
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const GoldSectionTitle(title: 'Saldo cuti'),
                      LeaveBalanceStrip(balances: leaveBalances),
                    ],
                  ),
                ),
              if (announcementItems.isNotEmpty)
                section(
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.item),
                    child: PromoBannerCarousel(
                      items: announcementItems,
                      onTap: (item) => context.push('/announcements/${item['id']}'),
                    ),
                  ),
                ),
              if (teamMembers.isNotEmpty)
                section(
                  Column(
                    children: [
                      GoldSectionTitle(
                        title: teamTitle,
                        actionLabel: 'Lihat aktivitas',
                        onAction: () => context.go('/attendance'),
                      ),
                      DirectReportsRow(
                        members: teamMembers,
                        onTap: () => context.go('/attendance'),
                      ),
                    ],
                  ),
                ),
              if (upcomingShifts.isNotEmpty)
                section(
                  Column(
                    children: [
                      GoldSectionTitle(
                        title: 'Upcoming Schedule',
                        actionLabel: 'Calendar',
                        onAction: () => context.push('/calendar'),
                      ),
                      UpcomingShiftsPreview(
                        shifts: upcomingShifts,
                        formatTimeRange: formatShiftTimeRange,
                        onTap: () => context.push('/calendar'),
                      ),
                    ],
                  ),
                ),
              if ((data['recent_notifications'] as List?)?.isNotEmpty ?? false)
                section(
                  Column(
                    children: [
                      GoldSectionTitle(
                        title: 'Kotak masuk',
                        actionLabel: 'Lihat semua',
                        onAction: () => context.go('/inbox'),
                      ),
                      ...((data['recent_notifications'] as List).take(3).map((n) {
                        final item = n as Map<String, dynamic>;
                        return InboxPreviewTile(
                          title: item['title'] ?? '',
                          message: item['message'] ?? '',
                          unread: item['is_read'] != true,
                          onTap: () => context.go('/inbox'),
                        );
                      })),
                    ],
                  ),
                ),
              const SliverToBoxAdapter(
                child: SizedBox(height: AppSpacing.bottomNav),
              ),
            ],
          );
        },
      ),
    );
  }

  static List<TalentaAppGridItem> _homeQuickApps(BuildContext context) => [
        TalentaAppGridItem(
          icon: Icons.beach_access_rounded,
          label: 'Leave',
          color: AppColors.chinaRed,
          onTap: () => context.push('/leave/new'),
        ),
        TalentaAppGridItem(
          icon: Icons.more_time_rounded,
          label: 'Overtime',
          color: AppColors.darkGold,
          onTap: () => context.push('/overtime/new'),
        ),
        TalentaAppGridItem(
          icon: Icons.location_on_rounded,
          label: 'Live Punch',
          color: AppColors.chinaRedDark,
          onTap: () => context.push('/punch?action=in'),
        ),
        TalentaAppGridItem(
          icon: Icons.history_rounded,
          label: 'Attendance Log',
          color: AppColors.darkGoldRich,
          onTap: () => context.go('/attendance'),
        ),
        TalentaAppGridItem(
          icon: Icons.receipt_long_rounded,
          label: 'Payslips',
          color: AppColors.success,
          onTap: () => context.push('/payslips'),
        ),
        TalentaAppGridItem(
          icon: Icons.calendar_month_rounded,
          label: 'Calendar',
          color: AppColors.darkGold,
          onTap: () => context.push('/calendar'),
        ),
        TalentaAppGridItem(
          icon: Icons.campaign_rounded,
          label: 'Announcements',
          color: AppColors.chinaRed,
          onTap: () => context.push('/announcements'),
        ),
        TalentaAppGridItem(
          icon: Icons.apps_rounded,
          label: 'All Apps',
          color: AppColors.textMuted,
          onTap: () => context.push('/all-apps'),
        ),
      ];
}

class _OpsStatsStrip extends StatelessWidget {
  const _OpsStatsStrip({
    required this.stats,
    required this.attendanceRate,
  });

  final Map<String, dynamic> stats;
  final dynamic attendanceRate;

  @override
  Widget build(BuildContext context) {
    final present = stats['present_today'] ?? 0;
    final onLeave = stats['on_leave_today'] ?? 0;
    final absent = stats['absent_today'] ?? 0;
    final rate = attendanceRate is num
        ? attendanceRate.toStringAsFixed(1)
        : '$attendanceRate';

    return GoldPanel(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Ringkasan operasional',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.success.withValues(alpha: 0.25)),
                ),
                child: Text(
                  '$rate% kehadiran',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppColors.success,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _OpsStatChip(label: 'Hadir', value: '$present', color: AppColors.success)),
              const SizedBox(width: 8),
              Expanded(child: _OpsStatChip(label: 'Cuti', value: '$onLeave', color: AppColors.info)),
              const SizedBox(width: 8),
              Expanded(child: _OpsStatChip(label: 'Belum', value: '$absent', color: AppColors.warning)),
            ],
          ),
        ],
      ),
    );
  }
}

class _OpsStatChip extends StatelessWidget {
  const _OpsStatChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: color,
              letterSpacing: 0.04,
            ),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}
