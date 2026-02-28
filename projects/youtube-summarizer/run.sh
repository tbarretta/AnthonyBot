#!/usr/bin/env bash
# Wrapper to run summarize.py with the local venv
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/venv/bin/python3" "$DIR/summarize.py" "$@"
