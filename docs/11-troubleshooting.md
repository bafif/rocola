# 11 · Resolución de problemas

*[English](11-troubleshooting.en.md) · Español*

## Build

**`make rootfs` falla con "exec format error" / no corre i386**
El host no puede ejecutar binarios i386. En CPUs x86-64 suelen correr nativos; si no, registrá
binfmt una sola vez con el emulador de la distribución:
```bash
sudo pacman -S qemu-user-static qemu-user-static-binfmt   # Arch
sudo apt install qemu-user-static                         # Debian / Ubuntu
```

**`make rootfs` falla con `Failed to fetch ... Unable to connect to deb.debian.org`**
Blip de red al bajar paquetes. El Containerfile ya reintenta (`Acquire::Retries` + reintento del
install con `--fix-missing`); volvé a correr `make rootfs` y normalmente completa.

**`make image` falla**
El armado usa `grub-mkrescue` (xorriso + mtools), **sin privilegios ni loop devices**. Si falla,
suele faltar `xorriso`/`mtools`/`grub-pc-bin`/`grub-efi-amd64-bin` en el builder (los trae
`image/Containerfile.builder`). No necesita `--privileged` ni `/dev`.

**La imagen queda enorme**
Revisá música precargada en `os/rootfs-overlay/opt/rocola/music/` y limpiá cachés de apt en el
Containerfile (`rm -rf /var/lib/apt/lists/*`).

## Arranque

**La PC no bootea del pendrive**
- Activá USB/Legacy boot en la BIOS; probá el menú de booteo (F12/F8/Esc).
- Regrabá el pendrive (ver [10](10-flashing-usb.md)); puede haber quedado a medias.
- Para UEFI muy viejo: usá modo BIOS/CSM.
- Si se cuelga apenas arranca el kernel en una CPU muy vieja (algunos Pentium M, VIA C3, AMD
  Geode), probá la entrada «Rocola — CPU sin PAE · without PAE (kernel 686)».

**Arranca pero queda en consola, no abre la rocola**
La UI la lanza el autologin de tty1 (`~rocola/.bash_profile` → `startx` → `rocola-session`).
Para ver el error:
```bash
journalctl -u rocola-display-setup.service -b        # config de video
journalctl -b | grep -iE 'startx|xinit|Xorg|rocola-session'
```
Suele ser video (ver abajo) o que Xorg no levantó.

Si la UI se cae 5 veces en 2 minutos, el autologin deja de relanzarla y la consola muestra cómo
seguir. Para entrar a la consola a propósito: la entrada de GRUB «Rocola — consola de recuperación ·
recovery console», que está en el pendrive y en el disco instalado.
El usuario `rocola` está en el grupo `systemd-journal`, así que ahí `journalctl` muestra los logs
de todo el sistema sin root.

## SSH de troubleshooting (remoto)

Para depurar una rocola que no abre la UI, el ISO trae un SSH que está apagado por defecto. Solo
se habilita si arrancás con la entrada de GRUB **«Rocola — SSH por red · SSH troubleshooting»** (que pasa `rocola.ssh`
en la línea de comandos del kernel); en el arranque normal sshd no se levanta. Entra como root y
solo con clave pública, sin contraseñas, y las host keys se generan en RAM en cada arranque, así que
la imagen no lleva claves fijas.

El ISO oficial no confía en ninguna clave: `os/rootfs-overlay/root/.ssh/authorized_keys` está vacío
a propósito, y aunque alguien arranque con `rocola.ssh` no entra nadie. Este SSH es para tu propio
build.

**Habilitarlo en tu propio build:**
1. Pegá tu clave **pública** en `os/rootfs-overlay/root/.ssh/authorized_keys` (una línea, p. ej.
   `ssh-ed25519 AAAA... vos@tu-pc`). Nunca pongas la clave privada.
2. Reconstruí y regrabá: `make rootfs && make image`, luego `make flash DEV=/dev/sdX`.
3. Booteá la PC con la entrada de GRUB **«Rocola — SSH por red · SSH troubleshooting»**.
4. La rocola toma IP por DHCP (systemd-networkd). Averiguá la IP (en tu router, o con consola local
   `ip -4 addr`) y conectate:
   ```bash
   ssh -o StrictHostKeyChecking=accept-new root@<ip>
   ```

Config endurecida en `etc/ssh/sshd_config.d/10-rocola.conf`; el gate por cmdline lo hace el script
`rocola-ssh-maybe` (lo dispara `rocola-ssh.service` en cada arranque, pero sale de inmediato salvo
que esté `rocola.ssh`).

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
- `mpc status` para ver si MPD reproduce y `mpc outputs` para ver sus salidas.
- Revisá el mixer (`alsamixer`): puede estar en mute o con el volumen en 0.
- En PCs con varias salidas, elegí la correcta desde el menú («Salida de audio») o fijala en
  `/etc/rocola/audio.conf`. Los comandos para revisarlo por SSH están en [14](14-audio.md).

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
- Algunos discos NVMe o RAID poco comunes pueden necesitar módulos extra; si te pasa, abrí un issue
  con el modelo.
- El propio pendrive de instalación se excluye a propósito.

¿Algo no cubierto? Abrí un issue en el repo con la salida de `journalctl -b` y el modelo de hardware.
