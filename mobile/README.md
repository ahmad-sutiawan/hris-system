# PT BPS HRIS — Mobile Karyawan (Flutter)

Aplikasi mobile **employee-only** untuk HRIS-Lite — terhubung ke REST API Django. Branding, palet warna, logo, dan konten login **identik dengan portal web**.

## Fitur employee (parity web)

| Fitur Web | Mobile | Status |
|---|---|---|
| Dashboard + absen masuk/pulang (selfie) | Beranda + Absen | ✓ |
| Notifikasi + tandai dibaca | Notifikasi | ✓ |
| Pengumuman + dismiss | Pengumuman | ✓ |
| Detail Karyawan + statistik + jadwal shift + shift default | Profil | ✓ |
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

## Server API (dev & release)

Mobile **selalu** connect ke backend publik:

```
http://148.230.98.125:8080/api/v1
```

Dev (`flutter run`) dan APK release memakai **credential yang sama** — tidak perlu arahkan ke localhost.

Override hanya jika benar-benar perlu (staging):

```bash
flutter run --dart-define=API_BASE_URL=http://148.230.98.125:8080/api/v1
flutter build apk --release --dart-define=API_BASE_URL=http://148.230.98.125:8080/api/v1
```

## Menjalankan (development)

```bash
# Terminal 1 — backend publik sudah jalan di 148.230.98.125:8080

# Terminal 2 — mobile (connect ke backend publik)
cd mobile
flutter run -d chrome          # browser
flutter run                    # pilih emulator/device
```

Login karyawan (mobile & web): **NIK** + **Employee ID** — contoh `3604231902010003` / `1704`. Admin: `admin` / `Admin123456!`

Setelah menambah karyawan baru, jalankan `python manage.py sync_employee_credentials` jika akun login belum otomatis tersinkron.

## Desain UI

- Tema gelap industrial — **sama dengan web** (`static/css/hris.css`)
- Palet web/mobile: navy `#140B6E`, purple `#3428A8`, blue `#3269CC`, gold `#FBD02F`, bg `#F3F5FC`
- Logo & hero login dari `static/img/` (main-logo.png, login-hero.jpg)
- Icon launcher Android dari `static/img/apk-logo.png` (jalankan `mobile/scripts/generate-app-icons.sh`)
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
