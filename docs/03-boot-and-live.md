# 03 · Boot y modo live

## Cadena de arranque

```
Firmware (BIOS o UEFI x64)
  └─ GRUB
      └─ kernel i386 (686-pae) + initrd con live-boot
          └─ monta filesystem.squashfs + overlay (tmpfs)   ← corre en RAM, no escribe el USB
              └─ systemd
                  ├─ rocola-display-setup.service   (driver y modo de video: VGA / 15 kHz)
                  └─ getty@tty1 con autologin de `rocola`
                      └─ ~/.bash_profile → startx → rocola-session
                          ├─ PipeWire + WirePlumber + MPD   (audio, en la sesión)
                          └─ app SDL2 a pantalla completa
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

- `getty@tty1` con **autologin** del usuario `rocola`.
- Su `~/.bash_profile` lanza `startx` con `rocola-session` como único cliente: **Xorg mínimo** y la
  **app SDL2 a pantalla completa**, sin window manager. Si X o la app terminan, el login se cierra,
  getty vuelve a entrar solo y la UI arranca de nuevo (kiosco).
- El audio vive en esa misma sesión: `rocola-session` levanta PipeWire, WirePlumber y **MPD** (MPD
  no es un servicio del sistema; `mpd.service` está enmascarado) y la app se conecta a MPD.

Archivos relevantes (en `os/rootfs-overlay/`):

```
etc/systemd/system/getty@tty1.service.d/autologin.conf
etc/systemd/system/rocola-display-setup.service
home/rocola/.bash_profile        (autologin → startx)
opt/rocola/                      (la app)
usr/local/bin/rocola-session     (audio + MPD + app, dentro de X)
```

`etc/systemd/system/rocola.service` es el mecanismo anterior (un servicio que tomaba tty1): queda
en el árbol pero no se habilita.

## BIOS y UEFI x64

- **BIOS**: GRUB-PC desde el MBR. Funciona en PCs de 32 y 64 bits.
- **UEFI x64**: GRUB-EFI amd64 desde la ESP, que carga el **kernel i386**. (UEFI de 32 bits puro no
  está soportado.)

## Recuperación / depuración

- Entrada de GRUB **«Rocola — recuperación (consola, sin UI)»**: pasa `rocola.noui`, el autologin
  queda en la consola de tty1 y no se lanza X.
- Entrada **«Rocola — troubleshooting (SSH por red)»**: la UI normal más `sshd` (ver
  [11](11-troubleshooting.md)).
- Para ver por qué no arrancó la UI: `journalctl -b | grep -iE 'startx|xinit|Xorg|rocola-session'`
  y `/var/log/Xorg.0.log`.

Siguiente: [04 · Instalador](04-installer.md).
