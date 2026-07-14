# Source this file from ~/.bashrc or ~/.zshrc.

cproj() {
  if [ "$#" -ne 1 ]; then
    echo "Usage: cproj WORKSPACE" >&2
    return 2
  fi
  target=$(rao resolve "$1") || return
  cd "$target" || return
  rao context "$1"
}

rstart() {
  if [ "$#" -lt 2 ]; then
    echo "Usage: rstart WORKSPACE OBJECTIVE [AGENT]" >&2
    return 2
  fi
  workspace=$1
  objective=$2
  agent=${3:-${RAO_AGENT:-unknown-agent}}
  rao start "$workspace" --agent "$agent" --objective "$objective"
}

rship() {
  if [ "$#" -lt 2 ]; then
    echo "Usage: rship WORKSPACE COMMIT_MESSAGE" >&2
    return 2
  fi
  rao ship "$1" --all -m "$2"
}
