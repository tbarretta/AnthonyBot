#!/bin/bash
# Wrapper for article summarizer — called by Anthony when a URL is sent via Telegram.
# Usage: tg_summarize.sh <url> [--audio]

set -e

URL="$1"
AUDIO="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")/../projects/article-summarizer" && pwd)"
ANTHROPIC_API_KEY=$(python3 -c "import json; c=json.load(open('/home/tbarr/.openclaw/openclaw.json')); print(c['env']['ANTHROPIC_API_KEY'])")

export ANTHROPIC_API_KEY

if [ "$AUDIO" = "--audio" ]; then
    "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/summarize.py" "$URL" --no-tts --save --save-audio
else
    "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/summarize.py" "$URL" --no-tts --save
fi
