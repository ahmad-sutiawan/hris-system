import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';
import 'aurora_background.dart';

/// Spacing konsisten antar section home.
abstract final class AppSpacing {
  static const section = 16.0;
  static const item = 10.0;
  static const screenH = 16.0;
  static const bottomNav = 100.0;
}

/// Tap scale + fade/slide entrance — fluid & responsif.
class AnimatedPress extends StatefulWidget {
  const AnimatedPress({
    super.key,
    required this.child,
    this.onTap,
    this.enabled = true,
    this.scale = 0.96,
  });

  final Widget child;
  final VoidCallback? onTap;
  final bool enabled;
  final double scale;

  @override
  State<AnimatedPress> createState() => _AnimatedPressState();
}

class _AnimatedPressState extends State<AnimatedPress> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: widget.enabled ? (_) => setState(() => _pressed = true) : null,
      onTapUp: widget.enabled ? (_) => setState(() => _pressed = false) : null,
      onTapCancel: widget.enabled ? () => setState(() => _pressed = false) : null,
      onTap: widget.enabled ? widget.onTap : null,
      child: AnimatedScale(
        scale: _pressed ? widget.scale : 1,
        duration: const Duration(milliseconds: 140),
        curve: Curves.easeOutCubic,
        child: AnimatedOpacity(
          opacity: widget.enabled ? 1 : 0.5,
          duration: const Duration(milliseconds: 150),
          child: widget.child,
        ),
      ),
    );
  }
}

class FadeSlideIn extends StatefulWidget {
  const FadeSlideIn({
    super.key,
    required this.child,
    this.index = 0,
    this.delayMs = 45,
  });

  final Widget child;
  final int index;
  final int delayMs;

  @override
  State<FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<FadeSlideIn> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fade;
  late final Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 480),
    );
    _fade = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
    _slide = Tween<Offset>(
      begin: const Offset(0, 0.05),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

    Future<void>.delayed(Duration(milliseconds: widget.index * widget.delayMs), () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fade,
      child: SlideTransition(position: _slide, child: widget.child),
    );
  }
}

/// Garis aksen aurora + judul section.
class GoldSectionTitle extends StatelessWidget {
  const GoldSectionTitle({
    super.key,
    required this.title,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.screenH, 0, AppSpacing.screenH, AppSpacing.item),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 22,
            decoration: BoxDecoration(
              gradient: AppColors.auroraButtonGradient,
              borderRadius: BorderRadius.circular(4),
              boxShadow: [
                BoxShadow(
                  color: AppColors.brandPurple.withValues(alpha: 0.25),
                  blurRadius: 8,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.text,
                letterSpacing: -0.3,
              ),
            ),
          ),
          if (actionLabel != null && onAction != null)
            AnimatedPress(
              onTap: onAction,
              scale: 0.98,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.brandPurple.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  actionLabel!,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: AppColors.brandPurple,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Panel kaca aurora dengan margin standar.
class GoldPanel extends StatelessWidget {
  const GoldPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.screenH),
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return AuroraGlass(
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.screenH),
      padding: padding,
      borderRadius: 22,
      borderColor: AppColors.glassBorder,
      child: child,
    );
  }
}
