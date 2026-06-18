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
          'Requests',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'New request',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          RequestActionCard(
            icon: Icons.beach_access_rounded,
            title: 'Leave Request',
            subtitle: 'Submit annual, sick, or personal leave',
            color: AppColors.info,
            onTap: () => context.push('/leave/new'),
          ),
          RequestActionCard(
            icon: Icons.more_time_rounded,
            title: 'Overtime Request',
            subtitle: 'Submit overtime before or after shift',
            color: AppColors.accent,
            onTap: () => context.push('/overtime/new'),
          ),
          RequestActionCard(
            icon: Icons.login_rounded,
            title: 'Clock In',
            subtitle: 'Clock in with selfie',
            color: AppColors.success,
            onTap: () => context.push('/punch?action=in'),
          ),
          RequestActionCard(
            icon: Icons.logout_rounded,
            title: 'Clock Out',
            subtitle: 'Clock out with selfie',
            color: AppColors.danger,
            onTap: () => context.push('/punch?action=out'),
          ),
          const SizedBox(height: 8),
          HomeSectionHeader(
            title: 'Request history',
            actionLabel: null,
            onAction: null,
          ),
          RequestActionCard(
            icon: Icons.history_rounded,
            title: 'Leave List',
            subtitle: 'View status and cancel requests',
            color: AppColors.cyan,
            onTap: () => context.push('/leave'),
          ),
          RequestActionCard(
            icon: Icons.schedule_rounded,
            title: 'Overtime List',
            subtitle: 'View overtime request status',
            color: AppColors.warning,
            onTap: () => context.push('/overtime'),
          ),
        ],
      ),
    );
  }
}
