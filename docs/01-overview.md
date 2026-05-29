# 01 · Visión general

## El problema

Hay muchas computadoras de escritorio viejas dando vueltas. Convertir una en una rocola (jukebox)
de arcade normalmente implica instalar un SO, drivers, software, configurar video (más aún si el
monitor es de tubo), mapear controles y lograr que todo arranque solo. Es tedioso y se repite por
cada máquina.

## La solución

Un **único pendrive** que:

1. **Arranca una rocola lista para usar** en cualquier PC (modo live, sin tocar el disco).
2. **Se clona al disco interno** con un instalador guiado de disparo manual.
3. Deja la PC convertida en una **rocola permanente**: abre sola al prender, se maneja con controles
   de arcade y anda en monitores modernos y de tubo (VGA y 15 kHz) sin configuración posterior.

## Objetivos

- **Rápido**: de PC vieja a rocola en minutos, repetible máquina por máquina.
- **Cero fricción post-install**: enciende → rocola. Sin teclado/mouse necesarios para el uso diario.
- **Hardware modesto**: i386, ~2 GB RAM, GPUs viejas, CRT incluido.
- **Brandeable**: estética propia (logos, colores, fuentes) sin tocar lógica.
- **Libre**: 100% software libre (MIT).

## No-objetivos (por ahora)

- No es un media center general (no video/fotos/streaming): es una rocola de música.
- No apunta a UEFI de 32 bits puro (raro). Sí BIOS y UEFI x64.
- No garantiza 15 kHz en cualquier GPU: depende del hardware (ver [05](05-display-crt-15khz.md)).

## Glosario

- **Rocola**: jukebox; la máquina/medio para elegir y reproducir música.
- **Live**: sistema que corre desde el pendrive sin instalarse (en RAM/overlay).
- **15 kHz**: frecuencia horizontal de los CRT de arcade/TV (vs 31 kHz+ de monitores VGA).
- **MPD**: Music Player Daemon, el motor de audio.
- **switchres**: utilidad que genera/cambia modelines para CRT.

Siguiente: [02 · Pipeline de build](02-build-pipeline.md).
