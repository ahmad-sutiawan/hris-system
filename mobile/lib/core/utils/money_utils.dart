import 'package:intl/intl.dart';

String formatRupiah(dynamic value) {
  if (value == null || '$value'.trim().isEmpty) return '—';
  final parsed = num.tryParse('$value'.replaceAll(',', ''));
  if (parsed == null) return '$value';
  return NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0).format(parsed);
}
