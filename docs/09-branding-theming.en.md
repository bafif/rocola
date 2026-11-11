# 09 · Branding and themes

*English · [Español](09-branding-theming.md)*

Everything on screen comes from a theme: the app knows no colors and no image files. A theme is a
folder in `app/assets/themes/` with a `theme.toml` and, if it has artwork, its images. The jukebox
ships with **Ámbar**, the default theme, with its pieces, its fonts and a version of its own for
15 kHz.

## Layout

```
app/assets/
  fonts/              # shared typefaces (.ttf/.otf) + README with their licenses
  themes/
    ambar/
      theme.toml      # colors, fonts, pieces, effects and variants
      *.png           # pieces (optional)
      src/            # the original SVGs of the pieces
```

## `theme.toml`

```toml
version = 2
name    = "Ámbar"
[colors]
background = "#24140c"
surface    = "#f1e4c6"
text       = "#2a160b"
on_dark    = "#f1e4c6"
accent     = "#8c1c2c"
glow       = "#ffcf7a"
[fonts]      # from the theme folder or from app/assets/
marquee = "fonts/Limelight-Regular.ttf"
body    = "fonts/Oswald-Medium.ttf"
[pieces]     # PNG; `slice` is the nine-slice cuts: left, top, right, bottom
strip = { file = "strip.png", slice = [10, 6, 10, 6] }
[effects]
record = { rpm = 45 }
[variant.crt15]
fonts.body      = "fonts/VT323-Regular.ttf"
fonts.antialias = false
[variant.tv]
safe_area = 0.10
[branding]
title = { es = "MI ROCOLA", en = "MY JUKEBOX" }
```

- **Colors**, by role:

  | Role | What it paints |
  |------|----------------|
  | `background` | what is behind everything: the cabinet |
  | `surface` | the title cards and the panels |
  | `text`, `text_dim` | text on `surface` |
  | `on_dark`, `on_dark_dim` | text on `background` |
  | `accent` | the stripes and codes of the cards |
  | `glow` | the cursor and the lamps |

  If `text_dim` or `on_dark_dim` is missing, it is mixed from its pair.
- **Fonts**: `marquee` (the marquee), `strip` (the cards), `body` (the text) and `digits` (numbers
  and codes). A missing one uses another (marquee → cards → text; numbers → text) and, last, SDL's
  own. `antialias = false` is for pixel fonts.
- **Pieces**: PNG images. A missing one is drawn with the colors. The ones in use: `cabinet` (the
  cabinet, behind everything), `marquee` (the marquee; the text keeps off its side cuts), `strip`
  (the paper of a song's card: the jukebox draws the stripe, after the code), `index` (an artist's
  or an album's; without it, `strip` in a frame), `cursor` (the light around the chosen card) and
  `lamp_on` and `lamp_off` (the lamps) and `tube` (the bubble tube; the jukebox draws the
  bubbles).
- **Effects**: the parameters each screen reads. `chaser = { lamps = 16, step_ms = 120 }` are the
  lamps under the marquee: how many, and how long each step lasts when they run.
- **Variants**: `[variant.lcd]`, `[variant.crt]`, `[variant.crt15]` and `[variant.tv]` are laid over
  the base according to the kind of display. A table is merged key by key (`fonts.body` changes only
  that font); a piece or an effect is replaced whole.
- **`safe_area`**: the margin on each side, as a fraction of the screen; without it, the display
  kind's own.
- **`[branding] title`**: the marquee text, a single one (`title = "BAR PEPE"`) or one per language;
  if the active language has none, whichever there is.

Nothing is required: if the theme is missing or broken, the jukebox starts in black and white.

## Kinds of display

| Kind | What it is | Margin | Smallest text | Cards per page |
|------|------------|--------|---------------|----------------|
| `lcd` | flat panel | 3 % | 18 px | 10 |
| `crt` | PC tube monitor (VGA, 31 kHz or more) | 5 % | 16 px | 8 |
| `crt15` | tube over RGB at 15 kHz (arcade or SCART) | 8 % | 10 px | 6 |
| `tv` | TV over composite, S-Video or a converter | 10 % | 14 px | 6 |

The kind comes from `display` in `/etc/rocola/rocola.toml` (see [07](07-rocola-app.en.md)); if it is
not there, from `/etc/rocola/display.conf` (`MODE=crt15` is `crt15`), and otherwise it is `lcd`. The
jukebox doesn't detect the kind of display by itself yet.

The cards go in two columns, the left one first, top to bottom. Their code is the page and the place
on it: with 10 a page, the eleventh card is B1 (the letters skip I and O, and after Z come AA,
AB…). It is not saved anywhere: it comes from the order of the list and changes with the kind of
display.

## Effects

`effects` in `/etc/rocola/rocola.toml` is `completo`, `suave` or `apagado` (also `full`, `soft`,
`off`). If frames take more than 20 ms on average, the jukebox lowers it one step by itself and does
not raise it again until it restarts.

When a song starts, the marquee's lamps run for 4 seconds (2 with `suave`, never with `apagado`) and
then stay lit; in the attraction mode they run all the time. While they run, the jukebox draws and
sends to the screen only that row, one frame per step. On starting, the marquee lights up over a
second (with `apagado`, already lit).

`glow = "plano"` draws the lamps as flat circles, without their pieces' blurred glow; Ámbar uses it
on a TV and at 15 kHz. A variant can also change the pieces: Ámbar's `crt15` one uses those in
`240p/`, drawn for that resolution (their SVGs are in `src/240p/`).

`bubbles = { tubes = 2, per_tube = 7 }` puts a tube at each side of the jukebox's screens
(`tubes = 0` takes them out) with that many bubbles, which rise by the clock: 15 frames a second
with `completo`, 8 with `suave`, and still with `apagado`. Those frames send to the screen only the
tubes and the row of lamps.

## Tools

- `make theme-check [THEME=ambar]` (or `python -m rocola.theme check <theme>`): for each kind of
  display, the contrast of every text against what is behind it (on a TV, by luminance), that the
  fonts have «ÁÉÍÓÚÜÑ¿¡», and that the files the theme names exist and load. The tests run it on
  every bundled theme.
- `make theme-assets`: turns each theme's `src/<path>.svg` into `<path>.png`, in a Podman
  container. The PNGs are committed.
- `make theme-shots THEME=ambar`: a screenshot of every screen on every kind of display, in
  `out/shots/<theme>/`, with made-up music (`app/tools/fake-mpd.py`): the library with many
  artists and, in `<kind>-songs.png`, with only one, to see the song cards.

## Changing the theme

The active theme is set with `theme` in `/etc/rocola/rocola.toml` (or with the `ROCOLA_THEME`
variable), with the name of a folder in `themes/`. You can have several themes and pick one for each
installation (see [07](07-rocola-app.en.md)).

## Fonts and licenses

Bundled typefaces must be under the OFL or Apache license. Each one is listed in
`app/assets/fonts/README.md`.

Next: [10 · Flashing the USB drive](10-flashing-usb.en.md).
