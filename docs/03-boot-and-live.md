# 03 · Boot y modo live

*[English](03-boot-and-live.en.md) · Español*

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

Si la UI se cierra 5 veces en 2 minutos, el autologin deja de relanzarla: tty1 queda en la consola
con el motivo y la forma de reintentar, en vez de un bucle que tapa la pantalla.

## Menú de arranque

| Entrada de GRUB | Qué hace |
|-----------------|----------|
| «Rocola» (por defecto) | la rocola en el idioma del sistema (español), con el video genérico del firmware |
| «Rocola — English» | lo mismo, en inglés (`rocola.lang=en`) |
| «Rocola — GPU / CRT 15 kHz (KMS)» | carga el driver de la placa de video; hace falta para 15 kHz (ver [05](05-display-crt-15khz.md)) |
| «Rocola — consola de recuperación · recovery console» | `rocola.noui`: tty1 queda en la consola, sin X |
| «Rocola — SSH por red · SSH troubleshooting» | la UI más `sshd` (ver [11](11-troubleshooting.md)) |
| «Rocola — CPU sin PAE · without PAE (kernel 686)» | el kernel sin PAE, para algunos Pentium M, VIA C3 y AMD Geode |

Como el modo live no guarda nada entre arranques, en el pendrive el idioma se elige acá; después se
cambia en el menú de la app (**«Idioma / Language»**) y, al instalar, queda guardado en
`/etc/rocola/language.conf`.

En el disco instalado, «Rocola — consola de recuperación · recovery console» hace lo mismo que en el
pendrive y el kernel sin PAE queda en el submenú «Advanced options». Las «recovery mode» de Debian
están apagadas: piden la clave de root, y root está bloqueado.

## BIOS y UEFI x64

- **BIOS**: GRUB-PC desde el MBR. Funciona en PCs de 32 y 64 bits.
- **UEFI x64**: GRUB-EFI amd64 desde la ESP, que carga el **kernel i386**. (UEFI de 32 bits puro no
  está soportado.)

## Servicios

Arrancan solos `rocola-hostname` (escribe `/etc/hostname` y `/etc/hosts`), `rocola-display-setup`,
`rocola-music-import` (deja la música precargada en `/music`), `systemd-networkd` y `bluetooth`.
`rocola-ssh` y `rocola-selftest` también corren en cada arranque, pero salen enseguida salvo que la
línea del kernel tenga `rocola.ssh` o `rocola.selftest`. `mpd.service` y `mpd.socket` están
enmascarados: a MPD lo lanza `rocola-session`. `rocola-installer.service` lo arranca el menú y
`rocola-usb-music@.service`, udev al enchufar un pendrive.

## Depuración

Para ver por qué no arrancó la UI: `journalctl -b | grep -iE 'startx|xinit|Xorg|rocola-session'` y
`/var/log/Xorg.0.log`. `rocola` está en el grupo `systemd-journal`, así que desde la consola
`journalctl` muestra los logs de todo el sistema sin root. Más en [11](11-troubleshooting.md).

Siguiente: [04 · Instalador](04-installer.md).
