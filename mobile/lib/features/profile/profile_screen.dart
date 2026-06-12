import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

final profileProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getProfile();
});

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('DETAIL KARYAWAN')),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(profileProvider),
        child: profile.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat profil', subtitle: '$e'),
            ],
          ),
          data: (data) {
            final emp = data['employee'] as Map<String, dynamic>;
            final stats = data['month_stats'] as Map<String, dynamic>? ?? {};
            final balances = data['leave_balances'] as List? ?? [];
            final shifts = data['upcoming_shifts'] as List? ?? [];
            final fmt = DateFormat('dd MMM');

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                IndustrialCard(
                  accentColor: AppColors.accent,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        emp['full_name'] ?? '',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${emp['employee_id']} · ${emp['status_label'] ?? emp['status']}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 12),
                      _InfoRow('Plant', emp['plant']),
                      _InfoRow('Departemen', emp['department']),
                      _InfoRow('Jabatan', emp['job_title']),
                      _InfoRow('Grade', emp['grade']),
                      _InfoRow('Atasan', emp['manager_name']),
                      _InfoRow('Email', emp['email']),
                      _InfoRow('Telepon', emp['phone']),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const SectionHeader(title: 'Statistik Bulan Ini'),
                const SizedBox(height: 10),
                IndustrialCard(
                  child: Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      _StatTile('Hadir', '${stats['present_days'] ?? 0} hari'),
                      _StatTile('Alpha', '${stats['alpha_days'] ?? 0} hari'),
                      _StatTile('Telat', '${stats['late_minutes'] ?? 0} m'),
                      _StatTile('OT', '${(stats['ot_before_minutes'] ?? 0) + (stats['ot_after_minutes'] ?? 0)} m'),
                    ],
                  ),
                ),
                if (balances.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Saldo Cuti'),
                  const SizedBox(height: 10),
                  ...balances.map((b) {
                    final bal = b as Map<String, dynamic>;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: IndustrialCard(
                        child: Text(
                          '${bal['leave_type_code']}: sisa ${bal['remaining']} hari '
                          '(pending ${bal['pending']})',
                        ),
                      ),
                    );
                  }),
                ],
                if (shifts.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Jadwal Shift (14 hari)'),
                  const SizedBox(height: 10),
                  ...shifts.map((s) {
                    final shift = s as Map<String, dynamic>;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: IndustrialCard(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(fmt.format(DateTime.parse(shift['work_date'] as String))),
                          subtitle: Text(
                            '${shift['shift_code']} — ${shift['shift_name'] ?? ''}',
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final dynamic value;

  @override
  Widget build(BuildContext context) {
    if (value == null || '$value'.isEmpty || value == '—') {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
          ),
          Expanded(child: Text('$value')),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 140,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.bgPanel,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
