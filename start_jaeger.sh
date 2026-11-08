#!/usr/bin/env bash
# KON Action Bridge - Jaeger UI Launcher for Mac
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAEGER_DIR="$DIR/.jaeger"
BIN="$JAEGER_DIR/jaeger-all-in-one"

if [ ! -f "$BIN" ]; then
  echo "Downloading Jaeger for macOS (Apple Silicon)..."
  mkdir -p "$JAEGER_DIR"
  curl -L -o "$JAEGER_DIR/jaeger.tar.gz" https://github.com/jaegertracing/jaeger/releases/download/v1.60.0/jaeger-1.60.0-darwin-arm64.tar.gz
  tar -xzf "$JAEGER_DIR/jaeger.tar.gz" -C "$JAEGER_DIR" --strip-components=1
  rm "$JAEGER_DIR/jaeger.tar.gz"
  chmod +x "$BIN"
fi

echo "=========================================================="
echo " Starting Jaeger OpenTelemetry UI for KON Action Bridge..."
echo " Web UI:     http://localhost:16686"
echo " OTLP HTTP:  http://localhost:4318"
echo "=========================================================="

# Check if already running
if lsof -Pi :16686 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Jaeger is already running on port 16686!"
  open http://localhost:16686 2>/dev/null || true
  exit 0
fi

# Open browser automatically after 1 second
(sleep 1 && open http://localhost:16686 2>/dev/null || true) &
exec "$BIN"
