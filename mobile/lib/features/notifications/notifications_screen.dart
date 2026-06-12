import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

final notificationsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/notifications/');
});

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationsProvider);
    final fmt = DateFormat('dd MMM yyyy HH:mm');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('NOTIFIKASI'),
        actions: [
          TextButton(
            onPressed: () => _markAllRead(context, ref),
            child: const Text('Tandai semua'),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(notificationsProvider),
        child: notifications.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [EmptyState(icon: Icons.error_outline, title: 'Gagal memuat', subtitle: '$e')],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  EmptyState(icon: Icons.notifications_none, title: 'Tidak ada notifikasi'),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final n = items[i] as Map<String, dynamic>;
                final unread = n['is_read'] != true;
                return IndustrialCard(
                  accentColor: unread ? AppColors.accent : AppColors.border,
                  onTap: () => _markRead(ref, n['id'] as int),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              n['title'] ?? '',
                              style: TextStyle(
                                fontWeight: unread ? FontWeight.w700 : FontWeight.w500,
                              ),
                            ),
                          ),
                          if (unread)
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: AppColors.accent,
                                shape: BoxShape.circle,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(n['message'] ?? ''),
                      const SizedBox(height: 6),
                      Text(
                        fmt.format(DateTime.parse(n['created_at'] as String).toLocal()),
                        style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
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

  Future<void> _markRead(WidgetRef ref, int id) async {
    await ref.read(apiClientProvider).postEmpty('/notifications/$id/mark_read/');
    ref.invalidate(notificationsProvider);
  }

  Future<void> _markAllRead(BuildContext context, WidgetRef ref) async {
    await ref.read(apiClientProvider).postEmpty('/notifications/mark_all_read/');
    ref.invalidate(notificationsProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Semua notifikasi ditandai dibaca.')),
      );
    }
  }
}
