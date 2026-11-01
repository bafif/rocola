# 05 · Video: VGA y CRT 15 kHz

La rocola tiene que andar en **monitores modernos o VGA (31 kHz o más)** y en **CRT de arcade o TV
(15 kHz)** sin configurar nada después de instalar. Es la parte más delicada del proyecto, y acá
cuento cómo la encaré y hasta dónde llega.

## El problema

- Los monitores modernos/VGA reportan sus modos por **EDID** → autoconfiguración estándar.
- Los **CRT de 15 kHz** (arcade, TV por RGB/compuesto/SCART) **no** dan EDID confiable y requieren
  **modelines de baja frecuencia** (p. ej. 320×240@60, 640×480i@60) que el driver normal no genera.
- Mandar 31 kHz a un CRT de 15 kHz no muestra imagen (o la daña). Hay que **forzar** 15 kHz.

## Estrategia

1. **Detección**: `rocola-display-setup` lee EDID. Si hay EDID válido de monitor multisync/VGA →
   usa modos estándar.
2. **15 kHz**: si al instalar se eligió un CRT de 15 kHz (o no hay EDID), aplica los modelines de
   15 kHz de `display/modelines/` y usa **switchres** para elegir el mejor modo según el contenido.
3. **Una sola elección, al instalar**: el instalador pregunta el tipo de monitor y guarda la
   respuesta en `/etc/rocola/display.conf`. De ahí en adelante, cada arranque la aplica solo.
4. **Fallback seguro**: si algo falla, cae a 640×480/800×600 VGA para no quedar a ciegas.

```
arranque → rocola-display-setup
              ├─ lee /etc/rocola/display.conf  (modo elegido al instalar)
              ├─ VGA/moderno → modos por EDID
              └─ 15 kHz      → modelines 15 kHz + switchres
                                  └─ fallback VGA si no hay señal
```

## Componentes

- **modelines** (`display/modelines/`): perfiles 15 kHz (NTSC/PAL, 320×240, 640×480i…) y VGA.
- **switchres**: genera/cambia modelines para acercarse a la resolución/refresh ideales del CRT.
- **Xorg**: config mínima que admite modelines custom; la app SDL2 renderiza al modo activo.

## El límite del hardware

Los 15 kHz no andan en cualquier máquina: hace falta una placa de video y un driver que acepten
modelines de baja frecuencia por la salida correcta (normalmente la VGA analógica). Las placas y
drivers que mejor se portan con esto son los que documenta la comunidad de arcade (GroovyArcade,
CRT_EmuDriver). En hardware que no los acepta, la rocola funciona igual con un monitor VGA o moderno
y, si se eligió 15 kHz, vuelve a un modo seguro.

O sea, con VGA o un monitor moderno anda siempre; con 15 kHz, donde el hardware lo permita.

## La app y la baja resolución

La UI SDL2 dibuja directamente a 320×240 o 640×480, así que en un CRT se ve bien, sin escalados
feos. El branding y la disposición de las pantallas tienen en cuenta el «title-safe area» de los
CRT.

Siguiente: [06 · Controles de arcade](06-arcade-controls.md).
