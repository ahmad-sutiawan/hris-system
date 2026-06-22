import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/employee_avatar.dart';
import '../../core/widgets/hris_widgets.dart';

final employeeDetailProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, id) async {
  return ref.watch(apiClientProvider).get('/employees/$id/');
});

class EmployeeDetailScreen extends ConsumerWidget {
  const EmployeeDetailScreen({super.key, required this.employeeId});

  final int employeeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(employeeDetailProvider(employeeId));
    final fmt = DateFormat('dd MMM yyyy');

    return HrisScaffold(
      appBar: hrisAppBar(title: 'Profil Karyawan'),
      body: RefreshIndicator(
        color: AppColors.chinaRed,
        onRefresh: () async => ref.invalidate(employeeDetailProvider(employeeId)),
        child: detail.when(
          loading: () => const Center(child: CircularProgressIndicator(color: AppColors.chinaRed)),
          error: (e, _) => ListView(
            children: [
              EmptyState(
                icon: Icons.error_outline_rounded,
                title: 'Gagal memuat profil',
                subtitle: '$e',
              ),
            ],
          ),
          data: (emp) {
            final joinDate = emp['join_date'] as String?;
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: AppColors.headerGradient,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Column(
                    children: [
                      EmployeeAvatar(
                        photoUrl: emp['photo_url'] as String?,
                        name: emp['full_name'] as String? ?? '?',
                        size: 68,
                        backgroundColor: Colors.white.withValues(alpha: 0.18),
                        textColor: Colors.white,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        emp['full_name'] as String? ?? '—',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.plusJakartaSans(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 20,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        emp['employee_id'] as String? ?? '—',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.88)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                _InfoCard(
                  rows: [
                    _InfoRow('Branch', '${emp['plant_code'] ?? '—'} · ${emp['plant_name'] ?? ''}'),
                    _InfoRow('Department', emp['department_name'] as String? ?? '—'),
                    _InfoRow('Position', emp['job_title'] as String? ?? '—'),
                    _InfoRow('Atasan', emp['manager_name'] as String? ?? '—'),
                    _InfoRow('Email', emp['email'] as String? ?? '—'),
                    _InfoRow('Telepon', emp['phone'] as String? ?? '—'),
                    _InfoRow(
                      'Bergabung',
                      joinDate == null ? '—' : fmt.format(DateTime.parse(joinDate)),
                    ),
                    _InfoRow('Status', emp['status'] as String? ?? '—'),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.rows});

  final List<_InfoRow> rows;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          for (var i = 0; i < rows.length; i++) ...[
            if (i > 0) const Divider(height: 20),
            rows[i],
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 92,
          child: Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        ),
        Expanded(
          child: Text(
            value,
            style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600, fontSize: 14),
          ),
        ),
      ],
    );
  }
}
