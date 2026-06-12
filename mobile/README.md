# HRIS Employee Mobile (Flutter)

Aplikasi mobile **employee-only** untuk HRIS-Lite — UI industrial futuristik, terhubung ke REST API Django.

## Fitur (parity dengan web employee)

| Fitur | Screen |
|---|---|
| Dashboard + Clock In/Out (selfie) | Home, Punch |
| Rekap Absensi / Timesheet | Absensi |
| Pengajuan Cuti + saldo + batalkan | Cuti |
| Pengajuan Lembur + preview kompensasi + batalkan | Lembur |
| Slip Gaji + download PDF | Slip Gaji |
| Detail Karyawan + statistik bulan + shift | Profil |
| Notifikasi + tandai dibaca | Notifikasi |
| Pengumuman + dismiss banner | Pengumuman |
| Logout | Menu |

## Prasyarat

- Flutter SDK 3.2+
- Backend HRIS berjalan (`python manage.py runserver`)
- Akun demo: `budi` / `Employee123!`

## Setup

```bash
cd mobile

# Jika folder platform belum ada (android/ios):
flutter create . --project-name hris_mobile

flutter pub get
```

### Konfigurasi API URL

Edit `lib/core/config/app_config.dart`:

| Platform | URL |
|---|---|
| Android Emulator | `http://10.0.2.2:8000/api/v1` (default) |
| iOS Simulator | `http://127.0.0.1:8000/api/v1` |
| Device fisik | `http://<IP-LAN-PC>:8000/api/v1` |

## Menjalankan

```bash
# Terminal 1 — backend
cd ..
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000

# Terminal 2 — mobile
cd mobile
flutter run
```

## Desain UI

- Tema gelap industrial dengan grid pattern
- Aksen amber/orange + cyan neon
- Tipografi: Orbitron (heading) + IBM Plex Sans (body)
- Komponen: `IndustrialCard`, `NeonButton`, `StatusBadge`

## Struktur

```
lib/
  core/          # theme, API client, auth
  features/      # auth, home, attendance, leave, overtime, payslip, profile, notifications, announcements, menu
  router/        # go_router + bottom nav shell
```

Lihat juga [`docs/API_FLUTTER.md`](../docs/API_FLUTTER.md) untuk dokumentasi endpoint lengkap.
