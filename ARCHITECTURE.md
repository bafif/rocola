# Arquitectura de Rocola

Este documento describe el diseño del sistema: cómo se construye la imagen, cómo arranca, cómo se
instala y cómo encajan los subsistemas. Para el detalle de cada parte, ver [`docs/`](docs/).

## 1. Objetivo y restricciones

Un **pendrive booteable** que convierte una PC de escritorio vieja en una **rocola** dedicada.

| Restricción | Decisión |
|-------------|----------|
| Hardware viejo (~2 GB RAM, 32-bit) | Debian **i386**, kernel `686-pae` (fallback `686` no-PAE) |
| Base del SO | **Docker `FROM i386/debian:bookworm`** (bookworm aún publica kernel/booteable i386; trixie lo discontinuó) |
| Arranque | **BIOS** (PCs 32 y 64-bit) **+ UEFI x64** (`grub-efi-amd64` carga kernel i386) |
| Monitores | **VGA 31 kHz + arcade/TV 15 kHz** vía `switchres` + modelines |
| Controles | Encoder USB **teclado y/o joystick**, autodetectado (SDL) |
| App | **UI propia SDL2** (Python + pygame-ce) sobre **MPD** |
| Instalación | **Live en el pendrive + disparo manual → instalador guiado** (nunca auto-formatea) |
| Música | **Precargada** + **import desde 2º USB** a partición de datos persistente |

## 2. Pipeline de build (Docker → pendrive)

```
┌──────────────────────────────────────────────────────────────────────┐
│ os/Dockerfile  (FROM i386/debian:bookworm)                             │
│   · paquetes mínimos (Xorg, MPD, SDL2/pygame-ce, switchres, GRUB…)     │
│   · rootfs-overlay/  (systemd units, autologin, mpd.conf, xorg, app)   │
└───────────────┬──────────────────────────────────────────────────────┘
                │  docker build  →  docker export
                ▼
        out/rootfs.tar
                │
                │  image/Dockerfile.builder (mksquashfs + xorriso + grub-mkrescue)
                ▼  build-image.sh   (docker run NORMAL, sin privilegios)
        out/rocola-i386.img  (ISO híbrida / isohybrid)
          · El Torito BIOS (core GRUB i386-pc) + UEFI x64 (BOOTX64.EFI)
          · /live/{vmlinuz,initrd.img,filesystem.squashfs}  (live-boot, overlay en RAM)
                │  make flash  (dd / Etcher)
                ▼
        PENDRIVE booteable
```

Decisiones clave:
- **El SO se define como una imagen Docker** (fiel a la consigna): todo el userland, configs y la
  app viven en `os/`. El kernel, `live-boot` y GRUB se instalan dentro de esa imagen para que el
  rootfs exportado sea autosuficiente.
- **El empaquetado a `.img`** (`mksquashfs` + `grub-mkrescue`) corre en un contenedor builder con un
  `docker run` **normal**: `grub-mkrescue` arma la ISO híbrida en espacio de usuario (xorriso +
  mtools), **sin loop devices ni privilegios**. Así el build funciona en WSL2/CI y no hace falta
  tooling especial en el host (solo Docker). La instalación a disco (particionar/`grub-install`) la
  hace el instalador en el sistema ya booteado, donde sí hay `/dev/sdX` real.

Detalle: [docs/02-build-pipeline.md](docs/02-build-pipeline.md).

## 3. Arranque y modo "live"

```
Encendido + pendrive
   └─► GRUB (BIOS o UEFI x64)
         └─► kernel i386 + initrd (live-boot)
               └─► monta filesystem.squashfs con overlay en RAM/tmpfs  (no escribe el USB)
                     └─► systemd: autologin del usuario `rocola` en un VT
                           └─► rocola-display-setup  (elige modo VGA/15 kHz)
                                 └─► Xorg mínimo  →  app SDL2 fullscreen
                                       └─► MPD (servicio) reproduce; la UI lo controla
```

- **Live-boot + squashfs + overlay**: el sistema corre en RAM, minimizando escrituras y desgaste
  del pendrive, y permite "probar antes de instalar".
- **Autostart** sin escritorio: solo `Xorg` + la app a pantalla completa (liviano para 2 GB i386).

Detalle: [docs/03-boot-and-live.md](docs/03-boot-and-live.md).

## 4. Instalador guiado (clonado al disco)

Disparo **manual** desde la rocola en vivo (combo de arcade / entrada de menú):

```
rocola-install (whiptail, navegable con arcade)
  1. Detecta discos (modelo, tamaño)         → el usuario elige el destino
  2. Doble confirmación anti-borrado          (muestra qué se va a destruir)
  3. Particiona destino (GPT):
        BIOSBOOT (ef02, BIOS) · ESP (FAT32, UEFI) · ROOT (ext4) · DATOS /music (ext4, persistente)
  4. Clona el SO:  rsync del sistema vivo (/)  →  ROOT
  5. Pregunta tipo de monitor (moderno/VGA | 15 kHz) → persiste la elección
  6. Instala GRUB en el destino (BIOS + UEFI x64), genera fstab
  7. Reboot → la PC arranca la rocola sola desde el disco
```

Seguridad: **nunca** formatea sin selección y confirmación explícitas del usuario.

Detalle: [docs/04-installer.md](docs/04-installer.md).

## 5. Subsistema de video (VGA + 15 kHz)

El requisito "ambos tipos de tubo sin configuración" se resuelve así:

- En monitores con **EDID útil** (VGA/moderno) se usan modos estándar.
- En **CRT 15 kHz** (arcade/TV, sin EDID confiable) se fuerzan **modelines 15 kHz** + `switchres`.
- El **tipo de monitor se elige una vez** en el instalador y se **persiste**; luego es automático en
  cada arranque → cumple "sin configuración una vez instalado".
- **Salvedad honesta**: 15 kHz real depende de GPU/driver compatibles; hay fallback a VGA seguro.

Detalle: [docs/05-display-crt-15khz.md](docs/05-display-crt-15khz.md).

## 6. Controles de arcade

- Los encoders USB típicos (iPAC/Xin-Mo/zero-delay) se presentan como **teclado** y/o **joystick**.
- La app usa **SDL2** para leer ambos y **autodetecta** el dispositivo presente.
- Mapeo de acciones (arriba/abajo, seleccionar, atrás, volumen, etc.) configurable.

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
| DATOS `/music` | ext4 | música del usuario | **sí** |

Reinstalar/actualizar el SO **no borra** la música del usuario.

Detalle: [docs/08-music-management.md](docs/08-music-management.md).

## 9. Estructura del repositorio

Ver [README.md](README.md#cómo-está-organizado). Cada carpeta de nivel superior mapea a un
subsistema de esta arquitectura y tiene su doc correspondiente en [`docs/`](docs/).
