import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'core/widgets/mobile_preview_frame.dart';
import 'router/app_router.dart';

class HrisApp extends ConsumerWidget {
  const HrisApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MobilePreviewFrame(
      child: MaterialApp.router(
        title: 'PT BPS HRIS',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        routerConfig: router,
      ),
    );
  }
}
