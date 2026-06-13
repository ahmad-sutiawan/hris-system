# PT BPS HRIS — Mobile Karyawan (Flutter)

Aplikasi mobile **employee-only** untuk HRIS-Lite — terhubung ke REST API Django. Branding, palet warna, logo, dan konten login **identik dengan portal web**.

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

# APK release (siap install) — ~57 MB
flutter build apk --release
```

**APK terbaru (jika sudah pernah build):**

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

### Konfigurasi server

**Production (default di APK release):**

```
http://148.230.98.125:8080
```

Portal web: [http://148.230.98.125:8080/](http://148.230.98.125:8080/)

APK release otomatis terhubung ke server di atas — **tidak perlu** atur server manual di HP.

Untuk development lokal, tap **Pengaturan server** dan isi IP komputer:

```
http://192.168.x.x:8000
```

Pastikan:
1. Backend: `python manage.py runserver 0.0.0.0:8000`
2. HP dan PC **satu WiFi**
3. Firewall PC izinkan port 8000

Emulator Android (dev): `http://10.0.2.2:8000`.

### Build dengan URL server kustom (opsional)

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=http://148.230.98.125:8080/api/v1
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

- Tema gelap industrial — **sama dengan web** (`static/css/hris.css`)
- Palet web/mobile: navy `#140B6E`, purple `#3428A8`, blue `#3269CC`, gold `#FBD02F`, bg `#F3F5FC`
- Logo & hero login dari `static/img/` (logo.png, login-hero.jpg)
- Font Plus Jakarta Sans, sudut tajam (radius 0), tombol min 48px
- Nav: Beranda · Absensi · Cuti · Lembur · Akun

## Izin Android

- `INTERNET` — API HRIS
- `CAMERA` — selfie absensi

## Production

- Ganti HTTP → **HTTPS** di server production
- Tanda tangani APK release dengan keystore perusahaan (bukan debug key)
- Set `applicationId`: `id.bps.hris.employee`

Swagger API docs: `{SERVER_URL}/api/docs/` (contoh `http://127.0.0.1:8000/api/docs/`).
