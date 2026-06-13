import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../../core/widgets/talenta_widgets.dart';

final notificationsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/notifications/');
});

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationsProvider);
    final fmt = DateFormat('dd MMM yyyy HH:mm');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text(
          embedded ? 'Kotak Masuk' : 'Notifikasi',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
        ),
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
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat', subtitle: '$e'),
            ],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  EmptyState(
                    icon: Icons.mail_outline_rounded,
                    title: 'Kotak masuk kosong',
                    subtitle: 'Notifikasi HR akan muncul di sini',
                  ),
                ],
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.only(top: 8, bottom: 24),
              itemCount: items.length,
              itemBuilder: (context, i) {
                final n = items[i] as Map<String, dynamic>;
                final unread = n['is_read'] != true;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: InboxPreviewTile(
                    title: n['title'] ?? '',
                    message: '${n['message'] ?? ''}\n${fmt.format(DateTime.parse(n['created_at'] as String).toLocal())}',
                    unread: unread,
                    onTap: () => _markRead(ref, n['id'] as int),
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
