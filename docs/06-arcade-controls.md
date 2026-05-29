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

1. Enumera joysticks presentes (`SDL_Joystick`/`SDL_GameController`).
2. Habilita además el mapeo por **teclado**.
3. **Autodetecta**: usa el primer joystick disponible; si no hay, opera por teclado. Ambos quedan
   activos a la vez (no hace falta elegir).

## Acciones de la rocola

| Acción | Joystick | Teclado (default) |
|--------|----------|-------------------|
| Navegar arriba/abajo | eje Y / D-pad | ↑ / ↓ |
| Navegar izq/der (páginas, letras) | eje X / D-pad | ← / → |
| Seleccionar / Reproducir | botón 1 | Enter |
| Atrás / Cancelar | botón 2 | Esc / Backspace |
| Play/Pausa | botón 3 | Space |
| Siguiente / Anterior | botones 4/5 | N / P |
| Volumen +/- | botones 6/7 | + / - |
| Menú / Salir a instalador | combo (p. ej. Start+Select) | F10 |

Los mapeos viven en la config del tema/app (`app/rocola/config.py` + archivo de usuario) y son
**reconfigurables** sin tocar el código.

## Calibración

- Para joysticks "raros", se puede generar/editar un mapping estilo SDL_GameControllerDB.
- Una pantalla de **test de input** (planeada) permite ver qué evento manda cada botón para mapearlo.

## Combo de instalación

El acceso al **instalador guiado** se hace con un combo poco accidental (p. ej. mantener Start+Select
unos segundos, o F10 en teclado), para no dispararlo sin querer durante el uso normal.

Siguiente: [07 · La app](07-rocola-app.md).
