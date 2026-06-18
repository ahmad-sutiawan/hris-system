import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_file/open_file.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/hris_widgets.dart';

final payslipsProvider = FutureProvider<List<dynamic>>((ref) async {
  return ref.watch(apiClientProvider).getPaginated('/payslips/');
});

class PayslipScreen extends ConsumerWidget {
  const PayslipScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final payslips = ref.watch(payslipsProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(title: const Text('Payslips')),
      body: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: () async => ref.invalidate(payslipsProvider),
        child: payslips.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              EmptyState(icon: Icons.error_outline, title: 'Gagal memuat', subtitle: '$e'),
            ],
          ),
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  EmptyState(
                    icon: Icons.receipt_long_outlined,
                    title: 'Belum ada slip gaji',
                  ),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final slip = items[i] as Map<String, dynamic>;
                return HrisCard(
                  accentColor: AppColors.success,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Periode ${slip['period_start']} — ${slip['period_end']}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 8),
                      Text('Bruto: Rp ${slip['gross_amount']}'),
                      Text('Potongan: Rp ${slip['deduction_amount']}'),
                      Text(
                        'Net: Rp ${slip['net_amount']}',
                        style: const TextStyle(
                          color: AppColors.success,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 12),
                      PrimaryButton(
                        label: 'Unduh PDF',
                        secondary: true,
                        icon: Icons.download,
                        onPressed: () => _download(context, ref, slip),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }

  Future<void> _download(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> slip,
  ) async {
    try {
      final id = slip['id'] as int;
      final code = slip['employee_code'] ?? 'slip';
      final file = await ref.read(apiClientProvider).downloadPdf(
            id,
            'slip_${code}_$id.pdf',
          );
      await OpenFile.open(file.path);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Slip gaji berhasil diunduh.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }
}
