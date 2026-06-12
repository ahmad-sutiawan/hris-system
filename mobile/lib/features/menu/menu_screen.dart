import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';

class MenuScreen extends ConsumerWidget {
  const MenuScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final employee = auth.employee;

    final items = [
      _MenuItem('Lembur', Icons.more_time, '/overtime', AppColors.accent),
      _MenuItem('Slip Gaji', Icons.receipt_long, '/payslips', AppColors.success),
      _MenuItem('Profil Karyawan', Icons.badge_outlined, '/profile', AppColors.cyan),
      _MenuItem('Notifikasi', Icons.notifications_outlined, '/notifications', AppColors.warning),
      _MenuItem('Pengumuman', Icons.campaign_outlined, '/announcements', AppColors.info),
    ];

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('MENU')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          IndustrialCard(
            accentColor: AppColors.accent,
            child: Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    border: Border.all(color: AppColors.accent, width: 2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Icon(Icons.person, color: AppColors.accent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        employee?['full_name'] ?? auth.user?['username'] ?? '',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                      ),
                      Text(
                        employee?['employee_id'] ?? auth.user?['role'] ?? '',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionHeader(title: 'Fitur Lainnya'),
          const SizedBox(height: 12),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: IndustrialCard(
                accentColor: item.color,
                onTap: () => context.push(item.route),
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(item.icon, color: item.color),
                  title: Text(item.label),
                  trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          NeonButton(
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

class _MenuItem {
  const _MenuItem(this.label, this.icon, this.route, this.color);

  final String label;
  final IconData icon;
  final String route;
  final Color color;
}
