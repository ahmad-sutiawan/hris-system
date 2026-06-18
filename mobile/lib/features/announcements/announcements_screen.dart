import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';

final announcementsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/announcements/');
});

class AnnouncementsScreen extends ConsumerWidget {
  const AnnouncementsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final announcements = ref.watch(announcementsProvider);
    final fmt = DateFormat('dd MMM yyyy');

    return HrisScaffold(
      appBar: hrisAppBar(title: 'Pengumuman'),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(announcementsProvider),
        child: announcements.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [EmptyState(icon: Icons.error_outline, title: 'Gagal memuat', subtitle: '$e')],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  EmptyState(icon: Icons.campaign_outlined, title: 'Tidak ada pengumuman aktif'),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final a = items[i] as Map<String, dynamic>;
                final priority = a['priority'] as String? ?? 'normal';
                Color accent = AppColors.info;
                if (priority == 'critical') accent = AppColors.error;
                if (priority == 'high') accent = AppColors.warning;

                return HrisCard(
                  accentColor: accent,
                  onTap: () => context.push('/announcements/${a['id']}'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (a['is_pinned'] == true)
                            const Padding(
                              padding: EdgeInsets.only(right: 6),
                              child: Icon(Icons.push_pin, size: 14, color: AppColors.accent),
                            ),
                          Expanded(
                            child: Text(
                              a['title'] ?? '',
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          StatusBadge(status: priority),
                        ],
                      ),
                      if ((a['summary'] as String?)?.isNotEmpty ?? false) ...[
                        const SizedBox(height: 8),
                        Text(
                          a['summary'] as String,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                      const SizedBox(height: 8),
                      Text(
                        fmt.format(DateTime.parse(a['publish_start'] as String).toLocal()),
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
}
