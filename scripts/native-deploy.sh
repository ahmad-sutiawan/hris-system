#!/usr/bin/env bash
# Wrapper — gunakan scripts/deploy.sh
exec "$(cd "$(dirname "$0")/.." && pwd)/scripts/deploy.sh" "$@"
