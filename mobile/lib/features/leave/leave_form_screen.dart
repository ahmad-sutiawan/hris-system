import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';
import '../shared/request_history_widgets.dart';
import 'leave_screen.dart';

final leaveTypesProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/leave-types/');
});

class LeaveFormScreen extends ConsumerStatefulWidget {
  const LeaveFormScreen({super.key});

  @override
  ConsumerState<LeaveFormScreen> createState() => _LeaveFormScreenState();
}

class _LeaveFormScreenState extends ConsumerState<LeaveFormScreen> {
  final _reasonCtrl = TextEditingController();
  DateTime _start = DateTime.now();
  DateTime _end = DateTime.now();
  int? _leaveTypeId;
  bool _halfDay = false;
  bool _loading = false;

  @override
  void dispose() {
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDate(bool isStart) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _start : _end,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _start = picked;
          if (_end.isBefore(_start) || _halfDay) _end = _start;
        } else {
          _end = picked;
          if (_halfDay) _start = _end;
        }
      });
    }
  }

  Future<void> _submit() async {
    if (_leaveTypeId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pilih jenis cuti.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      await ref.read(apiClientProvider).post('/leave-requests/', body: {
        'leave_type': _leaveTypeId,
        'start_date': DateFormat('yyyy-MM-dd').format(_start),
        'end_date': DateFormat('yyyy-MM-dd').format(_end),
        'is_half_day': _halfDay,
        'reason': _reasonCtrl.text.trim(),
      });
      ref.invalidate(leaveRequestsProvider);
      ref.invalidate(leaveBalancesProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan cuti berhasil dikirim.')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final types = ref.watch(leaveTypesProvider);
    final fmt = DateFormat('dd MMM yyyy');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('Submit Leave')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          types.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (items) => HrisCard(
              child: DropdownButtonFormField<int>(
                decoration: const InputDecoration(labelText: 'Jenis Cuti'),
                value: _leaveTypeId,
                items: items.map((t) {
                  final type = t as Map<String, dynamic>;
                  return DropdownMenuItem<int>(
                    value: type['id'] as int,
                    child: Text('${type['code']} — ${type['name']}'),
                  );
                }).toList(),
                onChanged: (v) => setState(() => _leaveTypeId = v),
              ),
            ),
          ),
          const SizedBox(height: 12),
          HrisCard(
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Tanggal Mulai'),
                  subtitle: Text(fmt.format(_start)),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () => _pickDate(true),
                ),
                const Divider(color: AppColors.border),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Tanggal Selesai'),
                  subtitle: Text(fmt.format(_end)),
                  trailing: const Icon(Icons.calendar_today),
                  enabled: !_halfDay,
                  onTap: _halfDay ? null : () => _pickDate(false),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Setengah Hari'),
                  value: _halfDay,
                  activeTrackColor: AppColors.accent.withValues(alpha: 0.5),
                  thumbColor: WidgetStateProperty.resolveWith(
                    (states) => states.contains(WidgetState.selected)
                        ? AppColors.accent
                        : AppColors.textMuted,
                  ),
                  onChanged: (v) => setState(() {
                    _halfDay = v;
                    if (v) _end = _start;
                  }),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          HrisCard(
            child: TextField(
              controller: _reasonCtrl,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Alasan',
                alignLabelWithHint: true,
              ),
            ),
          ),
          const SizedBox(height: 24),
          PrimaryButton(
            label: 'Kirim Pengajuan',
            loading: _loading,
            onPressed: _submit,
            icon: Icons.send,
          ),
          const LeaveRequestHistorySection(),
        ],
      ),
    );
  }
}
