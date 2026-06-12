import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';

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
      color: AppColors.accent,
      onRefresh: () async => ref.invalidate(dashboardProvider),
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverAppBar(
            floating: true,
            pinned: true,
            backgroundColor: AppColors.surface,
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Halo, ${name.split(' ').first}',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (employeeId.isNotEmpty)
                  Text(
                    employeeId,
                    style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                  ),
              ],
            ),
            actions: [
              IconButton(
                tooltip: 'Notifikasi',
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () => context.push('/notifications'),
              ),
              IconButton(
                tooltip: 'Pengumuman',
                icon: const Icon(Icons.campaign_outlined),
                onPressed: () => context.push('/announcements'),
              ),
            ],
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            sliver: dashboard.when(
              loading: () => const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => SliverFillRemaining(
                child: EmptyState(
                  icon: Icons.cloud_off,
                  title: 'Gagal memuat dashboard',
                  subtitle: '$e',
                ),
              ),
              data: (data) => SliverList(
                delegate: SliverChildListDelegate([
                  _PunchSection(data: data),
                  const SizedBox(height: 16),
                  _QuickActions(),
                  const SizedBox(height: 16),
                  if ((data['leave_balances'] as List?)?.isNotEmpty ?? false)
                    _LeaveBalances(balances: data['leave_balances'] as List),
                  const SizedBox(height: 16),
                  _TodaySummary(data: data),
                  const SizedBox(height: 16),
                  if ((data['recent_notifications'] as List?)?.isNotEmpty ?? false)
                    _RecentNotifications(items: data['recent_notifications'] as List),
                ]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PunchSection extends StatelessWidget {
  const _PunchSection({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final punchUi = data['punch_ui'] as Map<String, dynamic>? ?? {};
    final status = punchUi['status'] as String? ?? 'pending';
    final record = data['today_record'] as Map<String, dynamic>?;
    final fmt = DateFormat('HH:mm');

    String statusText;
    Color statusColor;
    IconData statusIcon;
    switch (status) {
      case 'in':
        statusText = 'Anda sedang bekerja';
        statusColor = AppColors.success;
        statusIcon = Icons.check_circle_outline;
      case 'out':
        statusText = 'Anda sudah pulang hari ini';
        statusColor = AppColors.info;
        statusIcon = Icons.logout;
      default:
        statusText = 'Belum absen hari ini';
        statusColor = AppColors.warning;
        statusIcon = Icons.schedule;
    }

    return HrisCard(
      showAccentBar: true,
      accentColor: statusColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(statusIcon, color: statusColor, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      statusText,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (record?['check_in'] != null)
                      Text(
                        'Masuk ${fmt.format(DateTime.parse(record!['check_in'] as String).toLocal())}'
                        '${record['check_out'] != null ? ' · Pulang ${fmt.format(DateTime.parse(record['check_out'] as String).toLocal())}' : ''}',
                        style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: PrimaryButton(
                  label: 'Absen Masuk',
                  icon: Icons.login,
                  onPressed: () => context.push('/punch?action=in'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: PrimaryButton(
                  label: 'Absen Pulang',
                  icon: Icons.logout,
                  secondary: true,
                  onPressed: () => context.push('/punch?action=out'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Menu cepat'),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 4,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 0.82,
          children: [
            QuickActionTile(
              icon: Icons.beach_access,
              label: 'Ajukan Cuti',
              color: AppColors.info,
              onTap: () => context.push('/leave/new'),
            ),
            QuickActionTile(
              icon: Icons.more_time,
              label: 'Ajukan Lembur',
              color: AppColors.accent,
              onTap: () => context.push('/overtime/new'),
            ),
            QuickActionTile(
              icon: Icons.receipt_long,
              label: 'Slip Gaji',
              color: AppColors.success,
              onTap: () => context.push('/payslips'),
            ),
            QuickActionTile(
              icon: Icons.badge_outlined,
              label: 'Profil Saya',
              color: AppColors.steel700,
              onTap: () => context.push('/profile'),
            ),
            QuickActionTile(
              icon: Icons.calendar_month,
              label: 'Rekap Absensi',
              color: AppColors.steel500,
              onTap: () => context.go('/attendance'),
            ),
            QuickActionTile(
              icon: Icons.notifications,
              label: 'Notifikasi',
              color: AppColors.warning,
              onTap: () => context.push('/notifications'),
            ),
            QuickActionTile(
              icon: Icons.campaign,
              label: 'Pengumuman',
              color: AppColors.info,
              onTap: () => context.push('/announcements'),
            ),
          ],
        ),
      ],
    );
  }
}

class _LeaveBalances extends StatelessWidget {
  const _LeaveBalances({required this.balances});

  final List balances;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Saldo cuti'),
        const SizedBox(height: 10),
        SizedBox(
          height: 88,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: balances.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, i) {
              final b = balances[i] as Map<String, dynamic>;
              return Container(
                width: 140,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '${b['leave_type_code'] ?? '—'}',
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: AppColors.accent,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Sisa ${b['remaining']} hari',
                      style: const TextStyle(fontSize: 14, color: AppColors.textSecondary),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _TodaySummary extends StatelessWidget {
  const _TodaySummary({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final shift = data['today_shift'] as Map<String, dynamic>?;
    final payslip = data['latest_payslip'] as Map<String, dynamic>?;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Informasi hari ini'),
        const SizedBox(height: 10),
        if (shift != null)
          HrisCard(
            onTap: () => context.push('/profile'),
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.infoSoft,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.schedule, color: AppColors.info),
              ),
              title: Text('Shift ${shift['shift_code'] ?? '—'}'),
              subtitle: Text('${shift['shift_name'] ?? ''}'),
            ),
          ),
        if (payslip != null) ...[
          const SizedBox(height: 10),
          HrisCard(
            onTap: () => context.push('/payslips'),
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.successSoft,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.payments_outlined, color: AppColors.success),
              ),
              title: const Text('Slip gaji terakhir'),
              subtitle: Text(
                '${payslip['period_start']} — ${payslip['period_end']}\nNet: Rp ${payslip['net_amount']}',
              ),
            ),
          ),
        ],
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _InfoChip(
                icon: Icons.notifications,
                label: 'Notifikasi baru',
                value: '${data['unread_notifications'] ?? 0}',
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _InfoChip(
                icon: Icons.campaign,
                label: 'Pengumuman',
                value: '${data['active_announcements'] ?? 0}',
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return HrisCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Icon(icon, color: AppColors.accent, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                Text(
                  value,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentNotifications extends StatelessWidget {
  const _RecentNotifications({required this.items});

  final List items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Notifikasi terbaru',
          trailing: TextButton(
            onPressed: () => context.push('/notifications'),
            child: const Text('Lihat semua'),
          ),
        ),
        const SizedBox(height: 8),
        ...items.take(3).map((n) {
          final item = n as Map<String, dynamic>;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: HrisCard(
              onTap: () => context.push('/notifications'),
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  item['title'] ?? '',
                  style: TextStyle(
                    fontWeight: item['is_read'] == true ? FontWeight.w500 : FontWeight.w700,
                  ),
                ),
                subtitle: Text(
                  item['message'] ?? '',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: item['is_read'] == true
                    ? null
                    : Container(
                        width: 10,
                        height: 10,
                        decoration: const BoxDecoration(
                          color: AppColors.accent,
                          shape: BoxShape.circle,
                        ),
                      ),
              ),
            ),
          );
        }),
      ],
    );
  }
}
