import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Latar aurora — gradien lembut + orbs blur yang bergerak halus (fluid & korporat).
class AuroraBackground extends StatefulWidget {
  const AuroraBackground({super.key, required this.child});

  final Widget child;

  @override
  State<AuroraBackground> createState() => _AuroraBackgroundState();
}

class _AuroraBackgroundState extends State<AuroraBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _drift;

  @override
  void initState() {
    super.initState();
    _drift = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _drift.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _drift,
      builder: (context, child) {
        final t = _drift.value;
        return DecoratedBox(
          decoration: const BoxDecoration(gradient: AppColors.auroraBaseGradient),
          child: Stack(
            fit: StackFit.expand,
            children: [
              _AuroraOrb(
                t: t,
                phase: 0,
                size: 340,
                top: -80 + math.sin(t * math.pi * 2) * 28,
                left: -90 + math.cos(t * math.pi * 2) * 22,
                colors: AppColors.auroraOrbPurple,
              ),
              _AuroraOrb(
                t: t,
                phase: 0.35,
                size: 300,
                top: 120 + math.cos(t * math.pi * 2 + 1) * 36,
                right: -70 + math.sin(t * math.pi * 2) * 18,
                colors: AppColors.auroraOrbBlue,
              ),
              _AuroraOrb(
                t: t,
                phase: 0.65,
                size: 260,
                bottom: 80 + math.sin(t * math.pi * 2 + 2) * 24,
                left: 40 + math.cos(t * math.pi * 2 + 0.5) * 30,
                colors: AppColors.auroraOrbGold,
              ),
              _AuroraOrb(
                t: t,
                phase: 0.85,
                size: 220,
                bottom: -40 + math.cos(t * math.pi * 2) * 20,
                right: 20 + math.sin(t * math.pi * 2 + 1.2) * 26,
                colors: AppColors.auroraOrbLavender,
              ),
              child!,
            ],
          ),
        );
      },
      child: widget.child,
    );
  }
}

class _AuroraOrb extends StatelessWidget {
  const _AuroraOrb({
    required this.t,
    required this.phase,
    required this.size,
    required this.colors,
    this.top,
    this.left,
    this.right,
    this.bottom,
  });

  final double t;
  final double phase;
  final double size;
  final List<Color> colors;
  final double? top;
  final double? left;
  final double? right;
  final double? bottom;

  @override
  Widget build(BuildContext context) {
    final pulse = 0.88 + math.sin((t + phase) * math.pi * 2) * 0.12;
    return Positioned(
      top: top,
      left: left,
      right: right,
      bottom: bottom,
      child: ImageFiltered(
        imageFilter: ImageFilter.blur(sigmaX: 48, sigmaY: 48),
        child: Transform.scale(
          scale: pulse,
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: colors,
                stops: const [0.0, 0.55, 1.0],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Panel kaca aurora — blur + border halus + highlight atas.
class AuroraGlass extends StatelessWidget {
  const AuroraGlass({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin,
    this.borderRadius = 20,
    this.onTap,
    this.blur = 22,
    this.tint,
    this.borderColor,
    this.showTopShine = true,
  });

  final Widget child;
  final EdgeInsets padding;
  final EdgeInsets? margin;
  final double borderRadius;
  final VoidCallback? onTap;
  final double blur;
  final Color? tint;
  final Color? borderColor;
  final bool showTopShine;

  @override
  Widget build(BuildContext context) {
    final surface = tint ?? AppColors.glassSurface;
    final border = borderColor ?? AppColors.glassBorder;

    Widget panel = ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: border),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                surface.withValues(alpha: 0.92),
                surface.withValues(alpha: 0.72),
              ],
            ),
            boxShadow: [
              BoxShadow(
                color: AppColors.brandPurple.withValues(alpha: 0.08),
                blurRadius: 28,
                offset: const Offset(0, 12),
              ),
              BoxShadow(
                color: AppColors.brandGold.withValues(alpha: 0.06),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Stack(
            children: [
              if (showTopShine)
                Positioned(
                  top: 0,
                  left: 16,
                  right: 16,
                  child: Container(
                    height: 1,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.white.withValues(alpha: 0.0),
                          Colors.white.withValues(alpha: 0.65),
                          Colors.white.withValues(alpha: 0.0),
                        ],
                      ),
                    ),
                  ),
                ),
              Padding(padding: padding, child: child),
            ],
          ),
        ),
      ),
    );

    if (margin != null) {
      panel = Padding(padding: margin!, child: panel);
    }

    if (onTap == null) return panel;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(borderRadius),
        splashColor: AppColors.brandPurple.withValues(alpha: 0.08),
        highlightColor: AppColors.brandPurple.withValues(alpha: 0.04),
        child: panel,
      ),
    );
  }
}

/// Tombol gradient aurora dengan glow lembut.
class AuroraButton extends StatelessWidget {
  const AuroraButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.loading = false,
    this.secondary = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool loading;
  final bool secondary;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    if (secondary) {
      return OutlinedButton(
        onPressed: loading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.brandPurple,
          side: BorderSide(color: AppColors.brandPurple.withValues(alpha: 0.45)),
          minimumSize: expand ? const Size.fromHeight(52) : null,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        child: _content(Colors.transparent),
      );
    }

    return AnimatedPressWrapper(
      enabled: !loading && onPressed != null,
      onTap: onPressed,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: AppColors.auroraButtonGradient,
          boxShadow: [
            BoxShadow(
              color: AppColors.brandPurple.withValues(alpha: 0.32),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: loading ? null : onPressed,
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              width: expand ? double.infinity : null,
              height: 52,
              child: _content(Colors.white),
            ),
          ),
        ),
      ),
    );
  }

  Widget _content(Color iconColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
      children: [
        if (loading)
          SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: secondary ? AppColors.brandPurple : Colors.white,
            ),
          )
        else if (icon != null) ...[
          Icon(icon, size: 20, color: iconColor),
          const SizedBox(width: 8),
        ],
        Text(
          label,
          style: TextStyle(
            color: secondary ? AppColors.brandPurple : Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        ),
      ],
    );
  }
}

/// Tap scale ringan — dipakai internal agar tidak circular import.
class AnimatedPressWrapper extends StatefulWidget {
  const AnimatedPressWrapper({
    super.key,
    required this.child,
    this.onTap,
    this.enabled = true,
    this.scale = 0.97,
  });

  final Widget child;
  final VoidCallback? onTap;
  final bool enabled;
  final double scale;

  @override
  State<AnimatedPressWrapper> createState() => _AnimatedPressWrapperState();
}

class _AnimatedPressWrapperState extends State<AnimatedPressWrapper> {
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
        child: widget.child,
      ),
    );
  }
}
