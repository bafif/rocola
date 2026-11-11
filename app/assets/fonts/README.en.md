# Fonts

*English · [Español](README.md)*

The typefaces the themes use. Each theme names them in its `theme.toml` (`[fonts]`, see
[docs/09](../../../docs/09-branding-theming.en.md)); a missing one falls back to another of the theme
and, last, to SDL's own, so the build never breaks because of a font.

Only fonts whose license allows redistributing them (OFL or Apache), each with its license next to
it and listed here. They are included unmodified.

| File | Font | Author | License | Source | Used by |
|------|------|--------|---------|--------|---------|
| `Limelight-Regular.ttf` | Limelight | Sorkin Type Co | SIL OFL 1.1, Reserved Font Name "Limelight" ([`Limelight-OFL.txt`](Limelight-OFL.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/ofl/limelight) | Ámbar: the marquee |
| `SpecialElite-Regular.ttf` | Special Elite | Astigmatic | Apache 2.0 ([`SpecialElite-LICENSE.txt`](SpecialElite-LICENSE.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/apache/specialelite) | Ámbar: the cards |
| `Oswald-Medium.ttf`, `Oswald-SemiBold.ttf` | Oswald | The Oswald Project Authors | SIL OFL 1.1 ([`Oswald-OFL.txt`](Oswald-OFL.txt)) | [googlefonts/OswaldFont](https://github.com/googlefonts/OswaldFont/tree/main/fonts/ttf) (the static ones: bookworm's pygame draws a variable font only at its default weight) | Ámbar: the data and the numbers |
| `VT323-Regular.ttf` | VT323 | The VT323 Project Authors | SIL OFL 1.1 ([`VT323-OFL.txt`](VT323-OFL.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/ofl/vt323) | Ámbar at 15 kHz: everything, without antialiasing; Display: the text |
| `DSEG7Classic-Bold.ttf` | DSEG7 Classic | keshikan | SIL OFL 1.1, reserved font name «DSEG» ([`DSEG-OFL.txt`](DSEG-OFL.txt)) | [keshikan/DSEG](https://github.com/keshikan/DSEG/releases/tag/v0.46) (v0.46) | Display: the codes and the numbers |

Each license is checked when its font is added. `make theme-check` checks that each one has
"ÁÉÍÓÚÜÑ¿¡", except the numbers one (`digits`), which only draws numbers and the capitals of the
codes.
