#!/bin/bash
# build-image.sh — arma la imagen booteable de la rocola desde el rootfs exportado.
#
#   build-image.sh <rootfs.tar> <salida.img>
#
# Produce una imagen GPT híbrida:
#   p1 bios_grub  (GRUB core para BIOS)
#   p2 FAT32      (ESP + sistema live: kernel, initrd, filesystem.squashfs, GRUB)
#
# Requiere correr en un contenedor PRIVILEGIADO con /dev montado (usa losetup + grub-install).
# NOTA: validar en QEMU/hardware; el booteo real depende de la GPU/firmware destino.
set -euo pipefail

ROOTFS_TAR="${1:?uso: build-image.sh <rootfs.tar> <salida.img>}"
OUT_IMG="${2:?uso: build-image.sh <rootfs.tar> <salida.img>}"

log() { echo -e "\033[36m[build-image]\033[0m $*"; }

WORK="$(mktemp -d)"
ROOTDIR="$WORK/root"
LIVE="$WORK/live"          # contenido que irá a la partición FAT32
MNT="$WORK/mnt"
mkdir -p "$ROOTDIR" "$LIVE/live" "$LIVE/boot/grub" "$LIVE/EFI/BOOT" "$MNT"

cleanup() {
    mountpoint -q "$MNT" && umount "$MNT" || true
    [ -n "${LOOP:-}" ] && losetup -d "$LOOP" 2>/dev/null || true
    rm -rf "$WORK"
}
trap cleanup EXIT

# --- 1) Extraer rootfs --------------------------------------------------------
log "Extrayendo rootfs…"
tar -C "$ROOTDIR" -xf "$ROOTFS_TAR"

# --- 2) Kernel + initrd -------------------------------------------------------
log "Tomando kernel + initrd…"
KIMG="$(ls -1 "$ROOTDIR"/boot/vmlinuz-*  2>/dev/null | sort -V | tail -1 || true)"
IIMG="$(ls -1 "$ROOTDIR"/boot/initrd.img-* 2>/dev/null | sort -V | tail -1 || true)"
[ -n "$KIMG" ] && [ -n "$IIMG" ] || { echo "ERROR: no encuentro kernel/initrd en el rootfs"; exit 1; }
cp "$KIMG" "$LIVE/live/vmlinuz"
cp "$IIMG" "$LIVE/live/initrd.img"

# --- 3) squashfs del rootfs ---------------------------------------------------
log "Creando filesystem.squashfs (puede tardar)…"
mksquashfs "$ROOTDIR" "$LIVE/live/filesystem.squashfs" \
    -comp xz -noappend -e boot
# Aviso: FAT32 limita archivos a 4 GB. Si el squashfs supera 4 GB (mucha música
# precargada), usar una partición ext4 para 'live' en vez de FAT32.

# --- 4) grub.cfg --------------------------------------------------------------
log "Escribiendo grub.cfg…"
cat > "$LIVE/boot/grub/grub.cfg" <<'EOF'
set timeout=5
set default=0
insmod all_video
insmod gfxterm

menuentry "Rocola" {
    linux  /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}
menuentry "Rocola — modo seguro (VGA)" {
    linux  /live/vmlinuz boot=live components nomodeset vga=788
    initrd /live/initrd.img
}
EOF

# --- 5) Crear y particionar la imagen ----------------------------------------
SIZE_MB=$(( $(du -sm "$LIVE" | cut -f1) + 600 ))
log "Creando imagen de ${SIZE_MB} MiB…"
truncate -s "${SIZE_MB}M" "$OUT_IMG"

parted -s "$OUT_IMG" mklabel gpt
parted -s "$OUT_IMG" mkpart bios_grub 1MiB 3MiB
parted -s "$OUT_IMG" set 1 bios_grub on
parted -s "$OUT_IMG" mkpart ESP fat32 3MiB 100%
parted -s "$OUT_IMG" set 2 esp on

# --- 6) loop + formato --------------------------------------------------------
LOOP="$(losetup --show -fP "$OUT_IMG")"
log "Loop: $LOOP"
mkfs.vfat -F32 -n ROCOLA "${LOOP}p2" >/dev/null

# --- 7) Copiar contenido a la partición --------------------------------------
mount "${LOOP}p2" "$MNT"
cp -a "$LIVE"/. "$MNT"/

# --- 8) GRUB BIOS (i386-pc) ---------------------------------------------------
log "Instalando GRUB BIOS…"
grub-install --target=i386-pc \
    --boot-directory="$MNT/boot" \
    --modules="part_gpt fat normal linux" \
    "$LOOP"

# --- 9) GRUB UEFI x64 (removable) --------------------------------------------
log "Instalando GRUB UEFI x64…"
grub-install --target=x86_64-efi \
    --efi-directory="$MNT" \
    --boot-directory="$MNT/boot" \
    --removable --no-nvram \
    --modules="part_gpt fat normal linux"

sync
umount "$MNT"
losetup -d "$LOOP"; LOOP=""

log "Imagen lista: $OUT_IMG"
