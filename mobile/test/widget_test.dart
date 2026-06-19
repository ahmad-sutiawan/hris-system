import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:hris_mobile/app.dart';

void main() {
  testWidgets('App renders login screen', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: HrisApp()),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 800));

    expect(find.text('Masuk dengan NIK dan Employee ID Anda'), findsOneWidget);
    expect(find.text('Masuk'), findsWidgets);
    expect(find.text('NIK'), findsWidgets);
    expect(find.text('Employee ID'), findsWidgets);
  });
}
