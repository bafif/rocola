# 12 · Verificación (qué está probado y qué no)

*[English](12-verificacion.en.md) · Español*

Cómo se prueba la rocola y qué está probado hoy. Lo que todavía depende de hardware físico está al
final.

## Tests automáticos

```bash
make app-test      # la app con pytest, sin pantalla ni audio (driver dummy de SDL y un MPD falso)
make app-lint      # ruff
make os-test       # los scripts del SO que corren sin root (el import de música)
make theme-check   # contraste, letras con tilde y archivos de cada tema
```

Los tests de la app también revisan que cada texto de pantalla esté en los dos idiomas, que cada
documento tenga su par en el otro idioma y que no haya enlaces rotos. El CI
(`.github/workflows/ci.yml`) corre ruff, pytest, shellcheck sobre los scripts y el test del import en
cada push a `main` y en cada pull request. La imagen no se arma en el CI: es pesada y se arma a mano.

## Probar la imagen en QEMU

```bash
make rootfs && make image
file out/rocola-i386.img                          # ISO 9660 con sector de arranque
podman run --rm -i rocola-builder \
  sh -c 'cat > /tmp/r.img && xorriso -indev /tmp/r.img -report_el_torito plain' < out/rocola-i386.img
                                                  # una entrada BIOS y una UEFI
qemu-system-i386 -enable-kvm -m 2048 -cdrom out/rocola-i386.img          # por BIOS
qemu-system-x86_64 -enable-kvm -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/vars.fd -cdrom out/rocola-i386.img   # por UEFI x64
```

`/tmp/vars.fd` es una copia de `OVMF_VARS.fd`; las rutas de OVMF cambian según la distribución. Con
la entrada por defecto, la rocola llega a pantalla completa con MPD conectado; sin música, lo dice y
manda al menú para importar canciones.

## El instalador, sin intervención

`rocola-selftest.service` corre el instalador en modo desatendido cuando el kernel arranca con
`rocola.selftest`; en cualquier otro arranque sale sin hacer nada. Para probarlo:

1. Arrancá la ISO en QEMU con un segundo disco vacío de 14 GB o más.
2. En el menú de GRUB, editá la entrada (tecla `e`) y agregale a la línea `linux` `rocola.selftest` y
   `rocola.selftest.target=/dev/sdX` con el disco vacío (por defecto, `/dev/sdb`). Con
   `rocola.selftest.keep_music=yes` reinstala conservando `/music`.
3. La consola muestra la tabla de particiones, el final del log del instalador y
   `SELFTEST_RESULT: OK` (o `FAIL(<código>)`), y la máquina se apaga.
4. Arrancá solo con ese disco: la rocola abre sola, por BIOS y por UEFI.

## Qué está probado

En QEMU/KVM, con la ISO armada desde el repo:

- **Arranque en vivo** hasta la rocola a pantalla completa con MPD conectado, con la entrada por
  defecto: por BIOS (800×600 por VBE, con 32 y con 16 bits de color) y por UEFI x64 (GOP de OVMF,
  1280×800). Capturas: [BIOS](screenshots/qemu-boot-ui.png) y [UEFI](screenshots/qemu-uefi-boot-ui.png).
- **Instalación** a un disco vacío: particiona, clona, instala GRUB para BIOS y UEFI, y el disco
  arranca solo a la rocola por BIOS y por UEFI, varias veces seguidas
  ([BIOS](screenshots/installed-bios-boot-ui.png), [UEFI](screenshots/installed-uefi-boot-ui.png)).
  Un disco de menos de 14 GB se rechaza con un mensaje que lo dice.
- **Reinstalar conservando la música**: las canciones importadas en el disco siguen en la biblioteca.
- **Import desde un segundo pendrive**, enchufado al arrancar o con la rocola andando: entra el audio
  sin importar las mayúsculas (`TEMA01.MP3`) y con sus portadas (al lado de un `Folder.jpg` queda un
  `cover.jpg`), y quedan afuera las fotos y las carpetas sin audio
  ([captura](screenshots/qemu-bios-usb-import.png)).
- **Biblioteca precargada**: con archivos en `os/rootfs-overlay/opt/rocola/music/`, el sistema en vivo
  los muestra sin enchufar nada.
- **La app en la imagen**: la navegación por artista y álbum, «Reproduciendo» con la portada, elegir
  una canción con la cola terminada (suena la elegida), un mapeo de `[keys]` en `rocola.toml` y
  «Probar controles».

Las capturas de estas pruebas muestran la interfaz anterior al tema Ámbar.

## En hardware real

El sistema en vivo arranca en una PC real desde un pendrive con Ventoy. Falta probar:

- El video a 15 kHz en un monitor de arcade o un televisor: depende de la placa y del driver, y QEMU
  no lo puede comprobar.
- Un encoder de arcade USB real (el mapeo por teclado está probado en QEMU).
- El import desde un segundo pendrive, la biblioteca precargada y reinstalar conservando `/music`.
- Lo que el proyecto busca: una desktop vieja con un monitor de tubo y controles de arcade.

Siguiente: [13 · Grabar con Rufus](13-rufus-windows.md).
