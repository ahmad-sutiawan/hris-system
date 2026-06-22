import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/money_utils.dart';
import '../../core/widgets/employee_avatar.dart';
import '../../core/widgets/hris_widgets.dart';

final profileProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getProfile();
});

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider);

    return HrisScaffold(
      appBar: hrisAppBar(title: 'Profil Karyawan'),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(profileProvider),
        child: profile.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat profil', subtitle: '$e'),
            ],
          ),
          data: (data) {
            final emp = data['employee'] as Map<String, dynamic>;
            final stats = data['month_stats'] as Map<String, dynamic>? ?? {};
            final balances = data['leave_balances'] as List? ?? [];
            final shifts = data['upcoming_shifts'] as List? ?? [];
            final todayShift = data['today_assignment'] as Map<String, dynamic>?;
            final defaultShift = emp['default_shift'] as Map<String, dynamic>?;
            final salaryPreview = data['salary_preview'] as Map<String, dynamic>?;
            final latestPayslip = data['latest_payslip'] as Map<String, dynamic>?;
            final todayTimesheet = data['today_timesheet'] as Map<String, dynamic>?;
            final recentTimesheets = data['recent_timesheets'] as List? ?? [];
            final deptName = emp['department_name'] as String? ?? emp['department'] as String?;
            final fmt = DateFormat('dd MMM');
            final timeFmt = DateFormat('HH:mm');

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                HrisCard(
                  accentColor: AppColors.accent,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          EmployeeAvatar(
                            photoUrl: emp['photo_url'] as String?,
                            name: emp['full_name'] as String? ?? '',
                            size: 56,
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  emp['full_name'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${emp['employee_id']} · ${emp['status_label'] ?? emp['status']}',
                                  style: const TextStyle(color: AppColors.textSecondary),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _InfoRow('Plant', emp['plant']),
                      _InfoRow('Departemen', deptName),
                      _InfoRow('Jabatan', emp['job_title']),
                      _InfoRow('Atasan', emp['manager_name']),
                      if (emp['join_date'] != null)
                        _InfoRow(
                          'Bergabung',
                          fmt.format(DateTime.parse(emp['join_date'] as String)),
                        ),
                      _InfoRow('Email', emp['email']),
                      _InfoRow('Telepon', emp['phone']),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => context.push('/payslips'),
                      icon: const Icon(Icons.receipt_long_outlined, size: 18),
                      label: const Text('Slip Gaji'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => context.push('/attendance'),
                      icon: const Icon(Icons.history_rounded, size: 18),
                      label: const Text('Riwayat Absensi'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => context.push('/punch?action=in'),
                      icon: const Icon(Icons.fingerprint_rounded, size: 18),
                      label: const Text('Absen Masuk/Pulang'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const SectionHeader(title: 'Gaji & Tunjangan'),
                const SizedBox(height: 10),
                HrisCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _InfoRow('Skema', emp['salary_scheme_label'] ?? emp['salary_scheme']),
                      _InfoRow('Gaji pokok', formatRupiah(emp['base_salary'])),
                      _InfoRow('Tunj. transport', formatRupiah(emp['allowance_transport'])),
                      _InfoRow('Tunj. makan', formatRupiah(emp['allowance_meal'])),
                      _InfoRow('Tunj. jabatan', formatRupiah(emp['allowance_position'])),
                      _InfoRow('Total komponen', formatRupiah(data['total_compensation'])),
                      _InfoRow('Gaji harian efektif', formatRupiah(data['effective_daily_wage'])),
                      _InfoRow('Tarif per jam', formatRupiah(data['effective_hourly_wage'])),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const SectionHeader(title: 'PPh 21 — TER PP 58/2023'),
                const SizedBox(height: 10),
                HrisCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _InfoRow('PTKP', emp['tax_status']),
                      _InfoRow('NPWP', emp['npwp']),
                      _InfoRow(
                        'Potong PPh 21',
                        emp['pph21_deduct'] == false ? 'Tidak' : (emp['pph21_deduct'] == true ? 'Ya' : '—'),
                      ),
                      if (salaryPreview != null) ...[
                        ...() {
                          final pph21 = salaryPreview['pph21'] as Map<String, dynamic>? ?? {};
                          return [
                            if (pph21['ter_category'] != null)
                              _InfoRow('Kategori TER', pph21['ter_category']),
                            if (pph21['ter_rate_percent'] != null)
                              _InfoRow('Tarif efektif', '${pph21['ter_rate_percent']}%'),
                            if (pph21['skipped'] == true && pph21['reason'] != null)
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text(
                                  'PPh 21: ${pph21['reason']}',
                                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                                ),
                              ),
                          ];
                        }(),
                      ],
                    ],
                  ),
                ),
                if (salaryPreview != null) ...[
                  const SizedBox(height: 16),
                  _SalaryPreviewCard(preview: salaryPreview),
                ],
                if (latestPayslip != null) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Slip Gaji Terakhir'),
                  const SizedBox(height: 10),
                  HrisCard(
                    accentColor: AppColors.success,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Periode ${latestPayslip['period_start']} — ${latestPayslip['period_end']}',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        Text('Bruto: ${formatRupiah(latestPayslip['gross_amount'])}'),
                        Text('Take-home: ${formatRupiah(latestPayslip['net_amount'])}'),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                const SectionHeader(title: 'BPJS & Rekening'),
                const SizedBox(height: 10),
                HrisCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _InfoRow('BPJS Kesehatan', emp['bpjs_kesehatan_number']),
                      _InfoRow('BPJS Ketenagakerjaan', emp['bpjs_ketenagakerjaan_number']),
                      _InfoRow('Bank', emp['bank_name']),
                      _InfoRow('No. rekening', emp['bank_account_number']),
                      _InfoRow('Atas nama', emp['bank_account_name']),
                    ],
                  ),
                ),
                if (todayShift != null || defaultShift != null) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Shift'),
                  const SizedBox(height: 10),
                  HrisCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (todayShift != null) ...[
                          Text(
                            'Shift hari ini',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textMuted,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${todayShift['shift_name'] ?? todayShift['shift_code']} '
                            '(${todayShift['shift_code'] ?? '—'})',
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          if (todayShift['scheduled_check_in'] != null &&
                              todayShift['scheduled_check_out'] != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                '${timeFmt.format(DateTime.parse(todayShift['scheduled_check_in'] as String).toLocal())} — '
                                '${timeFmt.format(DateTime.parse(todayShift['scheduled_check_out'] as String).toLocal())}',
                                style: const TextStyle(color: AppColors.textSecondary),
                              ),
                            ),
                        ],
                        if (defaultShift != null) ...[
                          if (todayShift != null) const SizedBox(height: 12),
                          Text(
                            defaultShift['source_label'] as String? ?? 'Shift default',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textMuted,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${defaultShift['name']} (${defaultShift['code']})',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
                if (todayTimesheet != null || recentTimesheets.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Absensi & Timesheet'),
                  const SizedBox(height: 10),
                  if (todayTimesheet != null)
                    HrisCard(
                      accentColor: AppColors.accent,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Hari ini',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: 6),
                          ..._timesheetRows(todayTimesheet, fmt, timeFmt),
                        ],
                      ),
                    ),
                  if (recentTimesheets.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ...recentTimesheets.take(7).map((raw) {
                      final ts = raw as Map<String, dynamic>;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: HrisCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                fmt.format(DateTime.parse(ts['work_date'] as String)),
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: 4),
                              ..._timesheetRows(ts, fmt, timeFmt),
                            ],
                          ),
                        ),
                      );
                    }),
                  ],
                ],
                const SizedBox(height: 16),
                const SectionHeader(title: 'Statistik Bulan Ini'),
                const SizedBox(height: 10),
                HrisCard(
                  child: Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      _StatTile('Hadir', '${stats['present_days'] ?? 0} hari'),
                      _StatTile('Alpha', '${stats['alpha_days'] ?? 0} hari'),
                      _StatTile('Telat', '${stats['late_minutes'] ?? 0} m'),
                      _StatTile('OT', '${(stats['ot_before_minutes'] ?? 0) + (stats['ot_after_minutes'] ?? 0)} m'),
                    ],
                  ),
                ),
                if (balances.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Saldo Cuti'),
                  const SizedBox(height: 10),
                  ...balances.map((b) {
                    final bal = b as Map<String, dynamic>;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: HrisCard(
                        child: Text(
                          '${bal['leave_type_code']}: sisa ${bal['remaining']} hari '
                          '(pending ${bal['pending']})',
                        ),
                      ),
                    );
                  }),
                ],
                if (shifts.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const SectionHeader(title: 'Jadwal Shift (14 hari)'),
                  const SizedBox(height: 10),
                  ...shifts.map((s) {
                    final shift = s as Map<String, dynamic>;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: HrisCard(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(fmt.format(DateTime.parse(shift['work_date'] as String))),
                          subtitle: Text(
                            '${shift['shift_code']} — ${shift['shift_name'] ?? ''}',
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

List<Widget> _timesheetRows(
  Map<String, dynamic> ts,
  DateFormat dateFmt,
  DateFormat timeFmt,
) {
  String? inLabel;
  String? outLabel;
  if (ts['check_in'] != null) {
    inLabel = timeFmt.format(DateTime.parse(ts['check_in'] as String).toLocal());
  }
  if (ts['check_out'] != null) {
    outLabel = timeFmt.format(DateTime.parse(ts['check_out'] as String).toLocal());
  }

  return [
    _InfoRow('Shift', ts['shift_code']),
    _InfoRow('Clock in', inLabel),
    _InfoRow('Clock out', outLabel),
    _InfoRow('Kode', ts['attendance_code']),
    if ((ts['late_in_minutes'] as int? ?? 0) > 0)
      _InfoRow('Telat', '${ts['late_in_minutes']} m'),
    if (((ts['ot_before_minutes'] as int? ?? 0) + (ts['ot_after_minutes'] as int? ?? 0)) > 0)
      _InfoRow(
        'Lembur',
        '${(ts['ot_before_minutes'] as int? ?? 0) + (ts['ot_after_minutes'] as int? ?? 0)} m',
      ),
  ];
}

class _SalaryPreviewCard extends StatelessWidget {
  const _SalaryPreviewCard({required this.preview});

  final Map<String, dynamic> preview;

  @override
  Widget build(BuildContext context) {
    final earnings = preview['earnings'] as List? ?? [];
    final deductions = preview['deductions'] as List? ?? [];

    return HrisCard(
      accentColor: AppColors.info,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeader(title: 'Simulasi Perhitungan Gaji'),
          const SizedBox(height: 4),
          Text(
            preview['scenario'] as String? ?? '',
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
          const SizedBox(height: 12),
          const Text('Pendapatan', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
          ...earnings.map((item) => _PreviewLine(item as Map<String, dynamic>)),
          _PreviewTotal('Bruto estimasi', preview['gross'], positive: true),
          const SizedBox(height: 10),
          const Text('Potongan', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
          ...deductions.map((item) => _PreviewLine(item as Map<String, dynamic>, deduct: true)),
          _PreviewTotal('Total potongan', preview['deductions_total'], deduct: true),
          const Divider(height: 20),
          _PreviewTotal('Take-home pay estimasi', preview['net'], highlight: true),
        ],
      ),
    );
  }
}

class _PreviewLine extends StatelessWidget {
  const _PreviewLine(this.item, {this.deduct = false});

  final Map<String, dynamic> item;
  final bool deduct;

  @override
  Widget build(BuildContext context) {
    final note = item['note'] as String?;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(item['label'] as String? ?? '', style: const TextStyle(fontSize: 13))),
              Text(
                deduct ? '− ${formatRupiah(item['amount'])}' : formatRupiah(item['amount']),
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: deduct ? AppColors.error : null,
                ),
              ),
            ],
          ),
          if (note != null && note.isNotEmpty)
            Text(note, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _PreviewTotal extends StatelessWidget {
  const _PreviewTotal(this.label, this.amount, {this.deduct = false, this.positive = false, this.highlight = false});

  final String label;
  final dynamic amount;
  final bool deduct;
  final bool positive;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(top: highlight ? 0 : 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontWeight: highlight ? FontWeight.w800 : FontWeight.w700,
                fontSize: highlight ? 15 : 13,
              ),
            ),
          ),
          Text(
            deduct ? '− ${formatRupiah(amount)}' : formatRupiah(amount),
            style: TextStyle(
              fontWeight: FontWeight.w800,
              fontSize: highlight ? 16 : 13,
              color: deduct
                  ? AppColors.error
                  : (highlight ? AppColors.accent : (positive ? AppColors.success : null)),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final dynamic value;

  @override
  Widget build(BuildContext context) {
    if (value == null || '$value'.isEmpty || value == '—') {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
          ),
          Expanded(child: Text('$value')),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 140,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
