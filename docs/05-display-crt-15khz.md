# 05 · Video: VGA y CRT 15 kHz

*[English](05-display-crt-15khz.en.md) · Español*

La rocola anda en **monitores modernos o VGA (31 kHz o más)** y en **CRT de arcade o TV (15 kHz)**
sin configurar nada después de instalar: el tipo de monitor se elige una vez, en el instalador.

## El problema

- Los monitores modernos/VGA reportan sus modos por **EDID** → autoconfiguración estándar.
- Los **CRT de 15 kHz** (arcade, TV por RGB/compuesto/SCART) **no** dan EDID confiable y requieren
  **modelines de baja frecuencia** (p. ej. 320×240@60, 640×480i@60) que el driver normal no genera.
- Mandar 31 kHz a un CRT de 15 kHz no muestra imagen (o la daña). Hay que **forzar** 15 kHz.

## Estrategia

1. **Una sola elección, al instalar**: el instalador pregunta el tipo de monitor (automático, VGA o
   15 kHz) y guarda la respuesta en `/etc/rocola/display.conf`. En cada arranque
   `rocola-display-setup` la aplica y escribe la config de Xorg.
2. **Automático y VGA**: una config VGA segura; Xorg toma los modos del monitor por **EDID** cuando
   lo hay. El modo automático no elige 15 kHz aunque no haya EDID: un monitor VGA viejo tampoco lo
   da, y mandarle 15 kHz lo dejaría en negro. Los 15 kHz se piden a propósito.
3. **15 kHz**: aplica los modelines fijos de `display/modelines/15khz.conf` y elige la resolución
   según el estándar de TV (`TV_STANDARD`): 640×480i a 60 Hz para NTSC, 768×576i a 50 Hz para PAL.
   `PREFERRED_RES` la cambia. Necesita KMS: se arranca con la entrada de GRUB «Rocola — GPU / CRT
   15 kHz (KMS)».
4. **Sin vuelta automática**: el sistema no puede saber si el monitor muestra imagen. Si un CRT
   queda en negro, se enchufa un monitor VGA y se cambia `MODE` en `/etc/rocola/display.conf` (o se
   reinstala eligiendo VGA).

```
arranque → rocola-display-setup
              ├─ lee /etc/rocola/display.conf  (modo elegido al instalar)
              ├─ auto / vga → config VGA segura; Xorg usa los modos del EDID
              └─ crt15      → modelines 15 kHz fijos (NTSC o PAL según TV_STANDARD)
```

## Driver de video

- La entrada por defecto del menú de arranque, «Rocola», arranca con `nomodeset`: Xorg usa `fbdev`
  sobre el framebuffer del firmware, que anda sin el driver de la placa. La resolución es la que deja
  GRUB (por ejemplo 800×600, con 32 o 16 bits de color).
- «Rocola — GPU / CRT 15 kHz (KMS)» carga el driver de la placa y Xorg usa `modesetting`: toma la
  resolución del monitor, y es la que hace falta para 15 kHz.
- Con esa entrada, `rocola-display-setup` espera a que se termine de cargar el driver de la placa
  antes de elegir el de Xorg (hasta 10 segundos; en una máquina lenta puede tardar). Si después de eso
  no aparece `/dev/dri/card0`, el kernel no maneja esa placa y usa `fbdev`. Con `nomodeset` no espera.
- El disco instalado arranca con el mismo video que el pendrive en el momento de instalar; con 15 kHz,
  siempre con KMS.
- En algunas APU de AMD (Picasso, Raven2) el driver `amdgpu` no anda con el kernel i386: ahí va la
  entrada por defecto.

## Componentes

- **modelines** (`display/modelines/15khz.conf`): 320×240 y 640×480i (NTSC, 60 Hz), 384×288 y
  768×576i (PAL, 50 Hz). Para VGA no hace falta archivo: Xorg los saca del EDID.
- **Xorg**: config mínima que admite modelines custom; la app SDL2 renderiza al modo activo.
- **EDID** (`display/rocola-edid`): con KMS, el kernel deja el EDID de cada conector en
  `/sys/class/drm/*/edid`. `rocola-display-setup` lo lee y anota en el log qué monitor encontró y en
  qué salida. Con la entrada por defecto (`nomodeset`) no hay conectores y no hay EDID que leer.
- `switchres`, que calcula modelines a medida de cada CRT, no está en Debian y no viene en la imagen.

## El límite del hardware

Los 15 kHz no andan en cualquier máquina: hace falta una placa de video y un driver que acepten
modelines de baja frecuencia por la salida correcta (normalmente la VGA analógica). Las placas y
drivers que mejor se portan con esto son los que documenta la comunidad de arcade (GroovyArcade,
CRT_EmuDriver). En hardware que no los acepta, la rocola funciona igual con un monitor VGA o moderno
(`MODE=vga`).

O sea, con VGA o un monitor moderno anda siempre; con 15 kHz, donde el hardware lo permita.

## La app y la baja resolución

La UI SDL2 dibuja directamente a 320×240 o 640×480, así que en un CRT se ve bien, sin escalados
feos. El branding y la disposición de las pantallas tienen en cuenta el «title-safe area» de los
CRT.

Siguiente: [06 · Controles de arcade](06-arcade-controls.md).
