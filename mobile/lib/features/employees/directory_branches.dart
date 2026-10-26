const branchPlantCodes = {'BPS_HARIAN', 'BPS_STAFF', 'SPV_UP'};

/// Cabang yang sama dengan master Cabang di web admin.
///
/// Server baru mengirim [entity_type]. Server yang masih berjalan mengirim
/// perusahaan induk dengan nama yang sama seperti cabang staff, tanpa tipe.
List<Map<String, dynamic>> directoryBranches(List plants) {
  final rows = <Map<String, dynamic>>[
    for (final raw in plants)
      if (raw is Map) Map<String, dynamic>.from(raw),
  ];
  final typed = rows.any((row) => row['entity_type'] != null);
  final candidates = typed
      ? rows.where((row) => row['entity_type'] == 'branch').toList()
      : rows;

  final codesByName = <String, Set<String>>{};
  for (final row in candidates) {
    final name = _plantName(row);
    final code = _plantCode(row);
    codesByName.putIfAbsent(name, () => {}).add(code);
  }

  return [
    for (final row in candidates)
      if (_keepBranch(row, codesByName)) row,
  ];
}

bool _keepBranch(Map<String, dynamic> row, Map<String, Set<String>> codesByName) {
  final codes = codesByName[_plantName(row)] ?? {};
  if (codes.length < 2) return true;
  final code = _plantCode(row);
  if (branchPlantCodes.contains(code)) return true;
  return !codes.any(branchPlantCodes.contains);
}

String _plantName(Map<String, dynamic> row) {
  return (row['name'] as String? ?? '').trim().toLowerCase();
}

String _plantCode(Map<String, dynamic> row) {
  return (row['code'] as String? ?? '').trim().toUpperCase();
}
