#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -B run_desktop.py
else
  exec python3 -B run_desktop.py
fi
