#!/bin/sh
# Start the editor on Linux or macOS (needs Python 3 with Tk: e.g. sudo apt install python3-tk).
cd "$(dirname "$0")" || exit 1
exec python3 smr_save_editor.py "$@"
