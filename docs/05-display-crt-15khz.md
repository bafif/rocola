# 05 · Video: VGA y CRT 15 kHz

El objetivo es funcionar en **monitores modernos/VGA (31 kHz+)** y en **CRT de arcade/TV (15 kHz)**
sin configuración una vez instalado. Esto es lo más delicado del proyecto; acá va el enfoque honesto.

## El problema

- Los monitores modernos/VGA reportan sus modos por **EDID** → autoconfiguración estándar.
- Los **CRT de 15 kHz** (arcade, TV por RGB/compuesto/SCART) **no** dan EDID confiable y requieren
  **modelines de baja frecuencia** (p. ej. 320×240@60, 640×480i@60) que el driver normal no genera.
- Mandar 31 kHz a un CRT de 15 kHz no muestra imagen (o la daña). Hay que **forzar** 15 kHz.

## Estrategia

1. **Detección**: `rocola-display-setup` lee EDID. Si hay EDID válido de monitor multisync/VGA →
   usa modos estándar.
2. **15 kHz**: si el usuario indicó CRT 15 kHz (o no hay EDID), aplica **modelines 15 kHz** desde
   `display/modelines/` e integra **switchres** para elegir el mejor modo por contenido.
3. **Elección única al instalar**: el instalador pregunta el tipo de monitor y **persiste** la
   decisión (`/etc/rocola/display.conf`). A partir de ahí, **automático en cada arranque** →
   cumple "sin configuración una vez instalado".
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

## Salvedad importante (hardware)

El 15 kHz **no es universal**: depende de **GPU + driver** que soporten modelines de baja frecuencia
por la salida correcta (VGA analógico típicamente). Tarjetas/drivers históricamente buenos para esto
son los documentados por la comunidad de arcade (GroovyArcade/CRT_EmuDriver). En hardware no
compatible, el sistema **funciona igual en VGA/moderno** y degrada el 15 kHz a un modo seguro.

> No prometemos 15 kHz en cualquier placa. Sí: VGA/moderno siempre; 15 kHz donde el hardware lo permita.

## La app y la baja resolución

La UI SDL2 renderiza **nativo** a 320×240 / 640×480, por lo que se ve bien en CRT sin escalados
feos. El branding y los layouts se diseñan teniendo en cuenta el "title-safe area" de los CRT.

Siguiente: [06 · Controles de arcade](06-arcade-controls.md).
