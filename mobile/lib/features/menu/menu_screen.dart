import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../home/home_screen.dart';

class MenuScreen extends ConsumerWidget {
  const MenuScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final dashboard = ref.watch(dashboardProvider);
    final employee = auth.employee;
    final unread = dashboard.maybeWhen(
      data: (d) => d['unread_notifications'] as int? ?? 0,
      orElse: () => 0,
    );
    final announcements = dashboard.maybeWhen(
      data: (d) => d['active_announcements'] as int? ?? 0,
      orElse: () => 0,
    );

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('Akun Saya')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          HrisCard(
            showAccentBar: true,
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: AppColors.accentSoft,
                  child: Icon(Icons.person, size: 32, color: AppColors.accent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        employee?['full_name'] ?? auth.user?['username'] ?? '',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        employee?['employee_id'] ?? '',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
                TextButton(
                  onPressed: () => context.push('/profile'),
                  child: const Text('Detail'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionHeader(title: 'Utama', subtitle: 'Sama seperti menu web'),
          const SizedBox(height: 8),
          _MenuTile(
            icon: Icons.notifications_outlined,
            label: 'Notifikasi',
            badge: unread > 0 ? '$unread' : null,
            onTap: () => context.push('/notifications'),
          ),
          _MenuTile(
            icon: Icons.campaign_outlined,
            label: 'Pengumuman',
            badge: announcements > 0 ? '$announcements' : null,
            onTap: () => context.push('/announcements'),
          ),
          _MenuTile(
            icon: Icons.badge_outlined,
            label: 'Detail Karyawan',
            onTap: () => context.push('/profile'),
          ),
          const SizedBox(height: 16),
          const SectionHeader(title: 'Operasional'),
          const SizedBox(height: 8),
          _MenuTile(
            icon: Icons.calendar_month_outlined,
            label: 'Rekap Absensi',
            onTap: () => context.go('/attendance'),
          ),
          _MenuTile(
            icon: Icons.beach_access_outlined,
            label: 'Pengajuan Cuti',
            onTap: () => context.go('/leave'),
          ),
          _MenuTile(
            icon: Icons.more_time_outlined,
            label: 'Pengajuan Lembur',
            onTap: () => context.go('/overtime'),
          ),
          const SizedBox(height: 16),
          const SectionHeader(title: 'Keuangan'),
          const SizedBox(height: 8),
          _MenuTile(
            icon: Icons.receipt_long_outlined,
            label: 'Slip Gaji',
            onTap: () => context.push('/payslips'),
          ),
          const SizedBox(height: 28),
          PrimaryButton(
            label: 'Keluar',
            secondary: true,
            icon: Icons.logout,
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
    );
  }
}

class _MenuTile extends StatelessWidget {
  const _MenuTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.badge,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: HrisCard(
        onTap: onTap,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.surfaceMuted,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: AppColors.steel700),
          ),
          title: Text(
            label,
            style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
          ),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (badge != null)
                Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.accent,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    badge!,
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700),
                  ),
                ),
              const Icon(Icons.chevron_right, color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
