# 04 · Instalador guiado

*[English](04-installer.en.md) · Español*

Clona el SO del pendrive al disco interno. **Disparo manual** (no automático) y con confirmación
explícita: el sistema **nunca** formatea un disco solo.

## Cómo se dispara

Desde la rocola en vivo: menú (**F10** o el botón 3 de arcade) → **Instalar en disco** (la opción
solo aparece cuando la rocola corre desde el pendrive). La app no es root: le pide a systemd que
arranque `rocola-installer.service`, y una regla de polkit le deja al usuario `rocola` arrancar esa
unidad y ninguna otra. La unidad pasa a la consola tty8, corre `rocola-install` (fuente en
`installer/`, enlazado en `/usr/local/bin/`) como root y al terminar vuelve a la UI. Desde una
consola es lo mismo: `systemctl start rocola-installer`.

Lo primero que pregunta es el idioma (español o inglés). Arranca marcado el de la rocola (el
del menú «Idioma / Language», la entrada «Rocola — English» de GRUB o el locale) y el que elijas
queda como idioma de la rocola instalada.

Es una TUI con `whiptail` que se maneja con **teclado**: la confirmación se tipea, y un encoder de
arcade en modo joystick no manda teclas a una consola de texto. Instalar se hace una vez; alcanza
con enchufar un teclado para eso.

## Flujo

```
1. Idioma                → español | inglés; viene marcado el de la rocola, y el elegido se
                           guarda en el disco instalado (/etc/rocola/language.conf)
2. Detección de discos   → lista modelo + tamaño de cada /dev/sdX, /dev/nvmeX, etc.
                           (los de menos de 14 GB salen marcados como «muy chico»)
3. Selección             → se elige el disco de destino (mínimo 14 GB)
4. Confirmación          → muestra qué se va a borrar y pide escribir "BORRAR"
                           ("ERASE" si se eligió inglés)
5. Particionado destino (GPT):
     ┌─────────┬──────────┬──────────────┬───────────────────────────┐
     │ BIOSBOOT│ ESP 256M │ ROOT 12G     │ DATOS /music (resto)      │
     │ 2M ef02 │ FAT32    │ ext4         │ ext4 (persistente)        │
     └─────────┴──────────┴──────────────┴───────────────────────────┘
6. Clonado               → rsync del sistema vivo (/) → ROOT (excluye /proc,/sys,/dev,/music…)
                           La música precargada (y la importada en la sesión en vivo) va a
                           la partición /music, si no tiene música; no ocupa ROOT.
7. Tipo de monitor       → moderno/VGA | 15 kHz  → se persiste (ver doc 05)
8. Bootloader            → GRUB BIOS (i386-pc, embebido en BIOSBOOT) + GRUB-EFI amd64
                           (BOOTX64.EFI en la ESP, --removable); /etc/fstab por UUID.
                           Si el pendrive arrancó con la entrada por defecto (nomodeset)
                           y el monitor no es de 15 kHz, el disco arranca igual: mismo
                           video genérico (/etc/default/grub.d/rocola-video.cfg).
9. Reboot                → la PC arranca la rocola desde el disco, sola
```

## Seguridad (anti-borrado)

- Selección **manual** del disco; nunca "el primero que encuentre".
- Resumen claro de la operación destructiva antes de tocar nada.
- Confirmación tipográfica (escribir una palabra), no solo "Enter".
- Detección y aviso si el destino es el **propio pendrive** de instalación (se excluye).
- Corre solo desde el pendrive: en una rocola instalada la opción no aparece y el instalador se
  niega, porque el disco del propio sistema aparecería como destino.

## Esquema de particiones y por qué

| Part | Tipo | Motivo |
|------|------|--------|
| BIOSBOOT | `ef02` (2 MiB, sin FS) | **obligatoria para arrancar por BIOS desde GPT**: GRUB embebe ahí su `core.img` (en GPT no hay hueco post-MBR como en MBR). Sin ella, `grub-install --target=i386-pc` falla. |
| ESP | FAT32 (`ef00`) | requerido para arrancar por UEFI x64 (`/EFI/BOOT/BOOTX64.EFI`) |
| ROOT | ext4 | sistema; se **reescribe** en cada (re)instalación |
| `/music` | ext4 | la música; **persiste** entre reinstalaciones |

Con `/music` aparte se puede actualizar el SO sin perder la música. Y el esquema GPT con la BIOS
Boot Partition más la ESP hace que el mismo disco arranque por BIOS y por UEFI x64.

En QEMU probé la instalación desatendida completa (particionar, clonar, GRUB) y el disco que queda
arranca a la UI por BIOS y por UEFI; el detalle está en [12 · Verificación](12-verificacion.md).

## Reinstalar / actualizar

Volver a correr el instalador sobre el mismo disco reescribe ROOT pero puede **preservar** la
partición `/music` (opción en la TUI). Ver [08 · Música](08-music-management.md).

## Modo desatendido (test / CI)

Para validar el instalador sin intervención (QEMU/CI), `rocola-install` acepta variables de entorno
que reemplazan los prompts de la TUI:

```bash
ROCOLA_UNATTENDED=1 ROCOLA_TARGET=/dev/sdX \
  ROCOLA_KEEP_MUSIC=no ROCOLA_DISPLAY=auto  rocola-install
```

`ROCOLA_LANG=es` (o `en`) fija además el idioma de la rocola instalada; sin ella, queda el de su
locale.

En uso normal no se usa: el menú de la rocola siempre lanza el flujo interactivo con confirmación.
Lo usa el arnés de prueba (`rocola-selftest.service`, que solo se activa con `rocola.selftest` en
la línea de comandos del kernel); ver [12 · Verificación](12-verificacion.md).

Siguiente: [05 · Video VGA y 15 kHz](05-display-crt-15khz.md).
