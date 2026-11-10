# Fonts

*English · [Español](README.md)*

Put the typefaces (`.ttf`/`.otf`) your theme uses here and reference them from
`themes/<tema>/theme.toml` (the `[fonts] title` and `body` keys).

**No fonts are included by default**: if the theme doesn't specify one (or the file
is missing), the app falls back to pygame/SDL's built-in font. That way the build
never breaks because a typeface is missing.

## Licenses

Only use fonts with a free/redistributable license (OFL, Apache, MIT). Document
each one here. Some suggestions that fit the arcade/jukebox aesthetic:

- **Press Start 2P** (OFL) — arcade-style headings.
- **Inter** / **DejaVu Sans** (OFL) — body text that stays readable at low resolution.

> Remember: readability at 320×240 / 640×480 and respecting the CRT's *title-safe area*.