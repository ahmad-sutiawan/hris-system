import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hris_mobile/core/widgets/app_splash.dart';

void main() {
  testWidgets('logo fades in, then the splash leaves the screen', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AppSplash(child: Text('beranda')),
      ),
    );

    expect(find.text('beranda'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);

    final mark = tester.widget<FadeTransition>(find.byType(FadeTransition).last);
    expect(mark.opacity.value, 0);

    await tester.pump(const Duration(milliseconds: 700));
    expect(mark.opacity.value, greaterThan(0.9));

    await tester.pump(const Duration(milliseconds: 1100));
    await tester.pump();

    expect(find.byType(Image), findsNothing);
    expect(find.text('beranda'), findsOneWidget);
  });
}
