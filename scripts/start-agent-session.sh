#!/usr/bin/env sh
set -eu

WORKSPACE=${1:?Usage: start-agent-session.sh WORKSPACE OBJECTIVE [AGENT]}
OBJECTIVE=${2:?Usage: start-agent-session.sh WORKSPACE OBJECTIVE [AGENT]}
AGENT=${3:-${RAO_AGENT:-unknown-agent}}

exec rao start "$WORKSPACE" --agent "$AGENT" --objective "$OBJECTIVE"
