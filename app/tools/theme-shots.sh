#!/bin/bash
# theme-shots.sh — capturas de cada pantalla en cada tipo de pantalla, para revisar un tema.
#
# Dibuja cada escena con ROCOLA_SCREENSHOT a la resolución típica de cada tipo de pantalla
# (crt15 320×240, crt 640×480, tv 720×576, lcd 1280×720) y deja los PNG en
# <salida>/<tema>/<tipo>-<escena>.png. La música es de mentira (tools/fake-mpd.py): la
# biblioteca con varios artistas (tarjetas de índice) y, en <tipo>-songs.png, con uno solo
# (tarjetas de canción).
#
# Uso: make theme-shots THEME=ambar      (o app/tools/theme-shots.sh <tema> [salida])
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
theme="${1:-ambar}"
out="$(realpath -m "${2:-out/shots}")/$theme"
mkdir -p "$out"

# Two pretend MPDs: many artists and a single one. Each writes its port and quits by itself
# 30 s after the last capture; the trap stops them earlier.
tmp="$(mktemp -d)"
pids=()
cleanup() {
    [ "${#pids[@]}" -eq 0 ] || kill "${pids[@]}" 2>/dev/null || true
    rm -rf "$tmp"
}
trap cleanup EXIT
for kind in many one; do
    (cd "$here/.." && exec uv run --quiet python tools/fake-mpd.py "$tmp/$kind" "$kind") &
    pids+=("$!")
done
for kind in many one; do
    for _ in $(seq 50); do [ -s "$tmp/$kind" ] && break; sleep 0.2; done
    [ -s "$tmp/$kind" ] || { echo "theme-shots: fake-mpd ($kind) did not start" >&2; exit 1; }
done
port_many="$(cat "$tmp/many")"
port_one="$(cat "$tmp/one")"

shot() { # <display> <res> <scene> <mpd port> <png>
    (cd "$here/.." && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
        ROCOLA_CONFIG=/nonexistent ROCOLA_THEME="$theme" ROCOLA_DISPLAY="$1" \
        ROCOLA_RES="$2" ROCOLA_WINDOWED=1 ROCOLA_SCREENSHOT_SCENE="$3" \
        ROCOLA_MPD_PORT="$4" ROCOLA_SCREENSHOT="$5" \
        uv run --quiet python -m rocola >/dev/null)
}

for spec in crt15:320x240 crt:640x480 tv:720x576 lcd:1280x720; do
    display="${spec%%:*}"
    res="${spec#*:}"
    for scene in library nowplaying menu audio info inputtest; do
        shot "$display" "$res" "$scene" "$port_many" "$out/$display-$scene.png"
    done
    shot "$display" "$res" library "$port_one" "$out/$display-songs.png"
done
echo "theme-shots: $out"
