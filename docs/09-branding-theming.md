# 09 · Branding y temas

La estética es **100% propia y reemplazable** sin tocar la lógica de la app. Logos, colores y fuentes
se cargan desde `app/assets/` según un archivo de tema.

## Qué se puede personalizar

- **Logo** (pantalla de inicio y cabecera).
- **Colores** (fondo, acentos, texto, resaltado de selección).
- **Fuentes** (titulares y cuerpo).
- **Fondo/atmósfera** (imagen o color sólido; pensado para verse bien en CRT).
- **Textos** (nombre de la rocola, mensajes).

## Estructura

```
app/assets/
  logo.svg            # logo principal (vectorial; reemplazable por PNG)
  fonts/              # tipografías (.ttf/.otf) + README de licencias
  themes/
    default/
      theme.toml      # colores, fuentes, rutas de assets, textos
      background.png  # opcional
```

`theme.toml` (ejemplo conceptual):

```toml
name = "Rocola Clásica"
[colors]
background = "#0b0b15"
accent     = "#ff3366"
text       = "#f5f5f5"
highlight  = "#ffd24a"
[fonts]
title = "fonts/PressStart2P.ttf"
body  = "fonts/Inter-Regular.ttf"
[branding]
logo   = "logo.svg"
title  = "MI ROCOLA"
```

`app/rocola/theme.py` lee este archivo; el código **nunca** hardcodea colores ni rutas de imagen.

## Consideraciones para CRT

- Alto contraste y tipografías legibles a 320×240 / 640×480.
- Respetar el *title-safe area* (no pegar texto a los bordes; los CRT recortan).
- Evitar líneas horizontales de 1 px puro en contenido entrelazado (parpadean); preferir grosores ≥2.

## Cambiar de tema

Setear el tema activo en la config (`config.py` / archivo de usuario) apuntando a una carpeta en
`themes/`. Se pueden mantener varios temas y elegir uno por instalación.

## Fuentes y licencias

Las tipografías incluidas deben tener licencia compatible (OFL/MIT/Apache). Documentá cada una en
`app/assets/fonts/README.md`. Si falta una fuente, la app cae a una fuente del sistema.

Siguiente: [10 · Grabar el pendrive](10-flashing-usb.md).
