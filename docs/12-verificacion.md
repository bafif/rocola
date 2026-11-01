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

6. **Arranque real en QEMU (UEFI x64, OVMF)** — la cadena completa de firmware también funciona:

   ```
   OVMF (UEFI x64) → El Torito UEFI → GRUB EFI amd64 → kernel i386 → live-boot
        → systemd → mpd → Xorg → UI de la rocola a PANTALLA COMPLETA
   ```

   Confirma la decisión clave del proyecto: **un GRUB de 64 bits carga el kernel i386**. El serial
   muestra `BdsDxe … → Welcome to GRUB! → Booting 'Rocola'`. Captura:
   **[screenshots/qemu-uefi-boot-ui.png](screenshots/qemu-uefi-boot-ui.png)**.

7. **Instalador a disco de punta a punta (QEMU)** — flujo completo del appliance:

   ```
   live + 2º disco vacío → rocola-install (desatendido) → particiona GPT
        (BIOSBOOT+ESP+ROOT+MUSIC) → rsync del sistema vivo → GRUB BIOS+UEFI → fstab
   → se arranca el DISCO solo (sin pendrive) → la rocola abre sola, por BIOS y por UEFI
   ```

   - Instalación: `SELFTEST_RESULT: OK` (particionar + clonar + `grub-install` i386-pc y x86_64-efi
     + `update-grub` detectando el kernel del destino).
   - Disco instalado arrancando solo: **[screenshots/installed-bios-boot-ui.png](screenshots/installed-bios-boot-ui.png)**
     (BIOS) y **[screenshots/installed-uefi-boot-ui.png](screenshots/installed-uefi-boot-ui.png)** (UEFI).
   - Se automatiza con un modo **desatendido** del instalador (`ROCOLA_UNATTENDED=1`) disparado por
     `rocola-selftest.service`, que solo actúa si el kernel arranca con `rocola.selftest` en el
     cmdline (inerte en producción). Scripts en `out/test/` (`installer-selftest.sh`, `boot-installed.sh`).
   - **Fiabilidad de arranque**: probados múltiples arranques seguidos del disco instalado —**todos**
     llegan a la rocola a pantalla completa (esto destapó y corrigió la race de video que dejaba 1 de
     cada 3 arranques en consola; ver tabla de bugs). **Tiempo a la UI ≈ 55–65 s** en QEMU/KVM tras
     desactivar la espera de resume del initramfs (~30 s menos por arranque).

### Reproducir

```bash
make rootfs && make image
file out/rocola-i386.img
docker run --rm -v "$PWD/out":/out rocola-builder \
  xorriso -indev /out/rocola-i386.img -report_el_torito plain      # lista BIOS y UEFI
# Arranque live a la UI (BIOS):
qemu-system-i386  -enable-kvm -m 2048 -cdrom out/rocola-i386.img
# Arranque live a la UI (UEFI x64):
qemu-system-x86_64 -enable-kvm -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/vars.fd -cdrom out/rocola-i386.img
# Instalador E2E + arranque del disco instalado: ver out/test/installer-selftest.sh y boot-installed.sh
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
| **GPT sin BIOS Boot Partition** | `grub-install i386-pc` fallaba ("no BIOS Boot Partition"): la PC **no arrancaría por BIOS** | agregar partición `ef02` (2 MiB) al layout |
| **Instalador "mentía" éxito** | `{ … } \|\| die` **desactiva `set -e`**: fallos de grub/rsync/mkfs se tragaban y reportaba OK | `trap … ERR` + sacar el `\|\| die` del grupo |
| **`grub-install` en chroot sin `/dev`** | rsync excluye `/dev,/proc,/sys` → los `mount --bind` fallaban → "is /dev mounted?" | `grub-install` fuera del chroot con `--boot-directory`; `mkdir -p` de los puntos de montaje para `update-grub` |
| **Race de video → rocola sin UI (intermitente)** | `rocola-display-setup` con `DefaultDependencies=no` corría **antes** del remount-rw → escribir el xorg.conf fallaba ("read-only") → Xorg sin config → **consola en vez de la rocola** (~1 de cada 3 arranques **instalados**) | sacar `DefaultDependencies=no`, ordenar `After=local-fs.target`; script tolerante a `/etc` ro |
| **rsync aborta install válido** | clonar un sistema VIVO devuelve 24/23 (archivos volátiles) y `set -e` + trap lo tomaba como fatal | aceptar 24/23 como no-fatales |
| **initramfs espera resume ~30s** | el initrd heredado del live esperaba un dispositivo de suspend/resume inexistente en CADA arranque instalado | `RESUME=none` + `update-initramfs -u` en el chroot |
| **Arranque en NEGRO ~30s** | la app bloqueaba en `_connect_mpd` (hasta 30s) **antes** del primer `draw` | dibujar primero y conectar MPD en el loop; refrescar biblioteca al conectar |
| autotest arrastraba `udev-settle` | la unidad de selftest metía un servicio deprecado en cada arranque | quitar el dep; `udevadm settle` dentro del script sólo en autotest |
| `systemctl enable` en build | podía fallar sin systemd corriendo | symlinks `*.wants/` a mano |
| red intermitente | `apt` cortaba el build | `Acquire::Retries` + reintento de install |
| `make image` rebuildeaba todo | doble build del rootfs | guard `ensure-os` |
| **Entrada por defecto sin UI (QEMU, BIOS y UEFI)** | `insmod all_video` cargaba el driver `bochs` de GRUB, que toma la VGA de QEMU y dejaba un framebuffer de 800×600×**24 bpp**; el del firmware no cambia de modo y Xorg 21 con `fbdev` no acepta 24 bpp («Specified fbbpp (24) is not a permitted value») → X moría con «FBIOPUT_VSCREENINFO succeeded but modified mode» | GRUB carga solo los drivers de firmware (GOP/UGA, VBE/VGA); por BIOS pide modos de 32 bpp y después de 16 bpp (hay BIOS VBE con modos de 24); con 16/8 bpp `rocola-display-setup` le pone a Xorg `DefaultDepth` igual |
| **Import desde USB** | `TEMA01.MP3` o `Folder.jpg` no entraban (los filtros de rsync distinguen mayúsculas); se copiaban todas las fotos y todas las carpetas del pendrive | filtros sin mayúsculas, solo audio y `cover.*`/`folder.*`, `--prune-empty-dirs` |
| initrd con el swap del host | `update-initramfs` en el build tomaba el swap de la máquina que armaba la imagen como dispositivo de resume | `RESUME=none` en el rootfs |
| Disco instalado siempre con KMS | sin `/etc/default/grub`, `update-grub` armaba el disco sin `nomodeset` aunque el live hubiera arrancado con la entrada por defecto | el instalador escribe `/etc/default/grub.d/rocola-video.cfg` con el mismo video que el live (salvo CRT 15 kHz) |
| El pendrive de instalación aparecía como destino | con el medio montado como dispositivo entero, `LIVE_DISK` quedaba en `/dev/` | si no hay disco padre, el disco es el propio medio |
| Disco chico → error críptico | ROOT es de 12 GiB fijos; con menos, `sgdisk` fallaba a mitad de camino | mínimo 14 GB, marcado en el menú y rechazado con un mensaje claro |

## Verificación del 31/10/2026 (QEMU/KVM)

- **Tests de la app**: `make app-test` (pytest, SDL dummy + MPD falso) y CI con ruff y shellcheck.
- **Import desde un 2º USB**: con un pendrive FAT con dos WAV conectado al arrancar, la biblioteca de
  la UI muestra las dos canciones (`rocola-usb-music@.service`, disparado por udev).
- **Carrera de `console-getty`**: sin enmascararlo, el arranque puede caer a `rocola login:` en la
  consola en vez de abrir la UI (pasó en el primer arranque de la prueba).
- **Entrada por defecto («Rocola», `nomodeset` + fbdev) por BIOS**: GRUB quedaba en modo texto y el
  kernel arrancaba sin framebuffer → Xorg «no screens found». Ahora GRUB pasa a `gfxterm` en BIOS y el
  kernel tiene framebuffer. Después fallaba en `ScreenInit` por la profundidad (24 bpp, ver la tabla
  de bugs), y lo mismo pasaba por UEFI. Arreglado: **la entrada por defecto abre la UI por BIOS
  (800×600×32 por VBE; también probado 800×600×16) y por UEFI (GOP de OVMF, 1280×800×32)** en
  QEMU/KVM, con la ISO armada desde lo commiteado. Falta una PC real por BIOS.
- **Import en caliente**: con la rocola andando se enchufa un pendrive FAT con `Album/TEMA01.MP3`,
  `Album/b.flac` y `DCIM/IMG_0001.JPG`; a los segundos la biblioteca muestra las dos canciones y en
  `/music` no hay ni la foto ni `DCIM/`. Captura:
  **[screenshots/qemu-bios-usb-import.png](screenshots/qemu-bios-usb-import.png)**.
- **Instalador desde la entrada por defecto**: instalación desatendida a un disco de 16 GB
  (`SELFTEST_RESULT: OK`); el `grub.cfg` del disco lleva `nomodeset` y los modos de 32/16 bpp, y el
  disco solo arranca a la UI por BIOS y por UEFI. Un disco de 6 GB se rechaza con el mensaje de
  tamaño mínimo.
- **Reinstalar conservando la música** (`rocola.selftest.keep_music=yes`): instalación limpia → el
  disco instalado importa dos canciones de un pendrive → reinstalación con keep-music («conservando
  datos en /dev/sda4», `SELFTEST_RESULT: OK`) → el disco arranca sin pendrive y la biblioteca sigue
  mostrando las dos canciones.

## ❌ Todavía NO verificado (requiere hardware físico)

- **Video 15 kHz (CRT arcade/TV)**: depende de GPU/driver físicos; **no** se valida en QEMU.
- **Controles de arcade**: el mapeo teclado/joystick está implementado (la UI responde en el render),
  pero no se probó con un encoder USB real.
- **Importar música desde 2º USB**: probado en QEMU (al arrancar y en caliente), falta un pendrive real.
- **Biblioteca precargada**: lógica escrita, no probada.
- **Hardware viejo real** (objetivo final: desktop antigua + CRT + arcade): requiere prueba física.

> El flujo **keep-music** (conservar `/music` al reinstalar) se probó en QEMU el 31/10/2026 (ver
> arriba); falta en un disco real.

## Próximos pasos sugeridos

1. Grabar el `.img` a un pendrive (`make flash`) y probar en una desktop vieja real (BIOS y, si hay, UEFI).
2. Probar en un CRT de 15 kHz real + encoder de arcade.
3. Validar en hardware real el import desde un 2º USB y la reinstalación conservando `/music`.
