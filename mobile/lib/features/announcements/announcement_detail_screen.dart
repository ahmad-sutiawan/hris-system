import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import 'announcements_screen.dart';

class AnnouncementDetailScreen extends ConsumerWidget {
  const AnnouncementDetailScreen({super.key, required this.id});

  final int id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(_announcementDetailProvider(id));

    return HrisScaffold(
      appBar: hrisAppBar(title: 'Detail Pengumuman'),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => EmptyState(
          icon: Icons.error_outline,
          title: 'Gagal memuat',
          subtitle: '$e',
        ),
        data: (a) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            HrisCard(
              accentColor: AppColors.accent,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    a['title'] ?? '',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    a['body'] ?? '',
                    style: const TextStyle(height: 1.5),
                  ),
                  if ((a['external_link'] as String?)?.isNotEmpty ?? false) ...[
                    const SizedBox(height: 16),
                    PrimaryButton(
                      label: a['action_label'] as String? ?? 'Buka tautan',
                      secondary: true,
                      icon: Icons.open_in_new,
                      onPressed: () async {
                        final uri = Uri.tryParse(a['external_link'] as String);
                        if (uri != null && await canLaunchUrl(uri)) {
                          await launchUrl(uri, mode: LaunchMode.externalApplication);
                        }
                      },
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),
            PrimaryButton(
              label: 'Tutup Banner',
              onPressed: () async {
                await ref.read(apiClientProvider).postEmpty('/announcements/$id/dismiss/');
                ref.invalidate(announcementsProvider);
                if (context.mounted) context.pop();
              },
            ),
          ],
        ),
      ),
    );
  }
}

final _announcementDetailProvider =
    FutureProvider.family<Map<String, dynamic>, int>((ref, id) async {
  return ref.watch(apiClientProvider).get('/announcements/$id/');
});
