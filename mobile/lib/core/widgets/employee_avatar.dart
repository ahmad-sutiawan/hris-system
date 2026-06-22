import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_colors.dart';
import 'auth_media_image.dart';

String employeeInitials(String name) {
  final parts = name.trim().split(RegExp(r'\s+')).where((part) => part.isNotEmpty).toList();
  if (parts.isEmpty) return '?';
  if (parts.length == 1) return parts.first[0].toUpperCase();
  return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
}

class EmployeeAvatar extends ConsumerWidget {
  const EmployeeAvatar({
    super.key,
    this.photoUrl,
    required this.name,
    this.size = 48,
    this.backgroundColor,
    this.textColor,
    this.border,
  });

  final String? photoUrl;
  final String name;
  final double size;
  final Color? backgroundColor;
  final Color? textColor;
  final BoxBorder? border;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final initials = employeeInitials(name);
    final bg = backgroundColor ?? AppColors.cyanDim;
    final fg = textColor ?? AppColors.cyan;

    Widget avatar = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: bg,
        border: border,
      ),
      clipBehavior: Clip.antiAlias,
      child: photoUrl != null && photoUrl!.isNotEmpty
          ? AuthMediaImage(
              url: photoUrl,
              fit: BoxFit.cover,
              loading: Center(
                child: SizedBox(
                  width: size * 0.35,
                  height: size * 0.35,
                  child: CircularProgressIndicator(strokeWidth: 2, color: fg),
                ),
              ),
              error: _Initials(initials: initials, color: fg, size: size),
            )
          : _Initials(initials: initials, color: fg, size: size),
    );

    return avatar;
  }
}

class _Initials extends StatelessWidget {
  const _Initials({
    required this.initials,
    required this.color,
    required this.size,
  });

  final String initials;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        initials,
        style: GoogleFonts.plusJakartaSans(
          color: color,
          fontWeight: FontWeight.w800,
          fontSize: size * 0.36,
        ),
      ),
    );
  }
}
