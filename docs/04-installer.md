# 04 · Instalador guiado

Clona el SO del pendrive al disco interno. **Disparo manual** (no automático) y con confirmación
explícita: el sistema **nunca** formatea un disco solo.

## Cómo se dispara

Desde la rocola en vivo, mediante un **combo de arcade** o una entrada de menú (configurable). Lanza
`rocola-install` (en `os/rootfs-overlay/usr/local/bin/`), una TUI con `whiptail` navegable con los
controles de arcade/teclado.

## Flujo

```
1. Detección de discos   → lista modelo + tamaño de cada /dev/sdX, /dev/nvmeX, etc.
2. Selección             → el usuario elige el disco destino
3. Confirmación          → muestra QUÉ se va a borrar; pide confirmación explícita ("BORRAR")
4. Particionado destino (GPT):
     ┌─────────┬──────────┬──────────────┬───────────────────────────┐
     │ BIOSBOOT│ ESP 256M │ ROOT 12G     │ DATOS /music (resto)      │
     │ 2M ef02 │ FAT32    │ ext4         │ ext4 (persistente)        │
     └─────────┴──────────┴──────────────┴───────────────────────────┘
5. Clonado               → rsync del sistema vivo (/) → ROOT (excluye /proc,/sys,/dev,/music…)
6. Tipo de monitor       → moderno/VGA | 15 kHz  → se persiste (ver doc 05)
7. Bootloader            → GRUB BIOS (i386-pc, embebido en BIOSBOOT) + GRUB-EFI amd64
                           (BOOTX64.EFI en la ESP, --removable); /etc/fstab por UUID
8. Reboot                → la PC arranca la rocola desde el disco, sola
```

## Seguridad (anti-borrado)

- Selección **manual** del disco; nunca "el primero que encuentre".
- Resumen claro de la operación destructiva antes de tocar nada.
- Confirmación tipográfica (escribir una palabra), no solo "Enter".
- Detección y aviso si el destino es el **propio pendrive** de instalación (se excluye).

## Esquema de particiones y por qué

| Part | Tipo | Motivo |
|------|------|--------|
| BIOSBOOT | `ef02` (2 MiB, sin FS) | **obligatoria para arrancar por BIOS desde GPT**: GRUB embebe ahí su `core.img` (en GPT no hay hueco post-MBR como en MBR). Sin ella, `grub-install --target=i386-pc` falla. |
| ESP | FAT32 (`ef00`) | requerido para arrancar por UEFI x64 (`/EFI/BOOT/BOOTX64.EFI`) |
| ROOT | ext4 | sistema; se **reescribe** en cada (re)instalación |
| `/music` | ext4 | datos del usuario; **persiste** entre reinstalaciones |

Separar `/music` permite **actualizar el SO sin perder la música**. El layout GPT con BIOS Boot
Partition + ESP hace que el **mismo disco** arranque por BIOS y por UEFI x64.

> **Verificado en QEMU**: instalación desatendida completa (particionar → clonar → GRUB) y el disco
> resultante arrancando a la UI por **BIOS y por UEFI**. Ver [12 · Verificación](12-verificacion.md).

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

En producción **no** se usa: el menú de la rocola lanza siempre el flujo interactivo con confirmación.
El arnés de prueba (`rocola-selftest.service`, gatillado solo con `rocola.selftest` en el cmdline del
kernel) usa este modo; ver [12 · Verificación](12-verificacion.md).

Siguiente: [05 · Video VGA y 15 kHz](05-display-crt-15khz.md).
