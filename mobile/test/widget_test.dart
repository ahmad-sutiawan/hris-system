import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:hris_mobile/app.dart';

void main() {
  testWidgets('App renders login screen', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: HrisApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Portal Karyawan'), findsOneWidget);
  });
}
