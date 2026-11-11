#!/bin/bash
# theme-shots.sh — capturas de cada pantalla en cada tipo de pantalla, para revisar un tema.
#
# Dibuja cada escena con ROCOLA_SCREENSHOT a la resolución típica de cada tipo de pantalla
# (crt15 320×240, crt 640×480, tv 720×576, lcd 1280×720) y deja los PNG en
# <salida>/<tema>/<tipo>-<escena>.png. Sin un MPD local, la biblioteca sale vacía.
#
# Uso: make theme-shots THEME=ambar      (o app/tools/theme-shots.sh <tema> [salida])
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
theme="${1:-ambar}"
out="$(realpath -m "${2:-out/shots}")/$theme"
mkdir -p "$out"

for spec in crt15:320x240 crt:640x480 tv:720x576 lcd:1280x720; do
    display="${spec%%:*}"
    res="${spec#*:}"
    for scene in library nowplaying menu audio info inputtest; do
        (cd "$here/.." && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
            ROCOLA_CONFIG=/nonexistent ROCOLA_THEME="$theme" ROCOLA_DISPLAY="$display" \
            ROCOLA_RES="$res" ROCOLA_WINDOWED=1 ROCOLA_SCREENSHOT_SCENE="$scene" \
            ROCOLA_SCREENSHOT="$out/$display-$scene.png" \
            uv run --quiet python -m rocola >/dev/null)
    done
done
echo "theme-shots: $out"
