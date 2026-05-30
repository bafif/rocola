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

## ❌ Todavía NO verificado (requiere hardware físico)

- **Video 15 kHz (CRT arcade/TV)**: depende de GPU/driver físicos; **no** se valida en QEMU.
- **Controles de arcade**: el mapeo teclado/joystick está implementado (la UI responde en el render),
  pero no se probó con un encoder USB real.
- **Importar música desde 2º USB** y **biblioteca precargada**: lógica escrita, no probada en QEMU.
- **Hardware viejo real** (objetivo final: desktop antigua + CRT + arcade): requiere prueba física.

> Nota: el flujo **keep-music** (conservar `/music` al reinstalar) tiene la lógica revisada pero el
> camino E2E probado en QEMU fue una instalación **limpia** (sin partición previa que conservar).

## Próximos pasos sugeridos

1. Grabar el `.img` a un pendrive (`make flash`) y probar en una desktop vieja real (BIOS y, si hay, UEFI).
2. Probar en un CRT de 15 kHz real + encoder de arcade.
3. Validar el import de música desde un 2º USB y la reinstalación conservando `/music`.
