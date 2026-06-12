import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

final timesheetsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/timesheets/');
});

class AttendanceScreen extends ConsumerWidget {
  const AttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final timesheets = ref.watch(timesheetsProvider);
    final fmtDate = DateFormat('dd MMM yyyy');
    final fmtTime = DateFormat('HH:mm');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('REKAP ABSENSI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.fingerprint),
            onPressed: () => context.push('/punch?action=in'),
            tooltip: 'Absen',
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(timesheetsProvider),
        child: timesheets.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              EmptyState(
                icon: Icons.error_outline,
                title: 'Gagal memuat data',
                subtitle: '$e',
              ),
            ],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  EmptyState(
                    icon: Icons.calendar_today_outlined,
                    title: 'Belum ada rekap absensi',
                  ),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final ts = items[i] as Map<String, dynamic>;
                final workDate = DateTime.parse(ts['work_date'] as String);
                return IndustrialCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              fmtDate.format(workDate),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 15,
                              ),
                            ),
                          ),
                          if (ts['attendance_code'] != null)
                            StatusBadge(status: '${ts['attendance_code']}'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Shift: ${ts['shift_code'] ?? '—'} ${ts['shift_label'] ?? ''}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          _TimeChip(
                            label: 'Masuk',
                            value: ts['check_in'] != null
                                ? fmtTime.format(
                                    DateTime.parse(ts['check_in'] as String).toLocal(),
                                  )
                                : '—',
                          ),
                          const SizedBox(width: 12),
                          _TimeChip(
                            label: 'Pulang',
                            value: ts['check_out'] != null
                                ? fmtTime.format(
                                    DateTime.parse(ts['check_out'] as String).toLocal(),
                                  )
                                : '—',
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Jam kerja: ${ts['paid_working_hours'] ?? '0'} jam · '
                        'Telat: ${ts['late_in_minutes'] ?? 0} m · '
                        'OT: ${(ts['ot_before_minutes'] ?? 0) + (ts['ot_after_minutes'] ?? 0)} m',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _TimeChip extends StatelessWidget {
  const _TimeChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.bgPanel,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}
