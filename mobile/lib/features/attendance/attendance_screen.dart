import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/animated_interactions.dart';
import '../../core/widgets/auth_media_image.dart';
import '../../core/widgets/hris_widgets.dart';

enum AttendanceRangePreset {
  week,
  month,
  quarter,
  custom,
}

class AttendanceDateFilter {
  const AttendanceDateFilter({
    required this.preset,
    this.from,
    this.to,
  });

  final AttendanceRangePreset preset;
  final DateTime? from;
  final DateTime? to;

  factory AttendanceDateFilter.thisMonth() {
    final now = DateTime.now();
    return AttendanceDateFilter(
      preset: AttendanceRangePreset.month,
      from: DateTime(now.year, now.month, 1),
      to: DateTime(now.year, now.month + 1, 0),
    );
  }

  AttendanceDateFilter copyWith({
    AttendanceRangePreset? preset,
    DateTime? from,
    DateTime? to,
  }) {
    return AttendanceDateFilter(
      preset: preset ?? this.preset,
      from: from ?? this.from,
      to: to ?? this.to,
    );
  }

  Map<String, dynamic> toQuery() {
    final fmt = DateFormat('yyyy-MM-dd');
    return {
      if (from != null) 'work_date_from': fmt.format(from!),
      if (to != null) 'work_date_to': fmt.format(to!),
    };
  }

  String label() {
    final fmt = DateFormat('dd MMM yyyy');
    switch (preset) {
      case AttendanceRangePreset.week:
        return '7 hari terakhir';
      case AttendanceRangePreset.month:
        return 'Bulan ${DateFormat('MMMM yyyy').format(from ?? DateTime.now())}';
      case AttendanceRangePreset.quarter:
        return '90 hari terakhir';
      case AttendanceRangePreset.custom:
        if (from != null && to != null) {
          return '${fmt.format(from!)} — ${fmt.format(to!)}';
        }
        return 'Rentang kustom';
    }
  }

  static AttendanceDateFilter forPreset(AttendanceRangePreset preset) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    switch (preset) {
      case AttendanceRangePreset.week:
        return AttendanceDateFilter(
          preset: preset,
          from: today.subtract(const Duration(days: 6)),
          to: today,
        );
      case AttendanceRangePreset.month:
        return AttendanceDateFilter.thisMonth();
      case AttendanceRangePreset.quarter:
        return AttendanceDateFilter(
          preset: preset,
          from: today.subtract(const Duration(days: 89)),
          to: today,
        );
      case AttendanceRangePreset.custom:
        return AttendanceDateFilter.thisMonth().copyWith(preset: preset);
    }
  }
}

final attendanceFilterProvider = StateProvider<AttendanceDateFilter>(
  (ref) => AttendanceDateFilter.thisMonth(),
);

final timesheetsProvider = FutureProvider<List<dynamic>>((ref) async {
  final filter = ref.watch(attendanceFilterProvider);
  return ref.watch(apiClientProvider).getPaginatedAll(
        '/timesheets/',
        query: filter.toQuery(),
        pageSize: 60,
      );
});

class AttendanceScreen extends ConsumerWidget {
  const AttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(attendanceFilterProvider);
    final timesheets = ref.watch(timesheetsProvider);

    return HrisScaffold(
      withBackground: false,
      appBar: hrisAppBar(
        title: 'Ringkasan Absensi',
        actions: [
          AnimatedPress(
            onTap: () => context.push('/punch?action=in'),
            scale: 0.92,
            child: Container(
              margin: const EdgeInsets.only(right: 12),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                gradient: AppColors.headerGradient,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                children: [
                  const Icon(Icons.fingerprint, color: Colors.white, size: 18),
                  const SizedBox(width: 6),
                  Text(
                    'Absen',
                    style: GoogleFonts.plusJakartaSans(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
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
        onRefresh: () async => ref.invalidate(timesheetsProvider),
        child: timesheets.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat data', subtitle: '$e'),
            ],
          ),
          data: (items) {
            final stats = _computeStats(items);
            return CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: FadeSlideIn(
                    index: 0,
                    child: _SummaryStrip(stats: stats),
                  ),
                ),
                SliverToBoxAdapter(
                  child: FadeSlideIn(
                    index: 1,
                    child: _FilterBar(
                      filter: filter,
                      onPreset: (preset) {
                        ref.read(attendanceFilterProvider.notifier).state =
                            AttendanceDateFilter.forPreset(preset);
                        ref.invalidate(timesheetsProvider);
                      },
                      onCustomRange: () async {
                        final picked = await _pickDateRange(context, filter);
                        if (picked != null) {
                          ref.read(attendanceFilterProvider.notifier).state = picked;
                          ref.invalidate(timesheetsProvider);
                        }
                      },
                    ),
                  ),
                ),
                if (items.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: EmptyState(
                      icon: Icons.event_busy_rounded,
                      title: 'Tidak ada data absensi',
                      subtitle: 'Coba ubah rentang tanggal filter',
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, i) {
                          final ts = items[i] as Map<String, dynamic>;
                          return FadeSlideIn(
                            index: i + 2,
                            delayMs: 30,
                            child: Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _TimesheetCard(data: ts),
                            ),
                          );
                        },
                        childCount: items.length,
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }

  static _AttendanceStats _computeStats(List<dynamic> items) {
    var present = 0;
    var lateMinutes = 0;
    var otMinutes = 0;
    var withPhotos = 0;
    for (final raw in items) {
      final ts = raw as Map<String, dynamic>;
      if (ts['check_in'] != null) present += 1;
      lateMinutes += ts['late_in_minutes'] as int? ?? 0;
      otMinutes += (ts['ot_before_minutes'] as int? ?? 0) + (ts['ot_after_minutes'] as int? ?? 0);
      if (ts['check_in_photo_url'] != null || ts['check_out_photo_url'] != null) {
        withPhotos += 1;
      }
    }
    return _AttendanceStats(
      totalDays: items.length,
      presentDays: present,
      lateMinutes: lateMinutes,
      otMinutes: otMinutes,
      withPhotos: withPhotos,
    );
  }

  static Future<AttendanceDateFilter?> _pickDateRange(
    BuildContext context,
    AttendanceDateFilter current,
  ) async {
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      initialDateRange: current.from != null && current.to != null
          ? DateTimeRange(start: current.from!, end: current.to!)
          : null,
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.light(
              primary: AppColors.chinaRed,
              onPrimary: Colors.white,
              secondary: AppColors.darkGold,
            ),
          ),
          child: child!,
        );
      },
    );
    if (range == null) return null;
    return AttendanceDateFilter(
      preset: AttendanceRangePreset.custom,
      from: range.start,
      to: range.end,
    );
  }
}

class _AttendanceStats {
  const _AttendanceStats({
    required this.totalDays,
    required this.presentDays,
    required this.lateMinutes,
    required this.otMinutes,
    required this.withPhotos,
  });

  final int totalDays;
  final int presentDays;
  final int lateMinutes;
  final int otMinutes;
  final int withPhotos;
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({required this.stats});

  final _AttendanceStats stats;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Expanded(child: _StatTile(label: 'Hari', value: '${stats.totalDays}', color: AppColors.chinaRed)),
          const SizedBox(width: 8),
          Expanded(child: _StatTile(label: 'Hadir', value: '${stats.presentDays}', color: AppColors.success)),
          const SizedBox(width: 8),
          Expanded(child: _StatTile(label: 'Telat', value: '${stats.lateMinutes}m', color: AppColors.darkGold)),
          const SizedBox(width: 8),
          Expanded(child: _StatTile(label: 'OT', value: '${stats.otMinutes}m', color: AppColors.info)),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.2)),
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
          Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.filter,
    required this.onPreset,
    required this.onCustomRange,
  });

  final AttendanceDateFilter filter;
  final ValueChanged<AttendanceRangePreset> onPreset;
  final VoidCallback onCustomRange;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _FilterChip(
                  label: '7 Hari',
                  selected: filter.preset == AttendanceRangePreset.week,
                  onTap: () => onPreset(AttendanceRangePreset.week),
                ),
                _FilterChip(
                  label: 'Bulan ini',
                  selected: filter.preset == AttendanceRangePreset.month,
                  onTap: () => onPreset(AttendanceRangePreset.month),
                ),
                _FilterChip(
                  label: '90 Hari',
                  selected: filter.preset == AttendanceRangePreset.quarter,
                  onTap: () => onPreset(AttendanceRangePreset.quarter),
                ),
                _FilterChip(
                  label: 'Pilih tanggal',
                  selected: filter.preset == AttendanceRangePreset.custom,
                  onTap: onCustomRange,
                  icon: Icons.date_range_rounded,
                ),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            filter.label(),
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.darkGoldRich,
            ),
          ),
        ),
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    this.icon,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: AnimatedPress(
        onTap: onTap,
        scale: 0.97,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            gradient: selected ? AppColors.headerGradient : null,
            color: selected ? null : AppColors.surface,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected ? Colors.transparent : AppColors.darkGold.withValues(alpha: 0.25),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 14, color: selected ? Colors.white : AppColors.darkGold),
                const SizedBox(width: 4),
              ],
              Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: selected ? Colors.white : AppColors.text,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TimesheetCard extends ConsumerWidget {
  const _TimesheetCard({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final fmtDate = DateFormat('EEEE, dd MMM yyyy');
    final fmtTime = DateFormat('HH:mm');
    final workDate = DateTime.parse(data['work_date'] as String);
    final code = data['attendance_code_label'] ?? data['attendance_code'];

    return GoldPanel(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  fmtDate.format(workDate),
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
              ),
              if (code != null) StatusBadge(status: '$code'),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Shift ${data['shift_code'] ?? '—'} · ${data['shift_label'] ?? ''}',
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
          if (data['punch_source'] != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Sumber: ${_sourceLabel(data['punch_source'])}',
                style: const TextStyle(fontSize: 11, color: AppColors.textDim),
              ),
            ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _TimeBlock(
                  label: 'Masuk',
                  time: _formatTime(data['check_in'], fmtTime),
                  lateMinutes: data['late_in_minutes'] as int? ?? 0,
                  isIn: true,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _TimeBlock(
                  label: 'Pulang',
                  time: _formatTime(data['check_out'], fmtTime),
                  earlyMinutes: data['early_out_minutes'] as int? ?? 0,
                  isIn: false,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _PhotoThumb(
                  label: 'Foto Masuk',
                  photoUrl: data['check_in_photo_url'] as String?,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _PhotoThumb(
                  label: 'Foto Pulang',
                  photoUrl: data['check_out_photo_url'] as String?,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.darkGoldLight.withValues(alpha: 0.45),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              'Jam kerja ${data['paid_working_hours'] ?? '0'} · '
              'Telat ${data['late_in_minutes'] ?? 0} m · '
              'Pulang cepat ${data['early_out_minutes'] ?? 0} m · '
              'OT ${(data['ot_before_minutes'] ?? 0) + (data['ot_after_minutes'] ?? 0)} m',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: AppColors.darkGoldRich,
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _formatTime(dynamic value, DateFormat fmt) {
    if (value == null) return '—';
    return fmt.format(DateTime.parse(value as String).toLocal());
  }

  static String _sourceLabel(dynamic source) {
    switch ('$source') {
      case 'mobile':
        return 'Aplikasi Mobile';
      case 'web':
        return 'Portal Web';
      case 'kiosk':
        return 'Kiosk';
      case 'import':
        return 'Import';
      default:
        return '$source';
    }
  }
}

class _TimeBlock extends StatelessWidget {
  const _TimeBlock({
    required this.label,
    required this.time,
    required this.isIn,
    this.lateMinutes = 0,
    this.earlyMinutes = 0,
  });

  final String label;
  final String time;
  final bool isIn;
  final int lateMinutes;
  final int earlyMinutes;

  @override
  Widget build(BuildContext context) {
    final accent = isIn ? AppColors.darkGold : AppColors.chinaRed;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accent.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 10, color: accent, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(
            time,
            style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800, fontSize: 18),
          ),
          if (isIn && lateMinutes > 0)
            Text('Telat $lateMinutes m', style: const TextStyle(fontSize: 10, color: AppColors.danger)),
          if (!isIn && earlyMinutes > 0)
            Text('Cepat $earlyMinutes m', style: const TextStyle(fontSize: 10, color: AppColors.warning)),
        ],
      ),
    );
  }
}

class _PhotoThumb extends ConsumerWidget {
  const _PhotoThumb({required this.label, this.photoUrl});

  final String label;
  final String? photoUrl;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AnimatedPress(
      onTap: photoUrl == null
          ? null
          : () => _openPhotoViewer(context, ref, label, photoUrl!),
      scale: 0.98,
      enabled: photoUrl != null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: AppColors.darkGold,
            ),
          ),
          const SizedBox(height: 6),
          AspectRatio(
            aspectRatio: 4 / 3,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.surfaceMuted,
                  border: Border.all(color: AppColors.darkGoldMuted),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: photoUrl == null
                    ? const Center(
                        child: Icon(Icons.no_photography_outlined, color: AppColors.textDim, size: 28),
                      )
                    : Stack(
                        fit: StackFit.expand,
                        children: [
                          AuthMediaImage(url: photoUrl),
                          Positioned(
                            right: 6,
                            bottom: 6,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.45),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(Icons.zoom_in, color: Colors.white, size: 14),
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openPhotoViewer(
    BuildContext context,
    WidgetRef ref,
    String title,
    String url,
  ) async {
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: const EdgeInsets.all(16),
        backgroundColor: Colors.transparent,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              style: GoogleFonts.plusJakartaSans(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: InteractiveViewer(
                minScale: 0.8,
                maxScale: 4,
                child: AuthMediaImage(
                  url: url,
                  fit: BoxFit.contain,
                  loading: const SizedBox(
                    width: 280,
                    height: 280,
                    child: Center(child: CircularProgressIndicator(color: Colors.white)),
                  ),
                  error: const SizedBox(
                    width: 280,
                    height: 200,
                    child: Center(
                      child: Icon(Icons.broken_image_outlined, color: Colors.white70, size: 48),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Tutup', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }
}
