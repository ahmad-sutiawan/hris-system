import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme/app_colors.dart';
import '../../core/utils/shift_utils.dart';
import '../../core/widgets/hris_widgets.dart';
import '../home/home_screen.dart';

class CalendarScreen extends ConsumerWidget {
  const CalendarScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(dashboardProvider);

    return HrisScaffold(
      appBar: hrisAppBar(title: 'Kalender Shift'),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(dashboardProvider),
        child: dashboard.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat jadwal', subtitle: '$e'),
            ],
          ),
          data: (data) {
            final shifts = (data['upcoming_shifts'] as List?)?.cast<Map<String, dynamic>>() ?? [];
            if (shifts.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  EmptyState(
                    icon: Icons.event_busy_rounded,
                    title: 'Belum ada jadwal shift',
                    subtitle: 'Jadwal akan muncul setelah HR mengatur shift Anda',
                  ),
                ],
              );
            }

            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
              itemCount: shifts.length + 1,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                if (index == shifts.length) {
                  return PrimaryButton(
                    label: 'Lihat profil lengkap',
                    icon: Icons.person_outline_rounded,
                    onPressed: () => context.push('/profile'),
                  );
                }
                final shift = shifts[index];
                return Material(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            color: AppColors.cyanDim,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.event_rounded, color: AppColors.cyan),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                formatWorkDateLabel(shift['work_date'] as String?),
                                style: GoogleFonts.plusJakartaSans(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 13,
                                  color: AppColors.textMuted,
                                ),
                              ),
                              Text(
                                '${shift['shift_name'] ?? shift['shift_code'] ?? 'Shift'} · ${formatShiftTimeRange(shift)}',
                                style: GoogleFonts.plusJakartaSans(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 14,
                                ),
                              ),
                              if ((shift['plant_name'] as String?)?.isNotEmpty ?? false)
                                Text(
                                  shift['plant_name'] as String,
                                  style: const TextStyle(fontSize: 12, color: AppColors.textDim),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
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
