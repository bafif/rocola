# 09 · Branding and themes

*English · [Español](09-branding-theming.md)*

The look is **100% custom and replaceable** without touching the app's logic. Logos, colors and fonts
are loaded from `app/assets/` based on a theme file.

## What you can customize

- **Logo** (home screen and header).
- **Colors** (background, accents, text, selection highlight).
- **Fonts** (headings and body).
- **Background/atmosphere** (image or solid color; designed to look good on a CRT).
- **Text** (jukebox name, messages).

## Structure

```
app/assets/
  logo.svg            # main logo (vector; can be replaced with a PNG)
  fonts/              # typefaces (.ttf/.otf) + licenses README
  themes/
    default/
      theme.toml      # colors, fonts, asset paths, text
      background.png  # optional
```

`theme.toml` (conceptual example):

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

`app/rocola/theme.py` reads this file; the code **never** hardcodes colors or image paths.
The header title can be a single text (`title = "BAR PEPE"`) or one per jukebox language, as
above; if the active language has none, whichever one there is gets used.

## CRT considerations

- High contrast and typefaces that stay legible at 320×240 / 640×480.
- Respect the *title-safe area* (don't put text right up against the edges; CRTs crop them).
- Avoid pure 1 px horizontal lines in interlaced content (they flicker); prefer thicknesses ≥2.

## Switching themes

The active theme is set with `theme` in `/etc/rocola/rocola.toml` (or with the `ROCOLA_THEME`
variable), using the name of a folder inside `themes/`. You can have several themes and pick
one for each installation (see [07](07-rocola-app.en.md)).

## Fonts and licenses

Bundled typefaces must have a compatible license (OFL/MIT/Apache). Document each one in
`app/assets/fonts/README.md`. If a font is missing, the app falls back to a system font.

Next: [10 · Flashing the USB drive](10-flashing-usb.en.md).