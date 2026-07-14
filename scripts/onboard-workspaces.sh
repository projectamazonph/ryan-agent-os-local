#!/usr/bin/env sh
set -eu

ROOT=${1:-"$HOME/workspaces"}
DEPTH=${2:-2}

rao scan "$ROOT" --depth "$DEPTH" --register
rao projects
