import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

final overtimeRequestsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/overtime-requests/');
});

class OvertimeScreen extends ConsumerWidget {
  const OvertimeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(overtimeRequestsProvider);
    final fmt = DateFormat('dd MMM yyyy');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('PENGAJUAN LEMBUR'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context.push('/overtime/new'),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.black,
        onPressed: () => context.push('/overtime/new'),
        icon: const Icon(Icons.add),
        label: const Text('AJUKAN'),
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(overtimeRequestsProvider),
        child: requests.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat', subtitle: '$e'),
            ],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  EmptyState(
                    icon: Icons.more_time,
                    title: 'Belum ada pengajuan lembur',
                  ),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final req = items[i] as Map<String, dynamic>;
                final status = req['status'] as String? ?? '';
                return IndustrialCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              fmt.format(DateTime.parse(req['work_date'] as String)),
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
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      Text(
                        'Kompensasi: ${req['compensation_mode'] == 'leave' ? 'Jatah Cuti' : 'Diuangkan'}',
                        style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                      if ((req['reason'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 6),
                        Text(req['reason'] as String),
                      ],
                      if (status == 'pending') ...[
                        const SizedBox(height: 12),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: () => _cancel(context, ref, req['id'] as int),
                            child: const Text('Batalkan'),
                          ),
                        ),
                      ],
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

  Future<void> _cancel(BuildContext context, WidgetRef ref, int id) async {
    try {
      await ref.read(apiClientProvider).postEmpty('/overtime-requests/$id/cancel/');
      ref.invalidate(overtimeRequestsProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan lembur dibatalkan.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }
}
