import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Splash pembuka. Muncul setiap proses aplikasi dimulai.
class AppSplash extends StatefulWidget {
  const AppSplash({super.key, required this.child});

  final Widget child;

  @override
  State<AppSplash> createState() => _AppSplashState();
}

class _AppSplashState extends State<AppSplash> with SingleTickerProviderStateMixin {
  static const _visible = Duration(milliseconds: 1500);
  static const _fadeIn = Duration(milliseconds: 420);
  static const _fadeOut = Duration(milliseconds: 280);

  late final AnimationController _controller;
  late final Animation<double> _logo;
  late final Animation<double> _veil;
  bool _show = true;

  @override
  void initState() {
    super.initState();
    final total = _visible + _fadeOut;
    _controller = AnimationController(vsync: this, duration: total);
    _logo = CurvedAnimation(
      parent: _controller,
      curve: Interval(
        0,
        _fadeIn.inMilliseconds / total.inMilliseconds,
        curve: Curves.easeOutCubic,
      ),
    );
    _veil = Tween<double>(begin: 1, end: 0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Interval(
          _visible.inMilliseconds / total.inMilliseconds,
          1,
          curve: Curves.easeInOutCubic,
        ),
      ),
    );
    _controller.forward().whenComplete(() {
      if (mounted) setState(() => _show = false);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        widget.child,
        if (_show)
          FadeTransition(
            opacity: _veil,
            child: ColoredBox(
              color: AppColors.bg,
              child: _SplashMark(opacity: _logo),
            ),
          ),
      ],
    );
  }
}

class _SplashMark extends StatelessWidget {
  const _SplashMark({required this.opacity});

  final Animation<double> opacity;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final logoWidth = (width * 0.78).clamp(232.0, 320.0);

    return Center(
      child: FadeTransition(
        opacity: opacity,
        child: Image.asset(
          'assets/images/main-logo.png',
          width: logoWidth,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
        ),
      ),
    );
  }
}
