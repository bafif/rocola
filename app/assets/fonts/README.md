# Fuentes

*[English](README.en.md) · Español*

Las tipografías que usan los temas. Cada tema las nombra en su `theme.toml` (`[fonts]`, ver
[docs/09](../../../docs/09-branding-theming.md)); la que falta usa otra del tema y, al final, la de SDL,
así que el build nunca se rompe por una fuente.

Sólo fuentes con licencia libre que permita redistribuirlas (OFL o Apache), cada una con su
licencia al lado y anotada acá. Se incluyen sin modificar.

| Archivo | Fuente | Autor | Licencia | De dónde | La usa |
|---------|--------|-------|----------|----------|--------|
| `Limelight-Regular.ttf` | Limelight | Sorkin Type Co | SIL OFL 1.1, nombre reservado «Limelight» ([`Limelight-OFL.txt`](Limelight-OFL.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/ofl/limelight) | Ámbar: la marquesina |
| `SpecialElite-Regular.ttf` | Special Elite | Astigmatic | Apache 2.0 ([`SpecialElite-LICENSE.txt`](SpecialElite-LICENSE.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/apache/specialelite) | Ámbar: las tarjetas |
| `Oswald-Medium.ttf`, `Oswald-SemiBold.ttf` | Oswald | The Oswald Project Authors | SIL OFL 1.1 ([`Oswald-OFL.txt`](Oswald-OFL.txt)) | [googlefonts/OswaldFont](https://github.com/googlefonts/OswaldFont/tree/main/fonts/ttf) (las estáticas: el pygame de bookworm dibuja una variable sólo en su peso por defecto) | Ámbar: los datos y los números |
| `VT323-Regular.ttf` | VT323 | The VT323 Project Authors | SIL OFL 1.1 ([`VT323-OFL.txt`](VT323-OFL.txt)) | [google/fonts](https://github.com/google/fonts/tree/main/ofl/vt323) | Ámbar a 15 kHz: todo, sin suavizado; Display: el texto |
| `DSEG7Classic-Bold.ttf` | DSEG7 Classic | keshikan | SIL OFL 1.1, nombre reservado «DSEG» ([`DSEG-OFL.txt`](DSEG-OFL.txt)) | [keshikan/DSEG](https://github.com/keshikan/DSEG/releases/tag/v0.46) (v0.46) | Display: los códigos y los números |

Las licencias se revisan al incorporar cada fuente. `make theme-check` comprueba que cada una tenga
«ÁÉÍÓÚÜÑ¿¡», salvo la de los números (`digits`), que sólo dibuja números y las mayúsculas de los
códigos.
