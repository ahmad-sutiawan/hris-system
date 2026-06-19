#!/usr/bin/env bash
# Generate Android launcher icons from static/img/apk-logo.png (icon saat install APK).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$ROOT/../static/img/apk-logo.png}"

if [ ! -f "$SRC" ]; then
  echo "Source icon not found: $SRC" >&2
  exit 1
fi

echo "Using $SRC (Android launcher only)"

# Android — ic_launcher untuk icon di home screen setelah install
sips -z 48 48 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-mdpi/ic_launcher.png"
sips -z 72 72 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-hdpi/ic_launcher.png"
sips -z 96 96 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xhdpi/ic_launcher.png"
sips -z 144 144 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png"
sips -z 192 192 "$SRC" --out "$ROOT/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png"

echo "Done — Android launcher icons updated from apk-logo.png."
