import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

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

    return RefreshIndicator(
      color: AppColors.accent,
      onRefresh: () async => ref.invalidate(dashboardProvider),
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverAppBar(
            floating: true,
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'DASHBOARD',
                  style: GoogleFonts.orbitron(fontSize: 16, letterSpacing: 2),
                ),
                Text(
                  name,
                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ],
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () => context.push('/notifications'),
              ),
              IconButton(
                icon: const Icon(Icons.campaign_outlined),
                onPressed: () => context.push('/announcements'),
              ),
            ],
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
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
                  _PunchHero(data: data),
                  const SizedBox(height: 16),
                  _QuickActions(),
                  const SizedBox(height: 16),
                  if ((data['leave_balances'] as List?)?.isNotEmpty ?? false)
                    _LeaveBalanceStrip(
                      balances: data['leave_balances'] as List,
                    ),
                  const SizedBox(height: 16),
                  _InfoTiles(data: data),
                  const SizedBox(height: 16),
                  if ((data['recent_notifications'] as List?)?.isNotEmpty ?? false)
                    _RecentNotifications(
                      items: data['recent_notifications'] as List,
                    ),
                ]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PunchHero extends StatelessWidget {
  const _PunchHero({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final punchUi = data['punch_ui'] as Map<String, dynamic>? ?? {};
    final status = punchUi['status'] as String? ?? 'pending';
    final record = data['today_record'] as Map<String, dynamic>?;
    final fmt = DateFormat('HH:mm');

    String statusLabel;
    Color accent;
    switch (status) {
      case 'in':
        statusLabel = 'SEDANG BEKERJA';
        accent = AppColors.success;
      case 'out':
        statusLabel = 'SUDAH PULANG';
        accent = AppColors.cyan;
      default:
        statusLabel = 'BELUM ABSEN';
        accent = AppColors.warning;
    }

    return IndustrialCard(
      accentColor: accent,
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      statusLabel,
                      style: GoogleFonts.orbitron(
                        color: accent,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.5,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (record?['check_in'] != null)
                      Text(
                        'Masuk: ${fmt.format(DateTime.parse(record!['check_in'] as String).toLocal())}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                    if (record?['check_out'] != null)
                      Text(
                        'Pulang: ${fmt.format(DateTime.parse(record!['check_out'] as String).toLocal())}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                  ],
                ),
              ),
              StatusBadge(status: status == 'in' ? 'in' : status),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: NeonButton(
                  label: 'Clock In',
                  icon: Icons.login,
                  onPressed: () => context.push('/punch?action=in'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: NeonButton(
                  label: 'Clock Out',
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
    final actions = [
      ('Cuti', Icons.beach_access, '/leave/new', AppColors.cyan),
      ('Lembur', Icons.more_time, '/overtime/new', AppColors.accent),
      ('Slip Gaji', Icons.receipt_long, '/payslips', AppColors.success),
      ('Profil', Icons.badge_outlined, '/profile', AppColors.info),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Aksi Cepat'),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 4,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 0.85,
          children: actions.map((a) {
            return IndustrialCard(
              padding: const EdgeInsets.all(10),
              accentColor: a.$4,
              onTap: () => context.push(a.$3),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(a.$2, color: a.$4, size: 24),
                  const SizedBox(height: 8),
                  Text(
                    a.$1,
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}

class _LeaveBalanceStrip extends StatelessWidget {
  const _LeaveBalanceStrip({required this.balances});

  final List balances;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Saldo Cuti'),
        const SizedBox(height: 12),
        SizedBox(
          height: 90,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: balances.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, i) {
              final b = balances[i] as Map<String, dynamic>;
              return IndustrialCard(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                accentColor: AppColors.cyan,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '${b['leave_type_code'] ?? b['code'] ?? '—'}',
                      style: GoogleFonts.orbitron(
                        fontWeight: FontWeight.w700,
                        color: AppColors.cyan,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Sisa ${b['remaining']} hari',
                      style: const TextStyle(fontSize: 13),
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

class _InfoTiles extends StatelessWidget {
  const _InfoTiles({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final shift = data['today_shift'] as Map<String, dynamic>?;
    final payslip = data['latest_payslip'] as Map<String, dynamic>?;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Ringkasan Hari Ini'),
        const SizedBox(height: 12),
        if (shift != null)
          IndustrialCard(
            accentColor: AppColors.info,
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.schedule, color: AppColors.info),
              title: Text('Shift ${shift['shift_code'] ?? '—'}'),
              subtitle: Text(
                '${shift['shift_name'] ?? ''}\n${shift['scheduled_check_in'] ?? ''} — ${shift['scheduled_check_out'] ?? ''}',
              ),
            ),
          ),
        if (payslip != null) ...[
          const SizedBox(height: 10),
          IndustrialCard(
            accentColor: AppColors.success,
            onTap: () => context.push('/payslips'),
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.payments_outlined, color: AppColors.success),
              title: const Text('Slip Gaji Terakhir'),
              subtitle: Text(
                'Periode ${payslip['period_start']} — ${payslip['period_end']}\nNet: Rp ${payslip['net_amount']}',
              ),
            ),
          ),
        ],
        const SizedBox(height: 10),
        IndustrialCard(
          child: Row(
            children: [
              _StatChip(
                label: 'Notifikasi',
                value: '${data['unread_notifications'] ?? 0}',
                color: AppColors.warning,
              ),
              const SizedBox(width: 12),
              _StatChip(
                label: 'Pengumuman',
                value: '${data['active_announcements'] ?? 0}',
                color: AppColors.cyan,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
            Text(
              value,
              style: GoogleFonts.orbitron(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: color,
              ),
            ),
          ],
        ),
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
          title: 'Notifikasi Terbaru',
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
            child: IndustrialCard(
              onTap: () => context.push('/notifications'),
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(item['title'] ?? ''),
                subtitle: Text(
                  item['message'] ?? '',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: item['is_read'] == true
                    ? null
                    : Container(
                        width: 8,
                        height: 8,
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
