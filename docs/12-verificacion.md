# 12 · Verificación (qué está probado y qué no)

Documento honesto sobre el estado real: qué se construyó y arrancó **de verdad**, y qué falta
validar (sobre todo en hardware físico). Construido y probado en un host x86-64 con Docker
(corre i386 nativo) + QEMU/KVM.

## ✅ Verificado de punta a punta

1. **Build del SO** (`make rootfs`): la imagen Docker `i386/debian:bookworm` se construye con todos
   los paquetes, el overlay, los symlinks de systemd y el initramfs con live-boot. ~478 MB (capa).
2. **Contenido del rootfs**: arquitectura **i386**; kernel `6.1.0-686-pae` + initrd; el initrd
   incluye `sr_mod`/`squashfs`/`overlay` (`MODULES=most`); servicios `mpd`, `rocola`,
   `rocola-display-setup` habilitados; usuario `rocola` con grupos correctos;
   `grub-install`/`update-grub`/`efibootmgr` presentes (para el instalador); la app importa
   (pygame 2.1.2 / SDL 2.26.5).
3. **Render de la UI** (headless, `SDL_VIDEODRIVER=dummy`): escenas **biblioteca**, **now-playing**
   y **menú** se dibujan con el branding (logo SVG + colores del tema). Ver
   [screenshots/ui-menu.png](screenshots/ui-menu.png), [ui-nowplaying.png](screenshots/ui-nowplaying.png).
4. **Imagen booteable** (`make image`): `grub-mkrescue` produce `out/rocola-i386.img`, una **ISO
   híbrida** con catálogo El Torito **doble** — entrada **BIOS** (GRUB i386-pc) + entrada **UEFI**
   (efi.img) — más MBR para `dd`. Verificado con `xorriso -report_el_torito`.
5. **Arranque real en QEMU (BIOS, KVM)** — el camino completo funciona:

   ```
   GRUB → kernel i386 → live-boot monta /live/filesystem.squashfs (overlay en RAM)
        → systemd (multi-user) → mpd.service → rocola.service
        → Xorg en tty1 → UI de la rocola a PANTALLA COMPLETA, con MPD conectado
   ```

   Captura del arranque real: **[screenshots/qemu-boot-ui.png](screenshots/qemu-boot-ui.png)**
   (muestra "Sin música. Importá canciones" = MPD conectado, biblioteca vacía porque este build
   de prueba no llevaba música).

### Reproducir

```bash
make rootfs && make image
file out/rocola-i386.img
docker run --rm -v "$PWD/out":/out rocola-builder \
  xorriso -indev /out/rocola-i386.img -report_el_torito plain      # lista BIOS y UEFI
qemu-system-i386 -enable-kvm -m 2048 -cdrom out/rocola-i386.img     # arranca a la UI
```

## ⚠️ Bugs encontrados y corregidos durante la verificación

Construir y arrancar "de verdad" destapó (y arregló) varios problemas reales:

| Problema | Síntoma | Arreglo |
|----------|---------|---------|
| Builder con loop devices | `make image` fallaba en WSL2 | pivote a **`grub-mkrescue`** (sin privilegios) |
| `grub-mkrescue` args | `-quiet`/`--volid=` rechazados por xorriso | `-- -volid ROCOLA` (sintaxis mkisofs) |
| rocola.service no arrancaba | tty1 quedaba en login de texto, no la UI | **mask `getty@tty1`** + servicio "reemplazo de getty" (sin `Conflicts`, que hacía a systemd descartarlo) |
| squashfs sin `/boot` | el sistema **instalado** quedaría sin kernel | incluir `/boot` en el squashfs |
| Xorg como no-root | `Cannot open virtual console` | `Xwrapper.config` (`needs_root_rights=yes`) |
| Instalador borraba `/music` | `--zap-all` destruía la partición a conservar | keep-mode no reparticiona, sólo reformatea ESP+ROOT |
| Faltaba `grub-install` | el instalador no podría poner GRUB | `grub2-common`+`efibootmgr`+`mtools` |
| `systemctl enable` en build | podía fallar sin systemd corriendo | symlinks `*.wants/` a mano |
| red intermitente | `apt` cortaba el build | `Acquire::Retries` + reintento de install |
| `make image` rebuildeaba todo | doble build del rootfs | guard `ensure-os` |

## ❌ Todavía NO verificado (requiere hardware o pasos manuales)

- **Arranque por UEFI x64**: el catálogo El Torito tiene la entrada UEFI, pero **no** se arrancó por
  UEFI en QEMU todavía. Pendiente: `qemu-system-x86_64 -bios OVMF.fd -cdrom out/rocola-i386.img`.
- **Instalador a disco** (`rocola-install`): lógica revisada y defensiva, pero **no** se ejecutó una
  instalación real (particionar + clonar + GRUB) en QEMU con 2º disco. Es destructivo: probar en VM
  antes que en hardware.
- **Video 15 kHz (CRT arcade/TV)**: depende de GPU/driver físicos; **no** se valida en QEMU.
- **Controles de arcade**: el mapeo teclado/joystick está implementado (la UI responde en el render),
  pero no se probó con un encoder USB real.
- **Importar música desde 2º USB** y **biblioteca precargada**: lógica escrita, no probada en QEMU.
- **Hardware viejo real** (objetivo final: desktop antigua + CRT + arcade): requiere prueba física.

## Próximos pasos sugeridos

1. Boot UEFI en QEMU con OVMF.
2. Instalación guiada en una VM con 2º disco vacío (validar particionado + reboot desde disco).
3. Grabar el `.img` a un pendrive (`make flash`) y probar en una desktop vieja real.
