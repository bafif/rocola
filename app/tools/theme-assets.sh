#!/bin/bash
# theme-assets.sh — pasa los SVG originales de cada tema a los PNG que usa la rocola.
#
# Cada app/assets/themes/<tema>/src/<ruta>.svg queda como <tema>/<ruta>.png, al tamaño del
# SVG (las piezas de 240p se dibujan aparte, en src/240p/). Corre en un contenedor de
# Podman con rsvg-convert: los SVG entran y los PNG salen por tar, sin montar el repo. Los
# PNG se commitean, así la imagen del sistema no suma librsvg.
#
# Uso: make theme-assets      (ROCOLA_THEMES_DIR cambia la carpeta de los temas)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
themes="${ROCOLA_THEMES_DIR:-$here/../assets/themes}"
image="${ROCOLA_SVG_IMAGE:-localhost/rocola-svg:bookworm}"

mapfile -t svgs < <(cd "$themes" && find . -path '*/src/*' -name '*.svg' | sort)
if [ "${#svgs[@]}" -eq 0 ]; then
    echo "theme-assets: no hay SVG en */src/ de $themes"
    exit 0
fi

if ! podman image exists "$image"; then
    podman build -t "$image" -f "$here/Containerfile.svg" "$here"
fi

(cd "$themes" && tar -cf - "${svgs[@]}") \
    | podman run --rm -i "$image" sh -c '
        set -e
        mkdir /w && cd /w && tar -xf -
        find . -path "*/src/*" -name "*.svg" | while read -r svg; do
            out=$(printf "%s" "$svg" | sed "s#/src/#/#; s#\.svg\$#.png#")
            mkdir -p "$(dirname "$out")"
            rsvg-convert -o "$out" "$svg"
        done
        find . -name "*.png" ! -path "*/src/*" | tar -cf - -T -
    ' \
    | (cd "$themes" && tar -xvf -)
