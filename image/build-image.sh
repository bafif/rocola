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
# Usa grub-mkrescue (xorriso + mtools): todo en espacio de usuario, sin loop
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
# No excluir /boot: el instalador clona desde la raíz viva (este squashfs) al
# disco destino, así que el kernel+initrd deben estar dentro del squashfs para
# que el sistema instalado tenga con qué arrancar. (En /live van aparte sólo
# para el arranque live del pendrive.)
log "Creando filesystem.squashfs (puede tardar)…"
mksquashfs "$ROOTDIR" "$STAGE/live/filesystem.squashfs" \
    -comp xz -noappend

# --- 4) grub.cfg del medio LIVE -----------------------------------------------
log "Escribiendo grub.cfg…"
cat > "$STAGE/boot/grub/grub.cfg" <<'EOF'
set timeout=8
set default=0
# Solo los drivers de video del FIRMWARE (GOP/UGA en UEFI, VBE/VGA en BIOS): son los que
# dejan un framebuffer que el kernel hereda con 'gfxpayload=keep' (efifb/vesafb), que es
# lo que usa Xorg/fbdev en la entrada por defecto. 'all_video' sumaba los drivers
# 'bochs' y 'cirrus' de GRUB, que toman la placa de video emulada de QEMU y dejaban un
# framebuffer de 24 bpp, por BIOS y por UEFI, con el que X no arranca (ver abajo).
if [ "${grub_platform}" = "efi" ]; then
    insmod efi_gop
    insmod efi_uga
else
    insmod vbe
    insmod vga
fi
insmod gfxterm

# BIOS: GRUB arranca en modo TEXTO, y 'gfxpayload=keep' le pasaba ese modo texto al
# kernel: sin framebuffer (vesafb/simplefb) no hay /dev/fb0 y Xorg con fbdev muere con
# "no screens found" (visto en QEMU por BIOS). Pasamos GRUB a un modo gráfico VBE para
# que el kernel herede un framebuffer lineal. En UEFI el framebuffer (GOP/efifb) ya
# existe siempre, así que no se toca.
# La profundidad importa: el framebuffer del firmware no puede cambiar de modo, y Xorg
# 21 con fbdev no soporta 24 bpp ("Specified fbbpp (24) is not a permitted value").
# Muchas BIOS VBE ofrecen modos de 24 bpp, así que no dejamos que 'auto' elija: pedimos
# 32 bpp y, si la placa no los tiene, 16 bpp (rocola-display-setup le dice a Xorg qué
# profundidad usar). 800x600 primero: lo soporta cualquier monitor SVGA, CRT incluido;
# VBE no consulta al monitor, así que no conviene arrancar más alto.
if [ "${grub_platform}" = "pc" ]; then
    if loadfont unicode; then
        set gfxmode=800x600x32,1024x768x32,640x480x32,800x600x16,1024x768x16,640x480x16,auto
        terminal_output gfxterm
    fi
fi

# Entrada por defecto: video GENÉRICO (fbdev sobre el framebuffer del firmware,
# efifb/vesafb). 'nomodeset' evita el KMS de la GPU — necesario porque en i386 la
# aceleración de varias GPU modernas (p. ej. APUs AMD) está rota (rings SDMA), y
# fbdev anda en casi cualquier placa. gfxpayload=keep le pasa al kernel el
# framebuffer lineal que armó GRUB (sirve en BIOS y UEFI). loglevel=3 calla el
# spam de la consola (p. ej. "enp3s0: Link is Up/Down").
menuentry "Rocola" {
    set gfxpayload=keep
    linux  /live/vmlinuz boot=live components quiet loglevel=3 nomodeset
    initrd /live/initrd.img
}
# Aceleración por GPU (KMS). NECESARIA para CRT 15 kHz (modelines via modesetting).
# Usar sólo si tu GPU soporta KMS en i386; si la pantalla queda en negro o loopea,
# volvé a la entrada "Rocola" (fbdev).
menuentry "Rocola — aceleración GPU / CRT 15 kHz (KMS)" {
    linux  /live/vmlinuz boot=live components quiet loglevel=3
    initrd /live/initrd.img
}
menuentry "Rocola — recuperación (consola, sin UI)" {
    # Arranca a una consola de texto sin lanzar la UI (flag rocola.noui), para
    # depurar (journalctl, lspci, etc.). Autologin de rocola en tty1.
    set gfxpayload=keep
    linux  /live/vmlinuz boot=live components nomodeset rocola.noui
    initrd /live/initrd.img
}
menuentry "Rocola — troubleshooting (SSH por red)" {
    # Arranca la UI (fbdev) PERO además habilita sshd (root, solo clave) para
    # depurar por red. SSH se prende solo al elegir esta entrada (flag rocola.ssh);
    # el arranque normal nunca abre SSH. Requiere red con DHCP (systemd-networkd).
    set gfxpayload=keep
    linux  /live/vmlinuz boot=live components nomodeset rocola.ssh
    initrd /live/initrd.img
}
EOF

# --- 5) Ensamblar imagen híbrida BIOS+UEFI con grub-mkrescue ------------------
# El volid se pasa a xorriso/mkisofs después de '--' y con sintaxis mkisofs
# (-volid VALUE, separado por espacio; '--volid=' no es válido).
log "Generando imagen híbrida (grub-mkrescue)…"
grub-mkrescue --output="$OUT_IMG" "$STAGE" -- -volid ROCOLA

[ -s "$OUT_IMG" ] || { echo "ERROR: no se generó $OUT_IMG"; exit 1; }
log "Imagen lista: $OUT_IMG ($(du -h "$OUT_IMG" | cut -f1))"
log "Grabar con:  dd if=$OUT_IMG of=/dev/sdX bs=4M status=progress conv=fsync"
