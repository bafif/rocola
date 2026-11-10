# 09 · Branding y temas

*[English](09-branding-theming.en.md) · Español*

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
title  = { es = "MI ROCOLA", en = "MY JUKEBOX" }
```

`app/rocola/theme.py` lee este archivo; el código **nunca** hardcodea colores ni rutas de imagen.
El título del encabezado puede ser un solo texto (`title = "BAR PEPE"`) o uno por idioma de la
rocola, como arriba; si falta el del idioma activo, se usa el que haya.

## Consideraciones para CRT

- Alto contraste y tipografías legibles a 320×240 / 640×480.
- Respetar el *title-safe area* (no pegar texto a los bordes; los CRT recortan).
- Evitar líneas horizontales de 1 px puro en contenido entrelazado (parpadean); preferir grosores ≥2.

## Cambiar de tema

El tema activo se elige con `theme` en `/etc/rocola/rocola.toml` (o con la variable
`ROCOLA_THEME`), con el nombre de una carpeta de `themes/`. Se pueden tener varios temas y elegir
uno en cada instalación (ver [07](07-rocola-app.md)).

## Fuentes y licencias

Las tipografías incluidas deben tener licencia compatible (OFL/MIT/Apache). Documentá cada una en
`app/assets/fonts/README.md`. Si falta una fuente, la app cae a una fuente del sistema.

Siguiente: [10 · Grabar el pendrive](10-flashing-usb.md).
