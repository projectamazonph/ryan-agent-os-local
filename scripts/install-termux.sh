#!/data/data/com.termux/files/usr/bin/sh
set -eu

if ! command -v pkg >/dev/null 2>&1; then
  echo "This installer is intended for Termux." >&2
  exit 1
fi

pkg install -y python git
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SCRIPT_DIR/install.sh"
