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

## 🚀 Inicio rápido

### 1. Construir la imagen

Requisitos en la máquina de build: **Docker** y `make`. (En CPUs x86-64 Docker corre los
contenedores i386 nativo; en otros hosts, instalá binfmt una vez —ver
[docs/02](docs/02-build-pipeline.md)—.)

```bash
make rootfs         # construye el SO (imagen Docker i386); la primera vez tarda
make image          # produce out/rocola-i386.img: ISO híbrida booteable BIOS + UEFI x64
```

> **Estado:** verificado de punta a punta — `make image` genera la ISO y **arranca en QEMU (BIOS)
> hasta la UI de la rocola a pantalla completa, con MPD conectado**. Capturas en
> [docs/screenshots/](docs/screenshots/); detalle en [docs/12-verificacion.md](docs/12-verificacion.md).

### 2. Grabar el pendrive

```bash
make flash DEV=/dev/sdX     # ⚠️ DESTRUCTIVO: reemplazá sdX por tu pendrive
# o con tu herramienta gráfica favorita (p. ej. balenaEtcher) usando out/rocola-i386.img
```

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
