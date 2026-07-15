#!/bin/sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$SCRIPT_DIR/src/input.css"
OUTPUT="$SCRIPT_DIR/static/css/output.css"

if [ ! -f "$INPUT" ]; then
  echo "Error: $INPUT not found" >&2
  exit 1
fi

if ! command -v tailwindcss >/dev/null 2>&1; then
  echo "Error: tailwindcss CLI not found in PATH" >&2
  exit 1
fi

case "${1:-build}" in
  watch)
    echo "Watching for changes..."
    tailwindcss -i "$INPUT" -o "$OUTPUT" --watch
    ;;
  build)
    echo "Building Tailwind CSS..."
    tailwindcss -i "$INPUT" -o "$OUTPUT" --minify
    echo "Done: $OUTPUT"
    ;;
  *)
    echo "Usage: $0 {build|watch}" >&2
    exit 1
    ;;
esac
