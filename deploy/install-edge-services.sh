#!/usr/bin/env bash
# Install Pli's edge AI services (LLM · agent · voice) as systemd user services and check that each answers.
# Prerequisites (docs/manual/INSTALL.md §3): .tools/edge-venv, .tools/tts-gpu-venv, llama.cpp and the models under .tools/edge-ai.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNITS=(pli-edge-llm pli-edge-ai pli-edge-voice)

missing=0
for need in .tools/edge-venv/bin/python .tools/tts-gpu-venv/bin/python .tools/edge-ai/bin/llama-b12314/llama-server \
            .tools/edge-ai/models/kanana-1.5-2.1b .tools/edge-ai/models/asr .tools/edge-ai/models/face; do
  if [ ! -e "$ROOT/$need" ]; then echo "missing: $need"; missing=1; fi
done
[ "$missing" -eq 0 ] || { echo "Prepare the items above first (docs/manual/INSTALL.md §3)."; exit 1; }

mkdir -p "$DEST"
for unit in "${UNITS[@]}"; do
  sed "s|@PLI_ROOT@|$ROOT|g" "$ROOT/deploy/systemd/$unit.service" > "$DEST/$unit.service"
  echo "installed $DEST/$unit.service"
done
systemctl --user daemon-reload
systemctl --user enable --now "${UNITS[@]/%/.service}"

check() {  # name url
  for _ in $(seq 1 90); do
    if curl -sf -m 3 "$2" >/dev/null; then echo "ok    $1  $2"; return 0; fi
    sleep 2
  done
  echo "FAIL  $1  $2 (journalctl --user -u $1)"; return 1
}
check pli-edge-llm   http://127.0.0.1:8891/health
check pli-edge-ai    http://127.0.0.1:8890/v1/health
check pli-edge-voice http://127.0.0.1:8892/v1/voice/health
