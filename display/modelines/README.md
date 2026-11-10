# Modelines

*[English](README.en.md) · Español*

Perfiles de video que `rocola-display-setup` inserta en la config de Xorg.

- **`15khz.conf`** — modelines para CRT de arcade/TV (15 kHz). Valores de referencia;
  afinar por monitor (timings y posición varían). Para VGA/moderno no hace falta
  archivo: Xorg autodetecta por EDID.

## Afinar un CRT 15 kHz

1. Arrancar con `MODE=crt15` en `/etc/rocola/display.conf`.
2. Si la imagen sale corrida/sin sync, ajustar el `Modeline` correspondiente.
3. Al tocar un modeline, revisar las frecuencias: horizontal = reloj ÷ total horizontal (entre
   15,0 y 16,5 kHz, lo que `rocola-display-setup` le declara a Xorg) y vertical = horizontal ÷
   total vertical (el doble si es entrelazado). Un modeline fuera de rango Xorg lo descarta sin
   avisar. `switchres` los calcula a medida, pero no está en Debian y no viene en la imagen.

## Advertencia de hardware

El 15 kHz requiere **GPU/driver compatibles** con estos modelines por la salida
analógica (VGA). En hardware no compatible, usar `MODE=vga`. Ver
[../../docs/05-display-crt-15khz.md](../../docs/05-display-crt-15khz.md).
