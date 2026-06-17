import 'package:flutter/material.dart';

Future<String?> promptRejectReason(BuildContext context) async {
  final controller = TextEditingController();
  final result = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Alasan Penolakan'),
      content: TextField(
        controller: controller,
        maxLines: 3,
        autofocus: true,
        decoration: const InputDecoration(
          hintText: 'Tuliskan alasan penolakan',
          border: OutlineInputBorder(),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
        FilledButton(
          onPressed: () {
            final reason = controller.text.trim();
            if (reason.isEmpty) return;
            Navigator.pop(ctx, reason);
          },
          child: const Text('Tolak'),
        ),
      ],
    ),
  );
  controller.dispose();
  return result;
}
