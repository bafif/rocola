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
4. Particionado destino:
     ┌──────────┬──────────────┬───────────────────────────┐
     │ ESP 256M │ ROOT (resto) │ DATOS /music (configurable)│
     │ FAT32    │ ext4         │ ext4 (persistente)         │
     └──────────┴──────────────┴───────────────────────────┘
5. Clonado               → unsquashfs/rsync del rootfs (squashfs) → ROOT
6. Tipo de monitor       → moderno/VGA | 15 kHz  → se persiste (ver doc 05)
7. Bootloader            → GRUB BIOS (MBR) + GRUB-EFI amd64 (ESP); genera /etc/fstab por UUID
8. Reboot                → la PC arranca la rocola desde el disco, sola
```

## Seguridad (anti-borrado)

- Selección **manual** del disco; nunca "el primero que encuentre".
- Resumen claro de la operación destructiva antes de tocar nada.
- Confirmación tipográfica (escribir una palabra), no solo "Enter".
- Detección y aviso si el destino es el **propio pendrive** de instalación (se excluye).

## Esquema de particiones y por qué

| Part | FS | Motivo |
|------|----|--------|
| ESP | FAT32 | requerido para arrancar por UEFI x64 |
| ROOT | ext4 | sistema; se **reescribe** en cada (re)instalación |
| `/music` | ext4 | datos del usuario; **persiste** entre reinstalaciones |

Separar `/music` permite **actualizar el SO sin perder la música**.

## Reinstalar / actualizar

Volver a correr el instalador sobre el mismo disco reescribe ROOT pero puede **preservar** la
partición `/music` (opción en la TUI). Ver [08 · Música](08-music-management.md).

Siguiente: [05 · Video VGA y 15 kHz](05-display-crt-15khz.md).
