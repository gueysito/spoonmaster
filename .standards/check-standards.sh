#!/bin/sh
# Read-only; never installs dependencies or changes the index/worktree.
exec python3 "$(dirname "$0")/standards.py" check "$@"
