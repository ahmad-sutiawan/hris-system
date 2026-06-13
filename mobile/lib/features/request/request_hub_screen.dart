import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme/app_colors.dart';
import '../../core/widgets/talenta_widgets.dart';

class RequestHubScreen extends ConsumerWidget {
  const RequestHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text(
          'Pengajuan',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Buat pengajuan baru',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          RequestActionCard(
            icon: Icons.beach_access_rounded,
            title: 'Pengajuan Cuti',
            subtitle: 'Ajukan cuti tahunan, sakit, atau izin',
            color: AppColors.info,
            onTap: () => context.push('/leave/new'),
          ),
          RequestActionCard(
            icon: Icons.more_time_rounded,
            title: 'Pengajuan Lembur',
            subtitle: 'Ajukan lembur sebelum atau sesudah shift',
            color: AppColors.accent,
            onTap: () => context.push('/overtime/new'),
          ),
          RequestActionCard(
            icon: Icons.login_rounded,
            title: 'Absen Masuk',
            subtitle: 'Clock in dengan selfie',
            color: AppColors.success,
            onTap: () => context.push('/punch?action=in'),
          ),
          RequestActionCard(
            icon: Icons.logout_rounded,
            title: 'Absen Pulang',
            subtitle: 'Clock out dengan selfie',
            color: AppColors.danger,
            onTap: () => context.push('/punch?action=out'),
          ),
          const SizedBox(height: 8),
          HomeSectionHeader(
            title: 'Riwayat pengajuan',
            actionLabel: null,
            onAction: null,
          ),
          RequestActionCard(
            icon: Icons.history_rounded,
            title: 'Daftar Cuti',
            subtitle: 'Lihat status dan batalkan pengajuan',
            color: AppColors.cyan,
            onTap: () => context.push('/leave'),
          ),
          RequestActionCard(
            icon: Icons.schedule_rounded,
            title: 'Daftar Lembur',
            subtitle: 'Lihat status pengajuan lembur',
            color: AppColors.warning,
            onTap: () => context.push('/overtime'),
          ),
        ],
      ),
    );
  }
}
