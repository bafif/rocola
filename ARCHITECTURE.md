# Arquitectura de Rocola

Este documento describe el diseño del sistema: cómo se construye la imagen, cómo arranca, cómo se
instala y cómo encajan los subsistemas. Para el detalle de cada parte, ver [`docs/`](docs/).

## 1. Objetivo y restricciones

Un **pendrive booteable** que convierte una PC de escritorio vieja en una **rocola** dedicada.

| Restricción | Decisión |
|-------------|----------|
| Hardware viejo (~2 GB RAM, 32-bit) | Debian **i386**, kernel `686-pae` (fallback `686` no-PAE) |
| Base del SO | **Imagen de contenedor `FROM i386/debian:bookworm`** (Podman; bookworm aún publica kernel/booteable i386; trixie lo discontinuó) |
| Arranque | **BIOS** (PCs 32 y 64-bit) **+ UEFI x64** (`grub-efi-amd64` carga kernel i386) |
| Monitores | **VGA 31 kHz + arcade/TV 15 kHz** vía `switchres` + modelines |
| Controles | Encoder USB **teclado y/o joystick**, autodetectado (SDL) |
| App | **UI propia SDL2** (Python + pygame-ce) sobre **MPD** |
| Instalación | **Live en el pendrive + disparo manual → instalador guiado** (nunca auto-formatea) |
| Música | **Precargada** + **import desde 2º USB** a partición de datos persistente |

## 2. Pipeline de build (contenedor → pendrive)

```
┌──────────────────────────────────────────────────────────────────────┐
│ os/Containerfile  (FROM i386/debian:bookworm)                          │
│   · paquetes mínimos (Xorg, MPD, SDL2/pygame-ce, switchres, GRUB…)     │
│   · rootfs-overlay/  (systemd units, autologin, mpd.conf, xorg, app)   │
└───────────────┬──────────────────────────────────────────────────────┘
                │  podman build  →  podman export
                ▼
        out/rootfs.tar
                │
                │  image/Containerfile.builder (mksquashfs + xorriso + grub-mkrescue)
                ▼  build-image.sh   (contenedor NORMAL, sin privilegios; entra y sale con podman cp)
        out/rocola-i386.img  (ISO híbrida / isohybrid)
          · El Torito BIOS (core GRUB i386-pc) + UEFI x64 (BOOTX64.EFI)
          · /live/{vmlinuz,initrd.img,filesystem.squashfs}  (live-boot, overlay en RAM)
                │  make flash  (dd / Etcher)
                ▼
        PENDRIVE booteable
```

Las dos decisiones que más pesan:
- **El SO es una imagen de contenedor.** Todo el userland, la configuración y la app están en `os/`.
  El kernel, `live-boot` y GRUB se instalan dentro de esa misma imagen para que el rootfs exportado
  alcance por sí solo.
- **El empaquetado a `.img`** (`mksquashfs` y `grub-mkrescue`) corre en un contenedor aparte, común y
  sin root: `grub-mkrescue` arma la ISO híbrida en espacio de usuario (xorriso y mtools), sin loop
  devices ni privilegios. El contenedor no monta el repo: el rootfs entra y la imagen sale con
  `podman cp`. Por eso el build anda en WSL2 y en el CI, y en el host no hace falta nada más que
  Podman. La instalación a disco (particionar, `grub-install`) la hace el instalador en el sistema ya
  arrancado, donde sí hay un `/dev/sdX` real.

Detalle: [docs/02-build-pipeline.md](docs/02-build-pipeline.md).

## 3. Arranque y modo "live"

```
Encendido + pendrive
   └─► GRUB (BIOS o UEFI x64)
         └─► kernel i386 + initrd (live-boot)
               └─► monta filesystem.squashfs con overlay en RAM/tmpfs  (no escribe el USB)
                     └─► systemd: rocola-display-setup (driver y modo VGA/15 kHz)
                           └─► autologin de `rocola` en tty1 → startx → rocola-session
                                 └─► PipeWire + MPD (en la sesión)  +  app SDL2 fullscreen
```

- **Live-boot, squashfs y overlay**: el sistema corre en RAM, así que casi no escribe en el
  pendrive ni lo gasta, y se puede probar todo antes de instalar.
- **Arranque directo, sin escritorio**: solo `Xorg` y la app a pantalla completa, que es lo que
  aguanta bien una máquina i386 con 2 GB.

Detalle: [docs/03-boot-and-live.md](docs/03-boot-and-live.md).

## 4. Instalador guiado (clonado al disco)

Disparo **manual** desde la rocola en vivo (menú → «Instalar en disco»; F10 o botón 3 de arcade):

```
rocola-install (whiptail, navegable con arcade)
  1. Detecta discos (modelo, tamaño)         → se elige el destino (mínimo 14 GB)
  2. Doble confirmación anti-borrado          (muestra qué se va a destruir)
  3. Particiona destino (GPT):
        BIOSBOOT (ef02, BIOS) · ESP (FAT32, UEFI) · ROOT (ext4) · DATOS /music (ext4, persistente)
  4. Clona el SO:  rsync del sistema vivo (/)  →  ROOT
  5. Pregunta tipo de monitor (moderno/VGA | 15 kHz) → persiste la elección
  6. Instala GRUB en el destino (BIOS + UEFI x64), genera fstab; mismo modo de video que el live
  7. Reboot → la PC arranca la rocola sola desde el disco
```

El instalador nunca formatea un disco sin que alguien lo haya elegido y confirmado.

Detalle: [docs/04-installer.md](docs/04-installer.md).

## 5. Subsistema de video (VGA + 15 kHz)

La idea es que los dos tipos de monitor de tubo anden sin configurar nada después de instalar:

- En monitores con un EDID que sirve (VGA o modernos) se usan los modos estándar.
- En un CRT de 15 kHz (arcade o TV, sin un EDID confiable) se fuerzan modelines de 15 kHz con
  `switchres`.
- El tipo de monitor se elige una sola vez, en el instalador, y queda guardado; de ahí en adelante
  cada arranque lo aplica solo.
- Los 15 kHz dependen de que la placa de video y el driver los acepten. Si no, el sistema vuelve a
  un modo VGA seguro.

Detalle: [docs/05-display-crt-15khz.md](docs/05-display-crt-15khz.md).

## 6. Controles de arcade

- Los encoders USB típicos (iPAC/Xin-Mo/zero-delay) se presentan como **teclado** y/o **joystick**.
- La app usa **SDL2** para leer ambos y **autodetecta** el dispositivo presente.
- Mapeo de acciones (arriba/abajo, seleccionar, atrás, volumen, etc.) con defaults en
  `app/rocola/input.py`, ajustables con `[keys]` y `[buttons]` en `rocola.toml`.

Detalle: [docs/06-arcade-controls.md](docs/06-arcade-controls.md).

## 7. La aplicación (UI + audio)

```
┌────────────────────────────┐        IPC (socket MPD)        ┌─────────────┐
│  app/rocola  (SDL2)         │  ───────────────────────────► │   MPD       │
│   · render fullscreen       │  play/pause/next/seek/queue    │  (motor de  │
│   · navegación + branding   │  ◄───────────────────────────  │   audio)    │
│   · input teclado/joystick  │        estado / biblioteca     └─────┬───────┘
└────────────────────────────┘                                      │
                                                            /music (biblioteca)
```

- **MPD** gestiona biblioteca, cola y reproducción (liviano, ideal i386).
- **La UI** es un cliente MPD: muestra portadas/listas, "now playing", y manda comandos.
- Renderiza a la resolución nativa del monitor (320×240/640×480 en CRT, o mayor en VGA/moderno).

Detalle: [docs/07-rocola-app.md](docs/07-rocola-app.md).

## 8. Datos y persistencia

| Partición | FS | Rol | Persiste reinstall |
|-----------|----|-----|--------------------|
| ESP | FAT32 | arranque UEFI | n/a |
| ROOT | ext4 | sistema (clon del SO) | se reescribe |
| DATOS `/music` | ext4 | la música | **sí** |

Reinstalar o actualizar el SO no borra la música.

Detalle: [docs/08-music-management.md](docs/08-music-management.md).

## 9. Estructura del repositorio

Ver [README.es.md](README.es.md#cómo-está-organizado). Cada carpeta de nivel superior mapea a un
subsistema de esta arquitectura y tiene su doc correspondiente en [`docs/`](docs/).
