import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/animated_interactions.dart';
import '../../core/widgets/hris_widgets.dart';

enum InboxFilter { all, unread, leave, attendance, payroll, system }

final inboxFilterProvider = StateProvider<InboxFilter>((ref) => InboxFilter.all);

final notificationsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginatedAll('/notifications/', pageSize: 50);
});

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(inboxFilterProvider);
    final notifications = ref.watch(notificationsProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text(
          embedded ? 'Kotak Masuk' : 'Notifikasi',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
        ),
        actions: [
          AnimatedPress(
            onTap: () => _markAllRead(context, ref),
            scale: 0.94,
            child: Container(
              margin: const EdgeInsets.only(right: 12),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.darkGoldLight,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.darkGold.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.done_all_rounded, size: 16, color: AppColors.darkGoldRich),
                  const SizedBox(width: 4),
                  Text(
                    'Tandai semua',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.darkGoldRich,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.chinaRed,
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
            final filtered = _applyFilter(items, filter);
            final stats = _computeStats(items);

            if (items.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  EmptyState(
                    icon: Icons.mail_outline_rounded,
                    title: 'Kotak masuk kosong',
                    subtitle: 'Notifikasi cuti, lembur, slip gaji, dan sistem akan muncul di sini',
                  ),
                ],
              );
            }

            final groups = _groupByDate(filtered);

            return CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: FadeSlideIn(
                    index: 0,
                    child: _InboxSummaryStrip(stats: stats),
                  ),
                ),
                SliverToBoxAdapter(
                  child: FadeSlideIn(
                    index: 1,
                    child: _InboxFilterBar(
                      active: filter,
                      stats: stats,
                      onSelect: (value) {
                        ref.read(inboxFilterProvider.notifier).state = value;
                      },
                    ),
                  ),
                ),
                if (filtered.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: EmptyState(
                      icon: Icons.filter_alt_off_rounded,
                      title: 'Tidak ada notifikasi',
                      subtitle: 'Coba ubah filter atau tandai semua sebagai dibaca',
                    ),
                  )
                else
                  ...groups.entries.expand((entry) {
                    final sectionIndex = groups.keys.toList().indexOf(entry.key);
                    return [
                      SliverToBoxAdapter(
                        child: FadeSlideIn(
                          index: sectionIndex + 2,
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                            child: Text(
                              entry.key,
                              style: GoogleFonts.plusJakartaSans(
                                fontWeight: FontWeight.w800,
                                fontSize: 13,
                                color: AppColors.darkGoldRich,
                              ),
                            ),
                          ),
                        ),
                      ),
                      SliverPadding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        sliver: SliverList(
                          delegate: SliverChildBuilderDelegate(
                            (context, i) {
                              final item = entry.value[i] as Map<String, dynamic>;
                              return FadeSlideIn(
                                index: i + sectionIndex * 3,
                                delayMs: 25,
                                child: Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: _InboxNotificationCard(
                                    data: item,
                                    onTap: () => _openDetail(context, ref, item),
                                  ),
                                ),
                              );
                            },
                            childCount: entry.value.length,
                          ),
                        ),
                      ),
                    ];
                  }),
                const SliverToBoxAdapter(child: SizedBox(height: 100)),
              ],
            );
          },
        ),
      ),
    );
  }

  static List<dynamic> _applyFilter(List<dynamic> items, InboxFilter filter) {
    return items.where((raw) {
      final n = raw as Map<String, dynamic>;
      final category = '${n['category']}';
      final unread = n['is_read'] != true;
      switch (filter) {
        case InboxFilter.all:
          return true;
        case InboxFilter.unread:
          return unread;
        case InboxFilter.leave:
          return category == 'leave';
        case InboxFilter.attendance:
          return category == 'attendance';
        case InboxFilter.payroll:
          return category == 'payroll';
        case InboxFilter.system:
          return category == 'system';
      }
    }).toList();
  }

  static _InboxStats _computeStats(List<dynamic> items) {
    var unread = 0;
    var leave = 0;
    var attendance = 0;
    var payroll = 0;
    var system = 0;
    for (final raw in items) {
      final n = raw as Map<String, dynamic>;
      if (n['is_read'] != true) unread += 1;
      switch ('${n['category']}') {
        case 'leave':
          leave += 1;
          break;
        case 'attendance':
          attendance += 1;
          break;
        case 'payroll':
          payroll += 1;
          break;
        case 'system':
          system += 1;
          break;
      }
    }
    return _InboxStats(
      total: items.length,
      unread: unread,
      leave: leave,
      attendance: attendance,
      payroll: payroll,
      system: system,
    );
  }

  static Map<String, List<dynamic>> _groupByDate(List<dynamic> items) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));
    final weekStart = today.subtract(Duration(days: today.weekday - 1));
    final fmt = DateFormat('EEEE, dd MMM yyyy');

    final groups = <String, List<dynamic>>{};
    for (final raw in items) {
      final n = raw as Map<String, dynamic>;
      final created = DateTime.parse(n['created_at'] as String).toLocal();
      final day = DateTime(created.year, created.month, created.day);
      late String label;
      if (day == today) {
        label = 'Hari ini';
      } else if (day == yesterday) {
        label = 'Kemarin';
      } else if (day.isAfter(weekStart.subtract(const Duration(days: 1)))) {
        label = 'Minggu ini';
      } else {
        label = fmt.format(created);
      }
      groups.putIfAbsent(label, () => []).add(n);
    }
    return groups;
  }

  static Future<void> _openDetail(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> item,
  ) async {
    if (item['is_read'] != true) {
      await _markRead(ref, item['id'] as int);
    }
    if (!context.mounted) return;

    final meta = _categoryMeta('${item['category']}');
    final created = DateTime.parse(item['created_at'] as String).toLocal();
    final readAt = item['read_at'] != null
        ? DateTime.parse(item['read_at'] as String).toLocal()
        : null;
    final route = resolveNotificationRoute(item['link'] as String?);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.55,
        minChildSize: 0.4,
        maxChildSize: 0.92,
        builder: (_, scrollController) {
          return Container(
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: ListView(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppColors.border,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: meta.bg,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: meta.color.withValues(alpha: 0.25)),
                      ),
                      child: Icon(meta.icon, color: meta.color, size: 24),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            meta.label,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: meta.color,
                            ),
                          ),
                          Text(
                            item['title'] ?? '',
                            style: GoogleFonts.plusJakartaSans(
                              fontWeight: FontWeight.w800,
                              fontSize: 17,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _DetailMetaRow(
                  icon: Icons.schedule_rounded,
                  label: 'Diterima',
                  value: '${DateFormat('dd MMM yyyy, HH:mm').format(created)} · ${relativeTime(created)}',
                ),
                if (readAt != null)
                  _DetailMetaRow(
                    icon: Icons.check_circle_outline_rounded,
                    label: 'Dibaca',
                    value: DateFormat('dd MMM yyyy, HH:mm').format(readAt),
                  ),
                _DetailMetaRow(
                  icon: item['is_read'] == true
                      ? Icons.mark_email_read_outlined
                      : Icons.mark_email_unread_outlined,
                  label: 'Status',
                  value: item['is_read'] == true ? 'Sudah dibaca' : 'Belum dibaca',
                ),
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceMuted,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.darkGoldMuted),
                  ),
                  child: Text(
                    item['message'] ?? '',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 14,
                      height: 1.55,
                      color: AppColors.text,
                    ),
                  ),
                ),
                if (route != null) ...[
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: AnimatedPress(
                      onTap: () {
                        Navigator.of(ctx).pop();
                        context.push(route);
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        decoration: BoxDecoration(
                          gradient: AppColors.headerGradient,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(meta.actionIcon, color: Colors.white, size: 18),
                            const SizedBox(width: 8),
                            Text(
                              meta.actionLabel,
                              style: GoogleFonts.plusJakartaSans(
                                color: Colors.white,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  static Future<void> _markRead(WidgetRef ref, int id) async {
    await ref.read(apiClientProvider).postEmpty('/notifications/$id/mark_read/');
    ref.invalidate(notificationsProvider);
  }

  Future<void> _markAllRead(BuildContext context, WidgetRef ref) async {
    await ref.read(apiClientProvider).postEmpty('/notifications/mark_all_read/');
    ref.invalidate(notificationsProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Semua notifikasi ditandai dibaca.',
            style: GoogleFonts.plusJakartaSans(),
          ),
          backgroundColor: AppColors.darkGoldRich,
        ),
      );
    }
  }
}

class _InboxStats {
  const _InboxStats({
    required this.total,
    required this.unread,
    required this.leave,
    required this.attendance,
    required this.payroll,
    required this.system,
  });

  final int total;
  final int unread;
  final int leave;
  final int attendance;
  final int payroll;
  final int system;
}

class _InboxSummaryStrip extends StatelessWidget {
  const _InboxSummaryStrip({required this.stats});

  final _InboxStats stats;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Expanded(
            child: _SummaryTile(
              label: 'Belum dibaca',
              value: '${stats.unread}',
              color: AppColors.chinaRed,
              highlight: stats.unread > 0,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SummaryTile(
              label: 'Total',
              value: '${stats.total}',
              color: AppColors.darkGold,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SummaryTile(
              label: 'Cuti',
              value: '${stats.leave}',
              color: AppColors.info,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SummaryTile(
              label: 'Gaji',
              value: '${stats.payroll}',
              color: AppColors.success,
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryTile extends StatelessWidget {
  const _SummaryTile({
    required this.label,
    required this.value,
    required this.color,
    this.highlight = false,
  });

  final String label;
  final String value;
  final Color color;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
      decoration: BoxDecoration(
        color: highlight ? color.withValues(alpha: 0.08) : AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: highlight ? color.withValues(alpha: 0.35) : color.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: GoogleFonts.plusJakartaSans(
              fontWeight: FontWeight.w800,
              fontSize: 16,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _InboxFilterBar extends StatelessWidget {
  const _InboxFilterBar({
    required this.active,
    required this.stats,
    required this.onSelect,
  });

  final InboxFilter active;
  final _InboxStats stats;
  final ValueChanged<InboxFilter> onSelect;

  @override
  Widget build(BuildContext context) {
    final chips = <({InboxFilter id, String label, int? count})>[
      (id: InboxFilter.all, label: 'Semua', count: stats.total),
      (id: InboxFilter.unread, label: 'Baru', count: stats.unread),
      (id: InboxFilter.leave, label: 'Cuti', count: stats.leave),
      (id: InboxFilter.attendance, label: 'Absensi', count: stats.attendance),
      (id: InboxFilter.payroll, label: 'Gaji', count: stats.payroll),
      (id: InboxFilter.system, label: 'Sistem', count: stats.system),
    ];

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: chips.map((chip) {
            final selected = active == chip.id;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: AnimatedPress(
                onTap: () => onSelect(chip.id),
                scale: 0.97,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(
                    gradient: selected ? AppColors.headerGradient : null,
                    color: selected ? null : AppColors.surface,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: selected
                          ? Colors.transparent
                          : AppColors.darkGold.withValues(alpha: 0.25),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        chip.label,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: selected ? Colors.white : AppColors.text,
                        ),
                      ),
                      if (chip.count != null && chip.count! > 0) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: selected
                                ? Colors.white.withValues(alpha: 0.25)
                                : AppColors.darkGoldLight,
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            '${chip.count}',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              color: selected ? Colors.white : AppColors.darkGoldRich,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

class _InboxNotificationCard extends StatelessWidget {
  const _InboxNotificationCard({
    required this.data,
    required this.onTap,
  });

  final Map<String, dynamic> data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final unread = data['is_read'] != true;
    final meta = _categoryMeta('${data['category']}');
    final created = DateTime.parse(data['created_at'] as String).toLocal();
    final hasAction = resolveNotificationRoute(data['link'] as String?) != null;

    return AnimatedPress(
      onTap: onTap,
      scale: 0.98,
      child: GoldPanel(
        padding: EdgeInsets.zero,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: unread
                ? Border.all(color: AppColors.chinaRed.withValues(alpha: 0.35), width: 1.5)
                : null,
          ),
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 4,
                  decoration: BoxDecoration(
                    color: unread ? AppColors.chinaRed : Colors.transparent,
                    borderRadius: const BorderRadius.horizontal(left: Radius.circular(16)),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: meta.bg,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(meta.icon, color: meta.color, size: 22),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      data['title'] ?? '',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontWeight: unread ? FontWeight.w800 : FontWeight.w700,
                                        fontSize: 14,
                                      ),
                                    ),
                                  ),
                                  if (unread)
                                    Container(
                                      width: 8,
                                      height: 8,
                                      margin: const EdgeInsets.only(left: 6),
                                      decoration: const BoxDecoration(
                                        color: AppColors.chinaRed,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                data['message'] ?? '',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 13,
                                  height: 1.4,
                                  color: AppColors.textMuted,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Wrap(
                                spacing: 8,
                                runSpacing: 4,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  _MiniTag(label: meta.label, color: meta.color),
                                  Text(
                                    relativeTime(created),
                                    style: const TextStyle(
                                      fontSize: 11,
                                      color: AppColors.textDim,
                                    ),
                                  ),
                                  if (hasAction)
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(meta.actionIcon, size: 12, color: meta.color),
                                        const SizedBox(width: 3),
                                        Text(
                                          meta.actionLabel,
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                            color: meta.color,
                                          ),
                                        ),
                                      ],
                                    ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded, color: AppColors.textDim, size: 20),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MiniTag extends StatelessWidget {
  const _MiniTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}

class _DetailMetaRow extends StatelessWidget {
  const _DetailMetaRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: AppColors.textDim),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 11, color: AppColors.textDim),
                ),
                Text(
                  value,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryMeta {
  const _CategoryMeta({
    required this.label,
    required this.icon,
    required this.color,
    required this.bg,
    required this.actionLabel,
    required this.actionIcon,
  });

  final String label;
  final IconData icon;
  final Color color;
  final Color bg;
  final String actionLabel;
  final IconData actionIcon;
}

_CategoryMeta _categoryMeta(String category) {
  switch (category) {
    case 'leave':
      return const _CategoryMeta(
        label: 'Cuti',
        icon: Icons.beach_access_rounded,
        color: AppColors.info,
        bg: AppColors.infoDim,
        actionLabel: 'Lihat cuti',
        actionIcon: Icons.arrow_forward_rounded,
      );
    case 'payroll':
      return const _CategoryMeta(
        label: 'Payroll',
        icon: Icons.receipt_long_rounded,
        color: AppColors.success,
        bg: AppColors.successDim,
        actionLabel: 'Lihat slip gaji',
        actionIcon: Icons.arrow_forward_rounded,
      );
    case 'attendance':
      return const _CategoryMeta(
        label: 'Absensi',
        icon: Icons.more_time_rounded,
        color: AppColors.darkGold,
        bg: AppColors.darkGoldLight,
        actionLabel: 'Lihat lembur',
        actionIcon: Icons.arrow_forward_rounded,
      );
    default:
      return const _CategoryMeta(
        label: 'Sistem',
        icon: Icons.notifications_active_rounded,
        color: AppColors.chinaRed,
        bg: AppColors.chinaRedLight,
        actionLabel: 'Buka',
        actionIcon: Icons.arrow_forward_rounded,
      );
  }
}

String relativeTime(DateTime dateTime) {
  final now = DateTime.now();
  final diff = now.difference(dateTime);
  if (diff.inMinutes < 1) return 'Baru saja';
  if (diff.inMinutes < 60) return '${diff.inMinutes} menit lalu';
  if (diff.inHours < 24) return '${diff.inHours} jam lalu';
  if (diff.inDays == 1) return 'Kemarin';
  if (diff.inDays < 7) return '${diff.inDays} hari lalu';
  return DateFormat('dd MMM yyyy').format(dateTime);
}

String? resolveNotificationRoute(String? link) {
  if (link == null || link.isEmpty) return null;
  final lower = link.toLowerCase();
  if (lower.contains('/leave')) return '/leave';
  if (lower.contains('/overtime')) return '/overtime';
  if (lower.contains('/payslip') || lower.contains('/payroll')) return '/payslips';
  if (lower.contains('/attendance')) return '/attendance';
  if (lower.contains('/announcement')) return '/announcements';
  return null;
}
