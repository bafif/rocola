#!/bin/bash
# build-image.sh — arma la imagen booteable de la rocola desde el rootfs exportado.
#
#   build-image.sh <rootfs.tar> <salida.img>
#
# Produce una imagen HÍBRIDA (ISO El Torito + isohybrid) booteable por:
#   - BIOS  (core GRUB i386-pc embebido)
#   - UEFI x64 (imagen EFI El Torito + /EFI/BOOT/BOOTX64.EFI)
# Se graba con `dd` a un pendrive y bootea en ambos firmwares.
#
# Usa grub-mkrescue (xorriso + mtools): TODO en espacio de usuario, sin loop
# devices ni mount. Así funciona en WSL2, contenedores y CI donde losetup falla.
#
# El sistema arranca "live" (live-boot) montando /live/filesystem.squashfs con
# overlay en RAM. La instalación a disco la hace el instalador en el sistema ya
# booteado (ahí sí hay /dev/sdX real), no este script.
set -euo pipefail

ROOTFS_TAR="${1:?uso: build-image.sh <rootfs.tar> <salida.img>}"
OUT_IMG="${2:?uso: build-image.sh <rootfs.tar> <salida.img>}"

log() { echo -e "\033[36m[build-image]\033[0m $*"; }

WORK="$(mktemp -d)"
ROOTDIR="$WORK/root"
STAGE="$WORK/stage"
mkdir -p "$ROOTDIR" "$STAGE/live" "$STAGE/boot/grub"
trap 'rm -rf "$WORK"' EXIT

# --- 1) Extraer rootfs --------------------------------------------------------
log "Extrayendo rootfs…"
tar -C "$ROOTDIR" -xf "$ROOTFS_TAR"

# --- 2) Kernel + initrd para el arranque LIVE ---------------------------------
log "Tomando kernel + initrd…"
KIMG="$(ls -1 "$ROOTDIR"/boot/vmlinuz-*   2>/dev/null | sort -V | tail -1 || true)"
IIMG="$(ls -1 "$ROOTDIR"/boot/initrd.img-* 2>/dev/null | sort -V | tail -1 || true)"
[ -n "$KIMG" ] && [ -n "$IIMG" ] || { echo "ERROR: no encuentro kernel/initrd en el rootfs"; exit 1; }
cp "$KIMG" "$STAGE/live/vmlinuz"
cp "$IIMG" "$STAGE/live/initrd.img"

# --- 3) squashfs del rootfs ---------------------------------------------------
# NO excluir /boot: el instalador clona desde la raíz viva (este squashfs) al
# disco destino, así que el kernel+initrd deben estar DENTRO del squashfs para
# que el sistema instalado tenga con qué arrancar. (En /live van aparte sólo
# para el arranque live del pendrive.)
log "Creando filesystem.squashfs (puede tardar)…"
mksquashfs "$ROOTDIR" "$STAGE/live/filesystem.squashfs" \
    -comp xz -noappend

# --- 4) grub.cfg del medio LIVE -----------------------------------------------
log "Escribiendo grub.cfg…"
cat > "$STAGE/boot/grub/grub.cfg" <<'EOF'
set timeout=5
set default=0
insmod all_video
insmod gfxterm

menuentry "Rocola" {
    linux  /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}
menuentry "Rocola — modo seguro (VGA, sin KMS)" {
    linux  /live/vmlinuz boot=live components nomodeset vga=788
    initrd /live/initrd.img
}
EOF

# --- 5) Ensamblar imagen híbrida BIOS+UEFI con grub-mkrescue ------------------
# El volid se pasa a xorriso/mkisofs DESPUÉS de '--' y con sintaxis mkisofs
# (-volid VALUE, separado por espacio; '--volid=' no es válido).
log "Generando imagen híbrida (grub-mkrescue)…"
grub-mkrescue --output="$OUT_IMG" "$STAGE" -- -volid ROCOLA

[ -s "$OUT_IMG" ] || { echo "ERROR: no se generó $OUT_IMG"; exit 1; }
log "Imagen lista: $OUT_IMG ($(du -h "$OUT_IMG" | cut -f1))"
log "Grabar con:  dd if=$OUT_IMG of=/dev/sdX bs=4M status=progress conv=fsync"
