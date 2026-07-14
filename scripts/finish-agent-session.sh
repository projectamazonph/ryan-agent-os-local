#!/usr/bin/env sh
set -eu

WORKSPACE=${1:?Usage: finish-agent-session.sh WORKSPACE OBJECTIVE STATUS NEXT_ACTION}
OBJECTIVE=${2:?Usage: finish-agent-session.sh WORKSPACE OBJECTIVE STATUS NEXT_ACTION}
STATUS=${3:?Usage: finish-agent-session.sh WORKSPACE OBJECTIVE STATUS NEXT_ACTION}
NEXT_ACTION=${4:?Usage: finish-agent-session.sh WORKSPACE OBJECTIVE STATUS NEXT_ACTION}

rao handoff write "$WORKSPACE" --objective "$OBJECTIVE" --status "$STATUS" --next "$NEXT_ACTION"
rao session close "$WORKSPACE" --status "$STATUS" --next "$NEXT_ACTION"
