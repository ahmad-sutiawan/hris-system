import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/animated_interactions.dart';
import '../../core/widgets/hris_widgets.dart';

class EmployeeDirectoryQuery {
  const EmployeeDirectoryQuery({
    this.search = '',
    this.plantId,
    this.jobPositionId,
  });

  final String search;
  final int? plantId;
  final int? jobPositionId;

  Map<String, dynamic> toParams() {
    return {
      if (search.trim().isNotEmpty) 'search': search.trim(),
      if (plantId != null) 'plant': plantId,
      if (jobPositionId != null) 'job_position': jobPositionId,
    };
  }

  @override
  bool operator ==(Object other) {
    return other is EmployeeDirectoryQuery &&
        other.search == search &&
        other.plantId == plantId &&
        other.jobPositionId == jobPositionId;
  }

  @override
  int get hashCode => Object.hash(search, plantId, jobPositionId);
}

final employeeFilterOptionsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.watch(apiClientProvider).get('/mobile/employees/filters/');
});

final employeeDirectoryProvider =
    FutureProvider.family<List<dynamic>, EmployeeDirectoryQuery>((ref, query) async {
  return ref.watch(apiClientProvider).getPaginatedAll(
        '/employees/',
        query: query.toParams(),
        pageSize: 80,
      );
});

class EmployeesScreen extends ConsumerStatefulWidget {
  const EmployeesScreen({super.key});

  @override
  ConsumerState<EmployeesScreen> createState() => _EmployeesScreenState();
}

class _EmployeesScreenState extends ConsumerState<EmployeesScreen> {
  final _searchController = TextEditingController();
  Timer? _debounce;
  String _search = '';
  int? _plantId;
  int? _jobPositionId;

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  EmployeeDirectoryQuery get _query => EmployeeDirectoryQuery(
        search: _search,
        plantId: _plantId,
        jobPositionId: _jobPositionId,
      );

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) return;
      setState(() => _search = value);
    });
  }

  void _clearFilters() {
    setState(() {
      _plantId = null;
      _jobPositionId = null;
      _search = '';
      _searchController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final filters = ref.watch(employeeFilterOptionsProvider);
    final employees = ref.watch(employeeDirectoryProvider(_query));
    final hasFilters = _plantId != null || _jobPositionId != null || _search.isNotEmpty;

    return HrisScaffold(
      withBackground: false,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _EmployeesHero(
            total: employees.maybeWhen(data: (v) => v.length, orElse: () => null),
          ),
          Expanded(
            child: RefreshIndicator(
              color: AppColors.cyan,
              onRefresh: () async {
                ref.invalidate(employeeFilterOptionsProvider);
                ref.invalidate(employeeDirectoryProvider(_query));
              },
              child: CustomScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: TextField(
                  controller: _searchController,
                  onChanged: _onSearchChanged,
                  decoration: InputDecoration(
                    hintText: 'Cari nama, ID, email…',
                    prefixIcon: const Icon(Icons.search_rounded, color: AppColors.textMuted),
                    suffixIcon: _search.isNotEmpty
                        ? IconButton(
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _search = '');
                            },
                            icon: const Icon(Icons.close_rounded),
                          )
                        : null,
                    filled: true,
                    fillColor: AppColors.surface,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: filters.when(
                loading: () => const SizedBox(height: 4),
                error: (_, __) => const SizedBox(height: 4),
                data: (data) => _FilterSection(
                  plants: (data['plants'] as List?) ?? const [],
                  positions: (data['job_positions'] as List?) ?? const [],
                  plantId: _plantId,
                  jobPositionId: _jobPositionId,
                  onPlantChanged: (value) => setState(() {
                    _plantId = value;
                    _jobPositionId = null;
                  }),
                  onPositionChanged: (value) => setState(() => _jobPositionId = value),
                  onClear: hasFilters ? _clearFilters : null,
                ),
              ),
            ),
            employees.when(
              loading: () => const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator(color: AppColors.chinaRed)),
              ),
              error: (e, _) => SliverFillRemaining(
                child: EmptyState(
                  icon: Icons.error_outline_rounded,
                  title: 'Gagal memuat karyawan',
                  subtitle: '$e',
                ),
              ),
              data: (items) {
                if (items.isEmpty) {
                  return const SliverFillRemaining(
                    child: EmptyState(
                      icon: Icons.people_outline_rounded,
                      title: 'Tidak ada karyawan',
                      subtitle: 'Coba ubah kata kunci atau filter pencarian',
                    ),
                  );
                }
                return SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final emp = items[index] as Map<String, dynamic>;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: FadeSlideIn(
                            index: index,
                            delayMs: 20,
                            child: _EmployeeCard(
                              employee: emp,
                              onTap: () => context.push('/employees/${emp['id']}'),
                            ),
                          ),
                        );
                      },
                      childCount: items.length,
                    ),
                  ),
                );
              },
            ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmployeesHero extends StatelessWidget {
  const _EmployeesHero({this.total});

  final int? total;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.brandBlue, AppColors.brandPurple],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.brandBlue.withValues(alpha: 0.28),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.people_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Direktori Karyawan',
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  total == null
                      ? 'Cari dan filter seluruh karyawan'
                      : '$total karyawan ditampilkan',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.88),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterSection extends StatelessWidget {
  const _FilterSection({
    required this.plants,
    required this.positions,
    required this.plantId,
    required this.jobPositionId,
    required this.onPlantChanged,
    required this.onPositionChanged,
    this.onClear,
  });

  final List plants;
  final List positions;
  final int? plantId;
  final int? jobPositionId;
  final ValueChanged<int?> onPlantChanged;
  final ValueChanged<int?> onPositionChanged;
  final VoidCallback? onClear;

  List<Map<String, dynamic>> get _positionsForPlant {
    final rows = positions.whereType<Map<String, dynamic>>();
    if (plantId == null) return rows.toList();
    return rows.where((row) => row['plant_id'] == plantId).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Filter',
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: AppColors.textMuted,
                ),
              ),
              const Spacer(),
              if (onClear != null)
                TextButton(
                  onPressed: onClear,
                  child: const Text('Reset'),
                ),
            ],
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<int?>(
            value: plantId,
            isExpanded: true,
            decoration: _filterDecoration('Branch', AppColors.cyan),
            items: [
              const DropdownMenuItem<int?>(value: null, child: Text('Semua branch')),
              for (final raw in plants)
                if (raw is Map<String, dynamic>)
                  DropdownMenuItem<int?>(
                    value: raw['id'] as int?,
                    child: Text('${raw['code']} — ${raw['name']}'),
                  ),
            ],
            onChanged: onPlantChanged,
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<int?>(
            value: jobPositionId,
            isExpanded: true,
            decoration: _filterDecoration('Position', AppColors.brandOrange),
            items: [
              const DropdownMenuItem<int?>(value: null, child: Text('Semua position')),
              for (final raw in _positionsForPlant)
                DropdownMenuItem<int?>(
                  value: raw['id'] as int?,
                  child: Text(raw['title'] as String? ?? '—'),
                ),
            ],
            onChanged: onPositionChanged,
          ),
        ],
      ),
    );
  }

  InputDecoration _filterDecoration(String label, Color accent) {
    return InputDecoration(
      labelText: label,
      labelStyle: TextStyle(color: accent, fontWeight: FontWeight.w700, fontSize: 12),
      filled: true,
      fillColor: accent.withValues(alpha: 0.06),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: accent.withValues(alpha: 0.22)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: accent, width: 1.5),
      ),
    );
  }
}

class _EmployeeCard extends StatelessWidget {
  const _EmployeeCard({required this.employee, required this.onTap});

  final Map<String, dynamic> employee;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final initials = _initials(employee['full_name'] as String? ?? '?');

    return AnimatedPress(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
          boxShadow: const [
            BoxShadow(color: AppColors.cardShadow, blurRadius: 12, offset: Offset(0, 4)),
          ],
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: AppColors.cyanDim,
              child: Text(
                initials,
                style: GoogleFonts.plusJakartaSans(
                  color: AppColors.cyan,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    employee['full_name'] as String? ?? '—',
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    employee['employee_id'] as String? ?? '—',
                    style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    [
                      employee['plant_code'],
                      employee['job_title'],
                    ].whereType<String>().where((v) => v.isNotEmpty).join(' · '),
                    style: const TextStyle(fontSize: 12, color: AppColors.textDim),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }

  static String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }
}
