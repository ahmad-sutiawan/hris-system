# HRIS Employee Mobile (Flutter)

Aplikasi mobile **employee-only** untuk HRIS-Lite — terhubung ke REST API Django.

## Fitur employee (parity web)

| Fitur Web | Mobile | Status |
|---|---|---|
| Dashboard + absen masuk/pulang (selfie) | Beranda + Absen | ✓ |
| Notifikasi + tandai dibaca | Notifikasi | ✓ |
| Pengumuman + dismiss | Pengumuman | ✓ |
| Detail Karyawan + statistik + jadwal shift | Profil | ✓ |
| Rekap Absensi / timesheet | Tab Absensi | ✓ |
| Pengajuan Cuti + saldo + batalkan | Tab Cuti | ✓ |
| Pengajuan Lembur + preview + batalkan | Tab Lembur | ✓ |
| Slip Gaji + unduh PDF | Slip Gaji | ✓ |
| Logout | Akun | ✓ |

## Build APK (install di Android)

### Prasyarat

- Flutter SDK + Android SDK (`flutter doctor` harus OK untuk Android)
- Backend HRIS jalan dan bisa diakses dari HP (satu jaringan WiFi)

### Langkah build

```bash
cd mobile
flutter pub get

# APK release (siap install)
flutter build apk --release
```

File APK hasil build:

```
mobile/build/app/outputs/flutter-apk/app-release.apk
```

Copy ke HP Android → buka file → izinkan "Install from unknown sources" jika diminta.

### APK split per arsitektur (ukuran lebih kecil)

```bash
flutter build apk --split-per-abi --release
```

Output: `app-armeabi-v7a-release.apk`, `app-arm64-v8a-release.apk`, dll.  
HP modern biasanya **arm64-v8a**.

### Konfigurasi server di HP fisik

Saat pertama login, tap **Pengaturan server** dan isi IP komputer server:

```
http://192.168.x.x:8000
```

Pastikan:
1. Backend: `python manage.py runserver 0.0.0.0:8000`
2. HP dan PC **satu WiFi**
3. Firewall PC izinkan port 8000

Emulator Android otomatis pakai `http://10.0.2.2:8000`.

### Build dengan IP server baku (opsional)

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=http://192.168.1.50:8000/api/v1
```

## Menjalankan (development)

```bash
# Terminal 1 — backend
cd ..
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000

# Terminal 2 — mobile
cd mobile
flutter run -d chrome          # browser
flutter run                    # pilih emulator/device
```

Login demo: `budi` / `Employee123!`

## Desain UI

- Tema terang industrial — ramah untuk karyawan pabrik
- Font Plus Jakarta Sans, tombol besar (min 48px)
- Nav: Beranda · Absensi · Cuti · Lembur · Akun

## Izin Android

- `INTERNET` — API HRIS
- `CAMERA` — selfie absensi

## Production

- Ganti HTTP → **HTTPS** di server production
- Tanda tangani APK release dengan keystore perusahaan (bukan debug key)
- Set `applicationId`: `id.bps.hris.employee`

Lihat [`docs/API_FLUTTER.md`](../docs/API_FLUTTER.md) untuk dokumentasi API.
