# 11 · Resolución de problemas

## Build

**`make rootfs` falla con "exec format error" / no corre i386**
El host no puede ejecutar binarios i386. En CPUs x86-64 Docker suele correrlos nativo; si no, instalá
el emulador binfmt una sola vez:
```bash
docker run --privileged --rm tonistiigi/binfmt --install all
```

**`make rootfs` falla con `Failed to fetch ... Unable to connect to deb.debian.org`**
Blip de red al bajar paquetes. El Dockerfile ya reintenta (`Acquire::Retries` + reintento del
install con `--fix-missing`); volvé a correr `make rootfs` y normalmente completa.

**`make image` falla**
El armado usa `grub-mkrescue` (xorriso + mtools), **sin privilegios ni loop devices**. Si falla,
suele faltar `xorriso`/`mtools`/`grub-pc-bin`/`grub-efi-amd64-bin` en el builder (los trae
`image/Dockerfile.builder`). No necesita `--privileged` ni `/dev`.

**La imagen queda enorme**
Revisá música precargada en `os/rootfs-overlay/opt/rocola/music/` y limpiá cachés de apt en el
Dockerfile (`rm -rf /var/lib/apt/lists/*`).

## Arranque

**La PC no bootea del pendrive**
- Activá USB/Legacy boot en la BIOS; probá el menú de booteo (F12/F8/Esc).
- Regrabá el pendrive (ver [10](10-flashing-usb.md)); puede haber quedado a medias.
- Para UEFI muy viejo: usá modo BIOS/CSM.

**Arranca pero queda en consola, no abre la rocola**
```bash
journalctl -u rocola.service -b      # ver el error
journalctl -u rocola-display-setup.service -b
```
Suele ser video (ver abajo) o que Xorg no levantó.

## Video / CRT

**Pantalla negra o "fuera de rango" en CRT 15 kHz**
- El hardware puede no soportar 15 kHz por esa salida (ver [05](05-display-crt-15khz.md)). Probá la
  opción VGA/moderno.
- Forzá fallback VGA arrancando con el modo seguro (entrada de GRUB / `display.conf`).

**Imagen corrida/sin sincronizar en CRT**
Ajustá el modeline (posición/tamaño) en `display/modelines/`; cada CRT varía un poco.

**Monitor moderno se ve a baja resolución**
Verificá que `display.conf` no esté forzando 15 kHz; debería usar EDID.

## Audio

**No suena nada**
- `mpc status` para ver si MPD reproduce; `mpc outputs` para ver salidas.
- Revisá el mixer (`alsamixer`): puede estar en mute o volumen 0.
- En PCs viejas con varias salidas, fijá la tarjeta correcta en `mpd.conf`.

## Controles

**Los botones no responden / hacen otra cosa**
- Mirá si el encoder está en modo teclado o joystick; ambos deberían andar (ver [06](06-arcade-controls.md)).
- Usá la pantalla de test de input para ver qué manda cada botón y reasigná en la config.

## Música

**No aparecen las canciones importadas**
- Forzá re-scan: menú "Actualizar biblioteca" o `mpc update`.
- Verificá que se copiaron a `/music` y que los formatos los soporta MPD.

## Instalación

**El instalador no lista mi disco**
- Discos NVMe/RAID exóticos pueden necesitar módulos extra; reportar el modelo.
- El propio pendrive de instalación se excluye a propósito.

¿Algo no cubierto? Abrí un issue en el repo con la salida de `journalctl -b` y el modelo de hardware.
