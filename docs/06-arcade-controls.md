# 06 · Controles de arcade

La rocola se maneja con **controles de arcade** (joystick + botones), sin teclado ni mouse en el uso
diario.

## Hardware típico

Los gabinetes de arcade usan un **encoder USB** que conecta los microswitches de joystick/botones y
los presenta a la PC como un dispositivo de entrada. Los más comunes:

- **Modo teclado** (iPAC, y muchos "zero-delay"): cada botón = una tecla.
- **Modo joystick/gamepad** (Xin-Mo, "zero-delay" en modo gamepad): ejes + botones.

Algunos encoders pueden funcionar en cualquiera de los dos modos.

## Enfoque: autodetección (teclado **y** joystick)

La app usa **SDL2**, que ya abstrae teclado y joystick. Al iniciar:

1. Enumera e inicializa **todos** los joysticks presentes (y los vuelve a enumerar cuando se
   enchufa o desenchufa uno).
2. Deja además el mapeo por **teclado** siempre activo.
3. No hace falta elegir: joystick y teclado funcionan a la vez.

## Acciones de la rocola

Los números de botón son los índices de SDL (empiezan en 0); `jstest` o `evtest` muestran cuál
manda cada botón del encoder.

| Acción | Joystick | Teclado (default) |
|--------|----------|-------------------|
| Navegar arriba/abajo | eje Y (ejes impares) / D-pad | ↑ / ↓ |
| Navegar izq/der (páginas, letras) | eje X (ejes pares) / D-pad | ← / → |
| Seleccionar / Reproducir | botón 0 | Enter |
| Atrás / Cancelar | botón 1 | Esc / Backspace |
| Play/Pausa | botón 2 | Espacio |
| Menú (audio, info, instalador) | botón 3 | F10 |
| Anterior / Siguiente | botones 4 / 5 | P / N |
| Volumen − / + | botones 6 / 7 | − / + (o =) |

Los ejes analógicos tienen zona muerta de 0,5 y disparan una sola acción por cada movimiento
(mantener el stick apretado no repite).

Los mapeos por defecto están en `app/rocola/input.py` (`DEFAULT_KEYMAP` y `DEFAULT_BUTTONMAP`). Se
cambian sin tocar código con las tablas `[keys]` y `[buttons]` de `/etc/rocola/rocola.toml`, que se
suman a los de por defecto:

```toml
[keys]          # nombre de tecla de SDL -> acción
m = "menu"
f10 = "none"    # "none" saca un mapeo por defecto

[buttons]       # índice de botón del joystick -> acción
8 = "menu"
3 = "none"
```

Acciones: `up`, `down`, `left`, `right`, `select`, `back`, `playpause`, `next`, `prev`, `volup`,
`voldown` y `menu`. Una tecla o una acción desconocida se ignora: la configuración nunca impide que
la app arranque. En el modo en vivo `/etc` vive en RAM; para que el archivo viaje en la imagen va en
`os/rootfs-overlay/etc/rocola/rocola.toml` antes de `make rootfs`. En el sistema instalado se edita
directamente.

## Calibración

La app lee el joystick por **índice de botón** (la API de joystick de SDL, no la de GameController),
así que un mapping de SDL_GameControllerDB no cambia nada. Para un encoder con otra numeración hay
que ajustar `[buttons]`. Para ver qué índice manda cada botón: menú → **Probar controles**. Cada
tecla o botón aparece con el nombre o el índice que va en `[keys]`/`[buttons]` y la acción que le
toca hoy. Se sale con Atrás dos veces seguidas o a los 15 s sin tocar nada, así un encoder mal
mapeado no deja a nadie adentro.

## Acceso al instalador

El **instalador guiado** se abre desde el menú (botón 3 o F10) → «Instalar en disco». No hay atajo
directo, para no dispararlo sin querer durante el uso normal, y el instalador pide confirmación
antes de tocar un disco.

Siguiente: [07 · La app](07-rocola-app.md).
