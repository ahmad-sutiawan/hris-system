import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/auth_provider.dart';
import '../features/announcements/announcement_detail_screen.dart';
import '../features/announcements/announcements_screen.dart';
import '../features/apps/all_apps_screen.dart';
import '../features/attendance/attendance_screen.dart';
import '../features/attendance/punch_screen.dart';
import '../features/home/home_screen.dart';
import '../features/leave/leave_form_screen.dart';
import '../features/leave/leave_screen.dart';
import '../features/menu/menu_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/overtime/overtime_form_screen.dart';
import '../features/overtime/overtime_screen.dart';
import '../features/calendar/calendar_screen.dart';
import '../features/payslip/payslip_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/request/request_hub_screen.dart';
import '../features/auth/login_screen.dart';
import 'app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: _AuthRefresh(ref),
    redirect: (context, state) {
      final loggingIn = state.matchedLocation == '/login';
      if (auth.isLoading) return null;
      if (!auth.isAuthenticated && !loggingIn) return '/login';
      if (auth.isAuthenticated && loggingIn) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/attendance',
                builder: (context, state) => const AttendanceScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/request',
                builder: (context, state) => const RequestHubScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/inbox',
                builder: (context, state) => const NotificationsScreen(
                  embedded: true,
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/account',
                builder: (context, state) => const MenuScreen(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(path: '/punch', builder: (_, __) => const PunchScreen()),
      GoRoute(path: '/leave', builder: (_, __) => const LeaveScreen()),
      GoRoute(path: '/leave/new', builder: (_, __) => const LeaveFormScreen()),
      GoRoute(path: '/overtime', builder: (_, __) => const OvertimeScreen()),
      GoRoute(path: '/overtime/new', builder: (_, __) => const OvertimeFormScreen()),
      GoRoute(path: '/payslips', builder: (_, __) => const PayslipScreen()),
      GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
      GoRoute(
        path: '/notifications',
        builder: (_, __) => const NotificationsScreen(),
      ),
      GoRoute(path: '/all-apps', builder: (_, __) => const AllAppsScreen()),
      GoRoute(path: '/calendar', builder: (_, __) => const CalendarScreen()),
      GoRoute(path: '/announcements', builder: (_, __) => const AnnouncementsScreen()),
      GoRoute(
        path: '/announcements/:id',
        builder: (context, state) => AnnouncementDetailScreen(
          id: int.parse(state.pathParameters['id']!),
        ),
      ),
    ],
  );
});

class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(this.ref) {
    ref.listen<AuthState>(authProvider, (_, __) => notifyListeners());
  }
  final Ref ref;
}
