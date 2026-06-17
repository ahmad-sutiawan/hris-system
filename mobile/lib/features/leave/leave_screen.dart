import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';

final leaveRequestsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/leave-requests/');
});

final leaveBalancesProvider = FutureProvider<List<dynamic>>((ref) async {
  final year = DateTime.now().year;
  return ref.watch(apiClientProvider).getPaginated(
        '/leave-balances/',
        query: {'year': year},
      );
});

class LeaveScreen extends ConsumerWidget {
  const LeaveScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(leaveRequestsProvider);
    final balances = ref.watch(leaveBalancesProvider);
    final myEmployeeId = ref.watch(authProvider).employee?['id'] as int?;
    final fmt = DateFormat('dd MMM yyyy');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Pengajuan Cuti'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context.push('/leave/new'),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.accent,
        foregroundColor: AppColors.onPrimary,
        onPressed: () => context.push('/leave/new'),
        icon: const Icon(Icons.add),
        label: const Text('Ajukan'),
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async {
          ref.invalidate(leaveRequestsProvider);
          ref.invalidate(leaveBalancesProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            balances.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (items) {
                if (items.isEmpty) return const SizedBox.shrink();
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeader(title: 'Saldo Cuti'),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: items.map((b) {
                        final bal = b as Map<String, dynamic>;
                        return Chip(
                          label: Text(
                            '${bal['leave_type_code']}: ${bal['remaining']} hari',
                          ),
                          backgroundColor: AppColors.surfaceMuted,
                          side: const BorderSide(color: AppColors.border),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 20),
                  ],
                );
              },
            ),
            const SectionHeader(title: 'Riwayat Pengajuan'),
            const SizedBox(height: 10),
            requests.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => EmptyState(
                icon: Icons.error_outline,
                title: 'Gagal memuat',
                subtitle: '$e',
              ),
              data: (items) {
                if (items.isEmpty) {
                  return const EmptyState(
                    icon: Icons.beach_access,
                    title: 'Belum ada pengajuan cuti',
                  );
                }
                return Column(
                  children: items.map((item) {
                    final req = item as Map<String, dynamic>;
                    final status = req['status'] as String? ?? '';
                    final canApprove = req['can_approve'] == true;
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
                                    employeeName != null && !isOwn
                                        ? '$employeeName · ${req['leave_type_code']}'
                                        : '${req['leave_type_code']} · ${req['days']} hari',
                                    style: const TextStyle(fontWeight: FontWeight.w700),
                                  ),
                                ),
                                StatusBadge(status: status),
                              ],
                            ),
                            if (employeeName != null && !isOwn) ...[
                              const SizedBox(height: 4),
                              Text(
                                '${req['days']} hari',
                                style: const TextStyle(color: AppColors.textSecondary),
                              ),
                            ],
                            const SizedBox(height: 6),
                            Text(
                              '${fmt.format(DateTime.parse(req['start_date'] as String))} — '
                              '${fmt.format(DateTime.parse(req['end_date'] as String))}',
                              style: const TextStyle(color: AppColors.textSecondary),
                            ),
                            if ((req['reason'] as String?)?.isNotEmpty ?? false) ...[
                              const SizedBox(height: 6),
                              Text(req['reason'] as String),
                            ],
                            if (status == 'pending' && canApprove) ...[
                              const SizedBox(height: 12),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  TextButton(
                                    onPressed: () => _reject(context, ref, req['id'] as int),
                                    child: const Text('Tolak'),
                                  ),
                                  const SizedBox(width: 8),
                                  FilledButton(
                                    onPressed: () => _approve(context, ref, req['id'] as int),
                                    child: const Text('Setujui'),
                                  ),
                                ],
                              ),
                            ] else if (status == 'pending' && isOwn) ...[
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
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _approve(BuildContext context, WidgetRef ref, int id) async {
    try {
      await ref.read(apiClientProvider).postEmpty('/leave-requests/$id/approve/');
      ref.invalidate(leaveRequestsProvider);
      ref.invalidate(leaveBalancesProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan cuti disetujui.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }

  Future<void> _reject(BuildContext context, WidgetRef ref, int id) async {
    try {
      await ref.read(apiClientProvider).post('/leave-requests/$id/reject/', body: {});
      ref.invalidate(leaveRequestsProvider);
      ref.invalidate(leaveBalancesProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan cuti ditolak.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }

  Future<void> _cancel(BuildContext context, WidgetRef ref, int id) async {
    try {
      await ref.read(apiClientProvider).postEmpty('/leave-requests/$id/cancel/');
      ref.invalidate(leaveRequestsProvider);
      ref.invalidate(leaveBalancesProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan cuti dibatalkan.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }
}
