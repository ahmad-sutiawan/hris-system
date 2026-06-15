import 'package:intl/intl.dart';

String formatShiftTimeRange(Map<String, dynamic>? shift) {
  if (shift == null) return '—';
  final fmt = DateFormat('HH:mm');
  final inStr = shift['scheduled_check_in'] as String?;
  final outStr = shift['scheduled_check_out'] as String?;
  if (inStr == null || outStr == null) {
    return shift['shift_code']?.toString() ?? '—';
  }
  try {
    final start = DateTime.parse(inStr).toLocal();
    final end = DateTime.parse(outStr).toLocal();
    return '${fmt.format(start)} - ${fmt.format(end)}';
  } catch (_) {
    return '${inStr.substring(0, 5)} - ${outStr.substring(0, 5)}';
  }
}

String formatWorkDateLabel(String? isoDate) {
  if (isoDate == null || isoDate.isEmpty) return '—';
  try {
    final date = DateTime.parse(isoDate);
    return DateFormat('EEE, dd MMM yyyy').format(date);
  } catch (_) {
    return isoDate;
  }
}

String shiftLocationLabel(Map<String, dynamic>? shift, {Map<String, dynamic>? employee}) {
  final plantName = shift?['plant_name'] as String?;
  if (plantName != null && plantName.isNotEmpty) return plantName;
  final shiftName = shift?['shift_name'] as String?;
  if (shiftName != null && shiftName.isNotEmpty) return shiftName;
  final dept = employee?['department_name'] as String? ?? employee?['department'] as String?;
  if (dept != null && dept.isNotEmpty) return dept;
  final plantCode = employee?['plant_code'] as String?;
  if (plantCode != null && plantCode.isNotEmpty) return plantCode;
  return 'Kantor';
}
