#!/bin/bash
# package-release.sh — empaqueta la imagen booteable como artefacto de Release.
#
#   package-release.sh <imagen-fuente> <version> <dir-salida>
#
# La imagen que produce `make image` es, de hecho, una ISO 9660 híbrida (isohybrid):
# bootea por BIOS y por UEFI x64, y se puede grabar tal cual con `dd`, Rufus o copiar
# a un pendrive Ventoy. Para que Windows/Rufus/Ventoy la reconozcan sin dudar, este
# script la publica con extensión `.iso` y genera un checksum SHA-256 para verificarla.
#
# Salida en <dir-salida>:
#   rocola-i386-<version>.iso   (copia de la imagen, lista para subir al Release)
#   SHA256SUMS.txt              (suma SHA-256 para verificar la descarga)
set -euo pipefail

SRC="${1:?uso: package-release.sh <imagen-fuente> <version> <dir-salida>}"
VERSION="${2:?uso: package-release.sh <imagen-fuente> <version> <dir-salida>}"
OUT_DIR="${3:?uso: package-release.sh <imagen-fuente> <version> <dir-salida>}"

log() { echo -e "\033[36m[package-release]\033[0m $*"; }

[ -s "$SRC" ] || { echo "ERROR: no existe o está vacía la imagen fuente: $SRC" >&2; exit 1; }

ISO_NAME="rocola-i386-${VERSION}.iso"
mkdir -p "$OUT_DIR"

log "Copiando $SRC -> $OUT_DIR/$ISO_NAME"
cp --reflink=auto -f "$SRC" "$OUT_DIR/$ISO_NAME"

log "Generando SHA256SUMS.txt"
( cd "$OUT_DIR" && sha256sum "$ISO_NAME" > SHA256SUMS.txt )

log "Artefactos listos en $OUT_DIR:"
( cd "$OUT_DIR" && ls -lh "$ISO_NAME" SHA256SUMS.txt && echo && cat SHA256SUMS.txt )

cat <<EOF

Para publicar el Release (requiere 'gh' autenticado):

  gh release create ${VERSION} \\
    "${OUT_DIR}/${ISO_NAME}" \\
    "${OUT_DIR}/SHA256SUMS.txt" \\
    --title "Rocola ${VERSION}" --notes-file <(...)
EOF
