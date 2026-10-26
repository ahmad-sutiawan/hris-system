class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

String friendlyError(Object error) {
  if (error is ApiException && error.message.isNotEmpty) return error.message;
  return 'Tidak bisa memuat data. Periksa koneksi lalu coba lagi.';
}
