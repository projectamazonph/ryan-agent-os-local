#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
INSTALL_ROOT=${RAO_INSTALL_ROOT:-"$HOME/.local/share/ryan-agent-os"}
BIN_DIR=${RAO_BIN_DIR:-"$HOME/.local/bin"}
APP_DIR="$INSTALL_ROOT/app"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11 or newer is required." >&2
  exit 1
}

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -R "$PROJECT_ROOT/src" "$APP_DIR/src"

cat > "$BIN_DIR/rao" <<EOF
#!/usr/bin/env sh
RAO_EXECUTABLE="$BIN_DIR/rao" PYTHONPATH="$APP_DIR/src\${PYTHONPATH:+:\$PYTHONPATH}" exec "$PYTHON_BIN" -m rao.cli "\$@"
EOF
chmod +x "$BIN_DIR/rao"
"$BIN_DIR/rao" init

printf '\nInstalled: %s\n' "$BIN_DIR/rao"
case ":${PATH:-}:" in
  *":$BIN_DIR:"*) ;;
  *)
    printf 'Add this to your shell profile:\n  export PATH="%s:$PATH"\n' "$BIN_DIR"
    ;;
esac
