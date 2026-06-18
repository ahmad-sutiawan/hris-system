#!/usr/bin/env bash
# Generate launcher icons from assets/images/app_icon.png (1024×1024 BPS HRIS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$ROOT/assets/images/app_icon.png}"

if [ ! -f "$SRC" ]; then
  echo "Source icon not found: $SRC" >&2
  exit 1
fi

echo "Using $SRC"

# Android
sips -z 48 48 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-mdpi/ic_launcher.png"
sips -z 72 72 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-hdpi/ic_launcher.png"
sips -z 96 96 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xhdpi/ic_launcher.png"
sips -z 144 144 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png"
sips -z 192 192 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png"

# iOS
IOS="$ROOT/ios/Runner/Assets.xcassets/AppIcon.appiconset"
sips -z 1024 1024 "$SRC" --out "$IOS/Icon-App-1024x1024@1x.png"
sips -z 40 40 "$SRC" --out "$IOS/Icon-App-20x20@2x.png"
sips -z 60 60 "$SRC" --out "$IOS/Icon-App-20x20@3x.png"
sips -z 29 29 "$SRC" --out "$IOS/Icon-App-29x29@1x.png"
sips -z 58 58 "$SRC" --out "$IOS/Icon-App-29x29@2x.png"
sips -z 87 87 "$SRC" --out "$IOS/Icon-App-29x29@3x.png"
sips -z 80 80 "$SRC" --out "$IOS/Icon-App-40x40@2x.png"
sips -z 120 120 "$SRC" --out "$IOS/Icon-App-40x40@3x.png"
sips -z 120 120 "$SRC" --out "$IOS/Icon-App-60x60@2x.png"
sips -z 180 180 "$SRC" --out "$IOS/Icon-App-60x60@3x.png"
sips -z 20 20 "$SRC" --out "$IOS/Icon-App-20x20@1x.png"
sips -z 40 40 "$SRC" --out "$IOS/Icon-App-40x40@1x.png"
sips -z 76 76 "$SRC" --out "$IOS/Icon-App-76x76@1x.png"
sips -z 152 152 "$SRC" --out "$IOS/Icon-App-76x76@2x.png"
sips -z 167 167 "$SRC" --out "$IOS/Icon-App-83.5x83.5@2x.png"

# Web PWA
mkdir -p "$ROOT/web/icons"
sips -z 192 192 "$SRC" --out "$ROOT/web/icons/Icon-192.png"
sips -z 512 512 "$SRC" --out "$ROOT/web/icons/Icon-512.png"
cp "$ROOT/web/icons/Icon-192.png" "$ROOT/web/icons/Icon-maskable-192.png"
cp "$ROOT/web/icons/Icon-512.png" "$ROOT/web/icons/Icon-maskable-512.png"
sips -z 32 32 "$SRC" --out "$ROOT/web/favicon.png"

echo "Done — Android, iOS, Web icons updated."
