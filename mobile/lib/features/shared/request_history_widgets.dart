import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../leave/leave_screen.dart';
import '../overtime/overtime_screen.dart';

class LeaveRequestHistorySection extends ConsumerWidget {
  const LeaveRequestHistorySection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(leaveRequestsProvider);
    final myEmployeeId = ref.watch(authProvider).employee?['id'] as int?;
    final isManagerView = ref.watch(authProvider).user?['role'] == 'manager' ||
        ref.watch(authProvider).user?['role'] == 'hr' ||
        ref.watch(authProvider).user?['role'] == 'admin';
    final fmt = DateFormat('dd MMM yyyy');
    final dtFmt = DateFormat('dd MMM yyyy HH:mm');

    return requests.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (items) {
        if (items.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 24),
            SectionHeader(title: 'Riwayat Pengajuan Cuti (${items.length})'),
            const SizedBox(height: 10),
            ...items.map((item) {
              final req = item as Map<String, dynamic>;
              final status = req['status'] as String? ?? '';
              final employeeName = req['employee_name'] as String?;
              final isOwn = myEmployeeId != null && req['employee'] == myEmployeeId;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: HrisCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              isManagerView && employeeName != null && !isOwn
                                  ? employeeName
                                  : '${req['leave_type_code']} — ${req['days']} hari',
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          StatusBadge(status: status),
                        ],
                      ),
                      const SizedBox(height: 6),
                      if (isManagerView && employeeName != null && !isOwn)
                        Text(
                          '${req['leave_type_code']} · ${req['days']} hari',
                          style: const TextStyle(color: AppColors.textSecondary),
                        ),
                      Text(
                        '${fmt.format(DateTime.parse(req['start_date'] as String))} — '
                        '${fmt.format(DateTime.parse(req['end_date'] as String))}'
                        '${req['is_half_day'] == true ? ' · Setengah hari' : ''}',
                        style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                      ),
                      if ((req['reason'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 4),
                        Text('Alasan: ${req['reason']}', style: const TextStyle(fontSize: 13)),
                      ],
                      if (req['created_at'] != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Diajukan: ${dtFmt.format(DateTime.parse(req['created_at'] as String))}',
                          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                        ),
                      ],
                      if (req['approved_at'] != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          'Diproses: ${dtFmt.format(DateTime.parse(req['approved_at'] as String))}',
                          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                        ),
                      ],
                      if ((req['rejection_reason'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Catatan: ${req['rejection_reason']}',
                          style: const TextStyle(fontSize: 12, color: AppColors.warning),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
          ],
        );
      },
    );
  }
}

class OvertimeRequestHistorySection extends ConsumerWidget {
  const OvertimeRequestHistorySection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(overtimeRequestsProvider);
    final myEmployeeId = ref.watch(authProvider).employee?['id'] as int?;
    final isManagerView = ref.watch(authProvider).user?['role'] == 'manager' ||
        ref.watch(authProvider).user?['role'] == 'hr' ||
        ref.watch(authProvider).user?['role'] == 'admin';
    final fmt = DateFormat('dd MMM yyyy');
    final dtFmt = DateFormat('dd MMM yyyy HH:mm');

    return requests.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (items) {
        if (items.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 24),
            SectionHeader(title: 'Riwayat Pengajuan Lembur (${items.length})'),
            const SizedBox(height: 10),
            ...items.map((item) {
              final req = item as Map<String, dynamic>;
              final status = req['status'] as String? ?? '';
              final employeeName = req['employee_name'] as String?;
              final isOwn = myEmployeeId != null && req['employee'] == myEmployeeId;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: HrisCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              isManagerView && employeeName != null && !isOwn
                                  ? employeeName
                                  : fmt.format(DateTime.parse(req['work_date'] as String)),
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          StatusBadge(status: status),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${req['overtime_type_code'] ?? '—'} · '
                        'Sebelum: ${req['ot_before_minutes']} m · '
                        'Sesudah: ${req['ot_after_minutes']} m',
                        style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                      ),
                      Text(
                        'Kompensasi: ${req['compensation_mode'] == 'leave' ? 'Jatah Cuti' : 'Diuangkan'}',
                        style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                      if ((req['reason'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 4),
                        Text('Alasan: ${req['reason']}', style: const TextStyle(fontSize: 13)),
                      ],
                      if (req['created_at'] != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Diajukan: ${dtFmt.format(DateTime.parse(req['created_at'] as String))}',
                          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                        ),
                      ],
                      if (req['approved_at'] != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          'Diproses: ${dtFmt.format(DateTime.parse(req['approved_at'] as String))}',
                          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                        ),
                      ],
                      if ((req['rejection_reason'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Catatan: ${req['rejection_reason']}',
                          style: const TextStyle(fontSize: 12, color: AppColors.warning),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
          ],
        );
      },
    );
  }
}
