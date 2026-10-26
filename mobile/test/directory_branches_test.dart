import 'package:flutter_test/flutter_test.dart';
import 'package:hris_mobile/features/employees/directory_branches.dart';

void main() {
  test('parent company with the staff branch name is hidden', () {
    final branches = directoryBranches([
      {'id': 1, 'code': 'BPS_HARIAN', 'name': 'PT. Baja Perkasa Sentosa (Harian)'},
      {'id': 2, 'code': 'BPS_STAFF', 'name': 'PT Baja Perkasa Sentosa'},
      {'id': 3, 'code': 'PT_BAJA_PERKASA_SENT', 'name': 'PT Baja Perkasa Sentosa'},
      {'id': 4, 'code': 'SPV_UP', 'name': 'PT. Baja Perkasa Sentosa (SPV Up)'},
    ]);

    expect(branches.map((row) => row['code']), ['BPS_HARIAN', 'BPS_STAFF', 'SPV_UP']);
  });

  test('entity type from the server is the source of truth', () {
    final branches = directoryBranches([
      {'id': 1, 'code': 'BPS_STAFF', 'name': 'PT Baja Perkasa Sentosa', 'entity_type': 'branch'},
      {'id': 9, 'code': 'PT_BAJA_PERKASA_SENT', 'name': 'PT Baja Perkasa Sentosa', 'entity_type': 'pt'},
    ]);

    expect(branches.map((row) => row['id']), [1]);
  });
}
