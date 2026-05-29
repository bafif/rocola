# 03 · Boot y modo live

## Cadena de arranque

```
Firmware (BIOS o UEFI x64)
  └─ GRUB
      └─ kernel i386 (686-pae) + initrd con live-boot
          └─ monta filesystem.squashfs + overlay (tmpfs)   ← corre en RAM, no escribe el USB
              └─ systemd
                  ├─ autologin del usuario `rocola` (getty)
                  ├─ rocola-display-setup.service   (modo VGA / 15 kHz)
                  └─ rocola.service                 (Xorg + app)  →  mpd.service
```

## live-boot + squashfs + overlay

El sistema de archivos raíz es de **solo lectura** (`filesystem.squashfs`); `live-boot` le monta un
**overlay** en RAM. Ventajas:

- **No desgasta el pendrive** (las escrituras van a tmpfs).
- Permite **probar la rocola antes de instalar**.
- Arranque consistente: cada boot parte del mismo estado.

Como contrapartida, **los cambios en vivo no persisten** (es a propósito). La persistencia real llega
al **instalar** en disco, donde el root es read-write y `/music` es una partición aparte.

## Autologin + autostart (sin escritorio)

No hay entorno de escritorio. Para que sea liviano en i386/2 GB:

- `getty` con **autologin** del usuario `rocola` en un VT.
- El perfil de login dispara `rocola.service`, que lanza **Xorg mínimo** y, como única "sesión", la
  **app SDL2 a pantalla completa**. Sin window manager pesado.
- `mpd.service` corre como demonio de sistema/usuario y la app lo controla.

Archivos relevantes (en `os/rootfs-overlay/`):

```
etc/systemd/system/getty@tty1.service.d/autologin.conf
etc/systemd/system/rocola.service
etc/systemd/system/rocola-display-setup.service
etc/systemd/system/mpd.service.d/override.conf
opt/rocola/                      (la app)
usr/local/bin/rocola-session     (arranca Xorg + app)
```

## BIOS y UEFI x64

- **BIOS**: GRUB-PC desde el MBR. Funciona en PCs de 32 y 64 bits.
- **UEFI x64**: GRUB-EFI amd64 desde la ESP, que carga el **kernel i386**. (UEFI de 32 bits puro no
  está soportado.)

## Recuperación / depuración

- Agregar `rocola.debug` a la cmdline de GRUB para caer a una consola en vez de la app (planeado).
- `journalctl -u rocola.service` para ver por qué no arrancó la UI.

Siguiente: [04 · Instalador](04-installer.md).
