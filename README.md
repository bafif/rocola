# 🎵 Rocola

> Convertí cualquier computadora de escritorio vieja en una **rocola (jukebox)** dedicada con un solo pendrive.

**Rocola** es un sistema operativo mínimo basado en **Debian i386** que se distribuye como un
**pendrive booteable**. Al encender una PC con el pendrive, arranca una rocola lista para usar; y
con un disparo manual podés **clonar** ese sistema al disco interno para que la máquina quede
convertida en una rocola permanente que **abre sola al prender**, se maneja con **controles de
arcade** y funciona tanto en **monitores modernos** como en **monitores de tubo (CRT), incluyendo
los de 15 kHz de arcade/TV**, sin configuración posterior.

---

## ✨ Características

- **Pendrive todo-en-uno**: arranca una rocola "en vivo" sin tocar el disco de la PC.
- **Instalador guiado de disparo manual**: clona el sistema al disco interno solo cuando vos lo
  decidís, con confirmación anti-borrado. Nunca formatea automáticamente.
- **Hardware viejo**: pensado para PCs de ~2 GB de RAM, CPU de 32 bits (i386). Arranca por **BIOS**
  (PCs de 32 y 64 bits) y por **UEFI x64**.
- **Soporte CRT real**: monitores VGA (31 kHz) **y** arcade/TV de 15 kHz vía `switchres` + modelines.
- **Controles de arcade**: encoders USB que se presentan como **teclado y/o joystick**, autodetectados.
- **UI propia y brandeable**: interfaz "rocola" hecha a medida con **SDL2** (Python + pygame-ce)
  sobre **MPD** como motor de audio. Logos, fuentes y tema reemplazables.
- **Tu música, fácil**: biblioteca **precargada** en la imagen **+** import desde un **segundo USB**
  a una **partición de datos persistente** que sobrevive reinstalaciones.
- **Open source**: 100% software libre, licencia MIT.

---

## ⬇️ Descargar y grabar (sin compilar)

¿Solo querés el pendrive? No hace falta compilar nada ni tener Docker.

1. Descargá el archivo `rocola-i386-<versión>.iso` (~405 MB) desde la página de
   **[Releases](https://github.com/bafif/rocola/releases/latest)**.
2. *(Opcional, recomendado)* verificá la descarga contra el `SHA256SUMS.txt` del Release:
   - **Windows (PowerShell):** `Get-FileHash rocola-i386-*.iso -Algorithm SHA256`
   - **Linux / macOS:** `sha256sum -c SHA256SUMS.txt`

   y comprobá que el hash coincida con el publicado.
3. Grabá el `.iso` a un pendrive (≥ 1 GB; **se borra entero**):

   | Herramienta | Cómo |
   |-------------|------|
   | **Rufus** (Windows) | *Dispositivo* = tu pendrive → *Seleccionar* el `.iso` → *Empezar* → elegí **"Escribir en modo Imagen DD"** (la imagen es híbrida; en modo DD el resto de opciones se ignoran). Guía detallada: [docs/13](docs/13-rufus-windows.md). |
   | **Ventoy** (Windows/Linux) | Instalá Ventoy en el pendrive **una vez** y después **copiá** el `.iso` a su partición. No hace falta reformatear para actualizar. |
   | **balenaEtcher** (multiplataforma) | *Flash from file* → el `.iso` → elegí el pendrive → *Flash*. |

4. Booteá la PC vieja desde el pendrive (BIOS o UEFI x64) y seguí desde [Usar](#3-usar).

> El archivo es una **ISO 9660 híbrida (isohybrid)**: arranca por **BIOS y por UEFI x64**, y se
> puede grabar con `dd`, Rufus o balenaEtcher, o copiar a Ventoy — todo desde el mismo `.iso`.

---

## 🚀 Inicio rápido

### 1. Construir la imagen

Requisitos en la máquina de build: **Docker** y `make`. (En CPUs x86-64 Docker corre los
contenedores i386 nativo; en otros hosts, instalá binfmt una vez —ver
[docs/02](docs/02-build-pipeline.md)—.)

```bash
make rootfs         # construye el SO (imagen Docker i386); la primera vez tarda
make image          # produce out/rocola-i386.img: ISO híbrida booteable BIOS + UEFI x64
make release VERSION=v0.1.0-beta   # empaqueta out/release/rocola-i386-<ver>.iso + SHA256SUMS.txt
```

> **Estado:** verificado de punta a punta en QEMU/KVM — `make image` genera la ISO y arranca hasta la
> UI de la rocola a pantalla completa (MPD conectado) por **BIOS y por UEFI x64**; además el
> **instalador clona a un disco vacío** (particiona, copia el SO, pone GRUB) y ese **disco arranca
> solo** —sin pendrive— a la rocola, también por BIOS y UEFI. Capturas en
> [docs/screenshots/](docs/screenshots/); detalle y bugs corregidos en
> [docs/12-verificacion.md](docs/12-verificacion.md).

### 2. Grabar el pendrive

```bash
make flash DEV=/dev/sdX     # ⚠️ DESTRUCTIVO: reemplazá sdX por tu pendrive
# o con tu herramienta gráfica favorita (p. ej. balenaEtcher) usando out/rocola-i386.img
```

> En Windows usá **Rufus**, **Ventoy** o **balenaEtcher** con el `.iso` del Release; ver
> [Descargar y grabar (sin compilar)](#️-descargar-y-grabar-sin-compilar).

### 3. Usar

1. Enchufá el pendrive en la PC vieja y encendéla (configurá el orden de booteo si hace falta).
2. Arranca la **rocola en vivo**. Ya podés escuchar música.
3. Para dejarla instalada: abrí el **instalador guiado** (combo de teclas/menú de arcade), elegí el
   disco destino, confirmá, elegí tipo de monitor (moderno/VGA o 15 kHz) y reiniciá.
4. Sacá el pendrive: la PC ahora **abre la rocola sola** en cada arranque.

### 4. Cargar música

- **Precargada**: poné carpetas en `os/rootfs-overlay/opt/rocola/music/` antes de `make image`.
- **Desde USB**: enchufá un pendrive con tus canciones; la rocola lo detecta y las importa a la
  partición de datos (`/music`). Ver [docs/08-music-management.md](docs/08-music-management.md).

---

## 🧱 Cómo está organizado

```
os/         SO de la rocola (Dockerfile FROM i386/debian:bookworm + overlay de archivos)
image/      Empaquetado: rootfs -> imagen booteable (squashfs + GRUB BIOS/UEFI)
app/        UI de la rocola (Python + pygame-ce/SDL2) + cliente MPD + input
installer/  Instalador guiado (TUI whiptail) que clona el SO al disco
display/    Modelines 15 kHz + autodetección/selección VGA vs CRT (switchres)
docs/       Documentación detallada por subsistema
```

Ver **[ARCHITECTURE.md](ARCHITECTURE.md)** para el diseño completo y **[docs/](docs/)** para el
detalle de cada parte.

---

## 📚 Documentación

| Doc | Tema |
|-----|------|
| [docs/01-overview.md](docs/01-overview.md) | Visión general y objetivos |
| [docs/02-build-pipeline.md](docs/02-build-pipeline.md) | Pipeline de build (Docker → img) |
| [docs/03-boot-and-live.md](docs/03-boot-and-live.md) | Boot, live-boot, autologin, autostart |
| [docs/04-installer.md](docs/04-installer.md) | Instalador guiado y particionado |
| [docs/05-display-crt-15khz.md](docs/05-display-crt-15khz.md) | Video: VGA y CRT 15 kHz |
| [docs/06-arcade-controls.md](docs/06-arcade-controls.md) | Controles de arcade |
| [docs/07-rocola-app.md](docs/07-rocola-app.md) | La app (UI SDL2 + MPD) |
| [docs/08-music-management.md](docs/08-music-management.md) | Gestión de música |
| [docs/09-branding-theming.md](docs/09-branding-theming.md) | Branding y temas |
| [docs/10-flashing-usb.md](docs/10-flashing-usb.md) | Grabar el pendrive |
| [docs/11-troubleshooting.md](docs/11-troubleshooting.md) | Resolución de problemas |
| [docs/12-verificacion.md](docs/12-verificacion.md) | Qué está probado y qué falta validar |
| [docs/13-rufus-windows.md](docs/13-rufus-windows.md) | Grabar con Rufus en Windows (modo DD, opciones) |
| [docs/14-audio.md](docs/14-audio.md) | Salida de audio (PipeWire), Bluetooth y selección de salida |

---

## ⚠️ Salvedades

- El soporte **15 kHz** depende de una **GPU/driver compatibles** con modelines de baja frecuencia;
  donde no haya, el sistema cae a un modo VGA seguro. Ver
  [docs/05-display-crt-15khz.md](docs/05-display-crt-15khz.md).
- El armado de la imagen usa `grub-mkrescue` (xorriso + mtools): **no requiere privilegios** ni loop
  devices, así que funciona en WSL2/CI con un `docker run` normal.
- `make flash` **borra** el dispositivo destino: verificá `DEV` dos veces.

---

## 📄 Licencia

[MIT](LICENSE) © 2026 Bautista D. Fiori
