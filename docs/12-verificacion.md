# 12 · Verificación (qué está probado y qué no)

*[English](12-verificacion.en.md) · Español*

Acá anoto qué construí y arranqué de punta a punta, qué problemas aparecieron en el camino y qué
falta probar, que es sobre todo lo que depende de hardware físico. Todo lo de este documento lo
armé y lo probé en una PC x86-64 con contenedores (que corren i386 nativo) y QEMU/KVM.

## Lo que anda de punta a punta

1. **Build del SO** (`make rootfs`). La imagen del SO (`FROM i386/debian:bookworm`) se construye con todos
   los paquetes, el overlay, los symlinks de systemd y el initramfs con live-boot. La capa pesa unos
   478 MB.
2. **Contenido del rootfs.** La arquitectura es i386, con el kernel `6.1.0-686-pae` y su initrd; el
   initrd incluye `sr_mod`, `squashfs` y `overlay` (`MODULES=most`). El usuario `rocola` tiene sus
   grupos, están `grub-install`, `update-grub` y `efibootmgr` (los necesita el instalador) y la app
   importa bien (pygame 2.1.2 con SDL 2.26.5). Los servicios que arrancan solos son
   `rocola-hostname`, `rocola-display-setup`, `rocola-selftest`, `rocola-music-import`, `rocola-ssh`
   (que sólo prende sshd con `rocola.ssh`), `systemd-networkd` y `bluetooth`. `mpd.service` y
   `mpd.socket` están enmascarados: a MPD lo lanza `rocola-session` dentro de la sesión de `rocola`
   (ver [14](14-audio.md)), y la UI arranca por el autologin de tty1, sin servicio propio. Así lo
   fija hoy `os/Containerfile`; en mayo `mpd` y `rocola` eran servicios del sistema, y el próximo
   build lo vuelve a comprobar en la imagen.
3. **Render de la UI** sin pantalla (`SDL_VIDEODRIVER=dummy`). Las escenas de biblioteca, now-playing
   y menú se dibujan con el branding (logo SVG y colores del tema). Se ven en
   [screenshots/ui-menu.png](screenshots/ui-menu.png) y [ui-nowplaying.png](screenshots/ui-nowplaying.png).
4. **Imagen booteable** (`make image`). `grub-mkrescue` produce `out/rocola-i386.img`, una ISO
   híbrida con catálogo El Torito doble (una entrada BIOS con GRUB i386-pc y una UEFI con `efi.img`)
   más un MBR para grabarla con `dd`. Lo comprobé con `xorriso -report_el_torito`.
5. **Arranque en QEMU por BIOS, con KVM.** El camino completo funciona:

   ```
   GRUB → kernel i386 → live-boot monta /live/filesystem.squashfs (overlay en RAM)
        → systemd (multi-user) → autologin de rocola en tty1 → startx
        → rocola-session (PipeWire, MPD) → Xorg en tty1 → UI de la rocola a pantalla
          completa, con MPD conectado
   ```

   La captura es [screenshots/qemu-boot-ui.png](screenshots/qemu-boot-ui.png). Muestra «Sin música.
   Importá canciones», o sea que MPD está conectado y la biblioteca está vacía porque ese build de
   prueba no llevaba música.

6. **Arranque en QEMU por UEFI x64, con OVMF.** La cadena de firmware completa también anda:

   ```
   OVMF (UEFI x64) → El Torito UEFI → GRUB EFI amd64 → kernel i386 → live-boot
        → systemd → mpd → Xorg → UI de la rocola a pantalla completa
   ```

   Esto confirma la decisión de fondo del proyecto: un GRUB de 64 bits carga sin problema el kernel
   i386. Por la consola serie se ve `BdsDxe … → Welcome to GRUB! → Booting 'Rocola'`. La captura es
   [screenshots/qemu-uefi-boot-ui.png](screenshots/qemu-uefi-boot-ui.png).

7. **Instalación a disco de punta a punta, en QEMU.** Es el flujo completo del aparato:

   ```
   live + 2º disco vacío → rocola-install (desatendido) → particiona GPT
        (BIOSBOOT+ESP+ROOT+MUSIC) → rsync del sistema vivo → GRUB BIOS+UEFI → fstab
   → se arranca el disco solo (sin pendrive) → la rocola abre sola, por BIOS y por UEFI
   ```

   La instalación termina con `SELFTEST_RESULT: OK`: particiona, clona, corre `grub-install` para
   i386-pc y x86_64-efi y `update-grub` detecta el kernel del destino. El disco instalado arrancando
   solo se ve en [screenshots/installed-bios-boot-ui.png](screenshots/installed-bios-boot-ui.png)
   (BIOS) y [screenshots/installed-uefi-boot-ui.png](screenshots/installed-uefi-boot-ui.png) (UEFI).

   Para automatizarlo, el instalador tiene un modo desatendido (`ROCOLA_UNATTENDED=1`) que dispara
   `rocola-selftest.service`; ese servicio solo actúa si el kernel arranca con `rocola.selftest` en
   la línea de comandos, así que en uso normal no hace nada. Los scripts de prueba están en
   `out/test/` (`installer-selftest.sh` y `boot-installed.sh`).

   También arranqué el disco instalado varias veces seguidas y todas llegaron a la rocola a pantalla
   completa. Esa prueba fue la que destapó la carrera de video que dejaba uno de cada tres arranques
   en la consola (está en la tabla de abajo). Desde que le saqué al initramfs la espera de resume, la
   UI aparece a los 55 a 65 segundos en QEMU/KVM, unos 30 segundos menos que antes.

### Cómo reproducirlo

```bash
make rootfs && make image
file out/rocola-i386.img
podman run --rm -i rocola-builder sh -c 'cat > /tmp/r.img && xorriso -indev /tmp/r.img -report_el_torito plain' \
  < out/rocola-i386.img                                            # lista BIOS y UEFI
# Arranque live a la UI (BIOS):
qemu-system-i386  -enable-kvm -m 2048 -cdrom out/rocola-i386.img
# Arranque live a la UI (UEFI x64):
qemu-system-x86_64 -enable-kvm -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/vars.fd -cdrom out/rocola-i386.img
# Instalador de punta a punta y arranque del disco instalado: out/test/installer-selftest.sh y boot-installed.sh
```

## Problemas que aparecieron al probar, y cómo los arreglé

Construir la imagen y arrancarla en serio sacó a la luz varios problemas reales. Los dejo anotados
porque más de uno puede volver a aparecer si se cambia el build o el instalador.

| Problema | Síntoma | Arreglo |
|----------|---------|---------|
| Builder con loop devices | `make image` fallaba en WSL2 | pasar a `grub-mkrescue`, que no pide privilegios |
| Argumentos de `grub-mkrescue` | xorriso rechazaba `-quiet` y `--volid=` | `-- -volid ROCOLA` (sintaxis de mkisofs) |
| rocola.service no arrancaba | tty1 quedaba en el login de texto, sin la UI | enmascarar `getty@tty1` y hacer del servicio un reemplazo de getty (sin `Conflicts`, que hacía que systemd lo descartara) |
| squashfs sin `/boot` | el sistema instalado se quedaba sin kernel | incluir `/boot` en el squashfs |
| Xorg sin root | `Cannot open virtual console` | `Xwrapper.config` con `needs_root_rights=yes` |
| El instalador borraba `/music` | `--zap-all` destruía la partición que había que conservar | al conservar la música no se reparticiona, solo se reformatean ESP y ROOT |
| Faltaba `grub-install` | el instalador no podía instalar GRUB | `grub2-common`, `efibootmgr` y `mtools` en la imagen |
| GPT sin BIOS Boot Partition | `grub-install i386-pc` fallaba («no BIOS Boot Partition») y la PC no iba a arrancar por BIOS | agregar una partición `ef02` de 2 MiB al esquema |
| El instalador daba por buena una instalación fallida | `{ … } \|\| die` desactiva `set -e`, así que los errores de grub, rsync o mkfs se perdían y terminaba en OK | `trap … ERR` y sacar el `\|\| die` del grupo |
| `grub-install` en un chroot sin `/dev` | rsync excluye `/dev`, `/proc` y `/sys`, los `mount --bind` fallaban y GRUB preguntaba «is /dev mounted?» | `grub-install` fuera del chroot con `--boot-directory`, y `mkdir -p` de los puntos de montaje para `update-grub` |
| Carrera de video: la rocola a veces arrancaba sin UI | `rocola-display-setup`, con `DefaultDependencies=no`, corría antes de que la raíz pasara a lectura y escritura; no podía escribir el `xorg.conf`, Xorg arrancaba sin configuración y quedaba la consola en vez de la rocola (uno de cada tres arranques del disco instalado) | sacar `DefaultDependencies=no`, ordenarlo `After=local-fs.target` y que el script tolere un `/etc` de solo lectura |
| rsync abortaba instalaciones válidas | clonar un sistema vivo devuelve 24 o 23 por archivos que cambian durante la copia, y con `set -e` y el trap se tomaba como error fatal | aceptar 24 y 23 como no fatales |
| El initramfs esperaba unos 30 s el resume | el initrd heredado del live buscaba en cada arranque instalado un dispositivo de suspensión que no existe | `RESUME=none` y `update-initramfs -u` en el chroot |
| Pantalla negra unos 30 s al arrancar | la app se bloqueaba en `_connect_mpd` (hasta 30 s) antes de dibujar nada | dibujar primero, conectar a MPD desde el loop y refrescar la biblioteca al conectar |
| El autotest arrastraba `udev-settle` | la unidad del selftest metía un servicio deprecado en cada arranque | sacar la dependencia y correr `udevadm settle` dentro del script, solo en el autotest |
| `systemctl enable` en el build | podía fallar sin systemd corriendo | los symlinks de `*.wants/` se crean a mano |
| Red intermitente | `apt` cortaba el build | `Acquire::Retries` y un reintento del install |
| `make image` reconstruía todo | el rootfs se armaba dos veces | el guard `ensure-os` |
| La entrada por defecto no mostraba la UI (QEMU, BIOS y UEFI) | `insmod all_video` cargaba el driver `bochs` de GRUB, que toma la VGA de QEMU y deja un framebuffer de 800×600 a 24 bpp; el framebuffer del firmware no cambia de modo y Xorg 21 con `fbdev` no acepta 24 bpp («Specified fbbpp (24) is not a permitted value»), así que X moría con «FBIOPUT_VSCREENINFO succeeded but modified mode» | GRUB carga solo los drivers de firmware (GOP/UGA, VBE/VGA); por BIOS pide primero modos de 32 bpp y después de 16 (hay BIOS VBE con modos de 24), y con 16 u 8 bpp `rocola-display-setup` le pone a Xorg el mismo `DefaultDepth` |
| Import desde USB | `TEMA01.MP3` o `Folder.jpg` no entraban (los filtros de rsync distinguen mayúsculas) y se copiaban todas las fotos y carpetas del pendrive | filtros que no distinguen mayúsculas, solo audio y `cover.*`/`folder.*`, y `--prune-empty-dirs` |
| El initrd tomaba el swap del host | `update-initramfs` en el build tomaba como dispositivo de resume el swap de la máquina que armaba la imagen | `RESUME=none` en el rootfs |
| El disco instalado arrancaba siempre con KMS | sin `/etc/default/grub`, `update-grub` armaba el disco sin `nomodeset` aunque el live hubiera arrancado con la entrada por defecto | el instalador escribe `/etc/default/grub.d/rocola-video.cfg` con el mismo video que el live (salvo con CRT de 15 kHz) |
| El pendrive de instalación aparecía como destino | con el medio montado como dispositivo entero, `LIVE_DISK` quedaba en `/dev/` | si no hay disco padre, el disco es el propio medio |
| Un disco chico daba un error críptico | ROOT ocupa 12 GiB fijos y con menos `sgdisk` fallaba a mitad de camino | mínimo de 14 GB, indicado en el menú y rechazado con un mensaje claro |
| Elegir una canción con la cola terminada | sonaba la primera de la cola y no la elegida (MPD queda sin canción actual y `play` arranca de la posición 0); en pausa, se reanudaba la anterior | `playid` de la canción elegida cuando no suena nada |
| Portadas del pendrive invisibles | `albumart` de MPD solo busca `cover.png`, `cover.jpg` o `cover.webp` escritos así, no `Folder.jpg` | el import agrega un `cover.<ext>` (enlace duro) en cada carpeta |

## Pruebas del 31/10/2026 (QEMU/KVM)

- Los tests de la app (`make app-test`, con pytest, SDL dummy y un MPD falso) pasan, y el CI corre
  además ruff y shellcheck.
- Import desde un segundo USB: con un pendrive FAT con dos WAV conectado al arrancar, la biblioteca
  muestra las dos canciones (lo dispara udev con `rocola-usb-music@.service`).
- La carrera de `console-getty`: si no se enmascara, el arranque puede caer en `rocola login:` en la
  consola en vez de abrir la UI. Me pasó en el primer arranque de esta prueba.
- La entrada por defecto («Rocola», con `nomodeset` y fbdev) por BIOS dejaba a GRUB en modo texto y
  el kernel arrancaba sin framebuffer, con lo que Xorg decía «no screens found». Ahora GRUB pasa a
  `gfxterm` en BIOS y el kernel tiene framebuffer. Después de eso fallaba en `ScreenInit` por la
  profundidad de color (los 24 bpp de la tabla de arriba), y lo mismo pasaba por UEFI. Ya está
  arreglado: la entrada por defecto abre la UI por BIOS (800×600 a 32 bpp por VBE, y probé también
  a 16 bpp) y por UEFI (GOP de OVMF, 1280×800 a 32 bpp) en QEMU/KVM, con la ISO armada desde lo
  commiteado. Falta probarlo en una PC real por BIOS.
- Import en caliente: con la rocola andando enchufé un pendrive FAT con `Album/TEMA01.MP3`,
  `Album/b.flac` y `DCIM/IMG_0001.JPG`. A los pocos segundos la biblioteca muestra las dos canciones,
  y en `/music` no está ni la foto ni `DCIM/`. Captura:
  [screenshots/qemu-bios-usb-import.png](screenshots/qemu-bios-usb-import.png).
- El instalador desde la entrada por defecto: la instalación desatendida a un disco de 16 GB termina
  con `SELFTEST_RESULT: OK`, el `grub.cfg` del disco lleva `nomodeset` y los modos de 32 y 16 bpp, y
  el disco arranca solo a la UI por BIOS y por UEFI. Un disco de 6 GB se rechaza con el mensaje del
  tamaño mínimo.
- Reinstalar conservando la música (`rocola.selftest.keep_music=yes`): hice una instalación limpia,
  el disco instalado importó dos canciones de un pendrive, reinstalé conservando los datos («conservando
  datos en /dev/sda4», `SELFTEST_RESULT: OK`) y el disco arrancó sin pendrive con las dos canciones
  todavía en la biblioteca.
- Biblioteca precargada: con dos archivos en `os/rootfs-overlay/opt/rocola/music/` antes de
  `make rootfs`, el live arranca y la biblioteca los muestra sin conectar nada.
- Mapeos desde `rocola.toml`: con `m = "menu"` en `[keys]` dentro de la imagen, la tecla `m` abre el
  menú.
- Probar controles: con F10 se entra a «Probar controles»; `n` y la barra espaciadora aparecen como
  `Tecla «n» -> next` y `Tecla «space» -> playpause`, y a los 15 segundos sin tocar nada vuelve sola
  al menú.

## Pruebas del 01/11/2026 (QEMU/KVM)

Usé la ISO armada desde lo commiteado, con la entrada por defecto por BIOS (800×600 a 32 bpp por
VBE) y un pendrive FAT conectado al arrancar. El pendrive tenía 10 WAV con tags ID3 en
`Artista/Álbum/` (una biblioteca de demostración inventada) y un `Folder.jpg` por álbum.

- Import con portadas: la biblioteca muestra «Todas las canciones» (10) y los tres artistas, y en
  `/music` cada álbum tiene su `cover.jpg` al lado del `Folder.jpg`.
- Navegación: Enter sobre un artista muestra «Todas de …» y sus dos álbumes (el de 1988 antes que el
  de 1991); Enter sobre un álbum muestra sus pistas numeradas.
- Reproducción: Enter sobre una pista abre «Reproduciendo» con la portada del álbum, el título, el
  artista, el álbum y `[play]`. Con Esc tres veces se vuelve por el álbum y el artista hasta la lista
  de artistas, con el mismo artista seleccionado.
- Elegir con la cola terminada, contra el MPD de la imagen (0.23.12): antes volvía a sonar la primera
  canción de la cola y ahora suena la elegida.

## Lo que falta probar en hardware

Todo lo anterior está probado en QEMU. Lo que sigue necesita una máquina real:

- El video a 15 kHz para un CRT de arcade o un televisor depende de la placa de video y del driver,
  y en QEMU no hay forma de comprobarlo.
- Los controles de arcade: el mapeo de teclado y joystick está hecho y la UI responde en el render,
  pero no lo probé con un encoder USB real.
- El import desde un segundo USB está probado en QEMU (al arrancar y en caliente); falta con un
  pendrive real.
- La biblioteca precargada está probada en QEMU en modo live; falta en hardware.
- Reinstalar conservando `/music` se probó en QEMU el 31/10/2026; falta en un disco real.
- Y lo más importante, que es el objetivo del proyecto: una desktop vieja con un CRT y controles de
  arcade.

El plan para eso es grabar el `.img` en un pendrive (`make flash`) y arrancarlo en una desktop vieja,
por BIOS y, si la máquina lo tiene, por UEFI. Después, conectarla a un CRT de 15 kHz con un encoder
de arcade, y en esa misma máquina importar música desde un segundo pendrive y reinstalar conservando
`/music`.
