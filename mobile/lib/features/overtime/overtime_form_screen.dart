import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/industrial_widgets.dart';
import 'overtime_screen.dart';

final overtimeTypesProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/overtime-types/');
});

class OvertimeFormScreen extends ConsumerStatefulWidget {
  const OvertimeFormScreen({super.key});

  @override
  ConsumerState<OvertimeFormScreen> createState() => _OvertimeFormScreenState();
}

class _OvertimeFormScreenState extends ConsumerState<OvertimeFormScreen> {
  final _reasonCtrl = TextEditingController();
  final _beforeCtrl = TextEditingController(text: '0');
  final _afterCtrl = TextEditingController(text: '0');
  DateTime _workDate = DateTime.now();
  int? _typeId;
  String _compMode = 'cash';
  bool _loading = false;
  Map<String, dynamic>? _preview;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadSuggested());
  }

  @override
  void dispose() {
    _reasonCtrl.dispose();
    _beforeCtrl.dispose();
    _afterCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadSuggested() async {
    try {
      final api = ref.read(apiClientProvider);
      final data = await api.get(
        '/overtime-requests/suggested_minutes/',
        query: {'work_date': DateFormat('yyyy-MM-dd').format(_workDate)},
      );
      setState(() {
        _beforeCtrl.text = '${data['ot_before_minutes'] ?? 0}';
        _afterCtrl.text = '${data['ot_after_minutes'] ?? 0}';
      });
      await _refreshPreview();
    } catch (_) {}
  }

  Future<void> _refreshPreview() async {
    try {
      final preview = await ref.read(apiClientProvider).post(
        '/overtime-requests/compensation_preview/',
        body: {
          'ot_before_minutes': int.tryParse(_beforeCtrl.text) ?? 0,
          'ot_after_minutes': int.tryParse(_afterCtrl.text) ?? 0,
          if (_typeId != null) 'overtime_type': _typeId,
        },
      );
      setState(() => _preview = preview);
    } catch (_) {
      setState(() => _preview = null);
    }
  }

  Future<void> _submit() async {
    if (_typeId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pilih jenis lembur.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      await ref.read(apiClientProvider).post('/overtime-requests/', body: {
        'overtime_type': _typeId,
        'work_date': DateFormat('yyyy-MM-dd').format(_workDate),
        'ot_before_minutes': int.tryParse(_beforeCtrl.text) ?? 0,
        'ot_after_minutes': int.tryParse(_afterCtrl.text) ?? 0,
        'compensation_mode': _compMode,
        'reason': _reasonCtrl.text.trim(),
      });
      ref.invalidate(overtimeRequestsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pengajuan lembur berhasil dikirim.')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final types = ref.watch(overtimeTypesProvider);
    final fmt = DateFormat('dd MMM yyyy');

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('AJUKAN LEMBUR')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          types.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (items) => IndustrialCard(
              child: DropdownButtonFormField<int>(
                decoration: const InputDecoration(labelText: 'Jenis Lembur'),
                value: _typeId,
                items: items.map((t) {
                  final type = t as Map<String, dynamic>;
                  return DropdownMenuItem<int>(
                    value: type['id'] as int,
                    child: Text('${type['code']} — ${type['name']}'),
                  );
                }).toList(),
                onChanged: (v) async {
                  setState(() => _typeId = v);
                  await _refreshPreview();
                },
              ),
            ),
          ),
          const SizedBox(height: 12),
          IndustrialCard(
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Tanggal Lembur'),
              subtitle: Text(fmt.format(_workDate)),
              trailing: const Icon(Icons.calendar_today),
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: _workDate,
                  firstDate: DateTime.now().subtract(const Duration(days: 30)),
                  lastDate: DateTime.now(),
                );
                if (picked != null) {
                  setState(() => _workDate = picked);
                  await _loadSuggested();
                }
              },
            ),
          ),
          const SizedBox(height: 12),
          IndustrialCard(
            child: Column(
              children: [
                TextField(
                  controller: _beforeCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Lembur Sebelum Shift (menit)',
                  ),
                  onChanged: (_) => _refreshPreview(),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _afterCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Lembur Sesudah Shift (menit)',
                  ),
                  onChanged: (_) => _refreshPreview(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          IndustrialCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Mode Kompensasi'),
                RadioListTile<String>(
                  title: const Text('Diuangkan (Cash)'),
                  value: 'cash',
                  groupValue: _compMode,
                  onChanged: (v) => setState(() => _compMode = v!),
                ),
                RadioListTile<String>(
                  title: const Text('Tambah Jatah Cuti'),
                  value: 'leave',
                  groupValue: _compMode,
                  onChanged: (v) => setState(() => _compMode = v!),
                ),
              ],
            ),
          ),
          if (_preview != null) ...[
            const SizedBox(height: 12),
            IndustrialCard(
              accentColor: AppColors.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeader(title: 'Estimasi Kompensasi'),
                  const SizedBox(height: 8),
                  Text('Total: ${_preview!['total_minutes']} menit'),
                  Text('Estimasi uang: Rp ${_preview!['cash_amount']}'),
                  Text('Estimasi cuti: ${_preview!['leave_days']} hari'),
                  Text(
                    'Tarif/jam: Rp ${_preview!['hourly_rate']}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          IndustrialCard(
            child: TextField(
              controller: _reasonCtrl,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Alasan / Keterangan'),
            ),
          ),
          const SizedBox(height: 24),
          NeonButton(
            label: 'Kirim Pengajuan',
            loading: _loading,
            onPressed: _submit,
            icon: Icons.send,
          ),
        ],
      ),
    );
  }
}
