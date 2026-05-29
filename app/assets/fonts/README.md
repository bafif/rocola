# Fuentes

Poné acá las tipografías (`.ttf`/`.otf`) que use tu tema y referencialas desde
`themes/<tema>/theme.toml` (claves `[fonts] title` y `body`).

**No se incluyen fuentes por defecto**: si el tema no especifica una (o el archivo
falta), la app usa la fuente integrada de pygame/SDL como fallback. Así el build
nunca se rompe por falta de una tipografía.

## Licencias

Usá solo fuentes con licencia libre/redistribuible (OFL, Apache, MIT). Documentá
cada una acá. Sugerencias que combinan con la estética arcade/rocola:

- **Press Start 2P** (OFL) — titulares tipo arcade.
- **Inter** / **DejaVu Sans** (OFL) — cuerpo legible a baja resolución.

> Recordá: legibilidad a 320×240 / 640×480 y respetar el *title-safe area* del CRT.
