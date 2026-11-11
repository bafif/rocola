# 09 · Branding y temas

*[English](09-branding-theming.en.md) · Español*

Todo lo que se ve sale de un tema: la app no conoce colores ni archivos de imagen. Un tema es una
carpeta de `app/assets/themes/` con un `theme.toml` y, si tiene arte, sus imágenes. La rocola trae
**Ámbar** (una rocola de fines de los 40), el tema por defecto; hasta que llegue su arte se dibuja
sólo con sus colores.

## Estructura

```
app/assets/
  fonts/              # tipografías compartidas (.ttf/.otf) + README con sus licencias
  themes/
    ambar/
      theme.toml      # colores, fuentes, piezas, efectos y variantes
      *.png           # piezas (opcionales)
      src/            # los SVG originales de las piezas
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
[fonts]      # desde la carpeta del tema o desde app/assets/
marquee = "fonts/Limelight-Regular.ttf"
body    = "fonts/Oswald-Medium.ttf"
[pieces]     # PNG; `slice` son los nueve cortes: izquierda, arriba, derecha, abajo
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

- **Colores**, por rol:

  | Rol | Qué pinta |
  |-----|-----------|
  | `background` | lo que está detrás de todo: el gabinete |
  | `surface` | las tarjetas y los paneles |
  | `text`, `text_dim` | el texto sobre `surface` |
  | `on_dark`, `on_dark_dim` | el texto sobre `background` |
  | `accent` | las franjas y los códigos de las tarjetas |
  | `glow` | el cursor y las lámparas |

  Si faltan `text_dim` u `on_dark_dim`, se mezclan de su par.
- **Fuentes**: `marquee` (la marquesina), `strip` (las tarjetas), `body` (el texto) y `digits`
  (números y códigos). La que falta usa otra (marquesina → tarjetas → texto; números → texto) y, al
  final, la de SDL. `antialias = false` es para fuentes de píxeles.
- **Piezas**: imágenes PNG. La que falta se dibuja con los colores. Las que se usan: `cabinet` (el
  gabinete, detrás de todo), `marquee` (la marquesina; el texto no pisa sus cortes de los
  costados), `strip` (el papel de la tarjeta de una canción: la franja la dibuja la rocola, después
  del código), `index` (la de un artista o un álbum; sin ella, `strip` con un marco), `cursor` (la
  luz alrededor de la tarjeta elegida), `lamp_on` y `lamp_off` (las lámparas) y `tube` (el tubo de
  burbujas; las burbujas las dibuja la rocola).
- **Efectos**: los parámetros que lee cada pantalla. `chaser = { lamps = 16, step_ms = 120 }` son
  las lámparas bajo la marquesina: cuántas y cuánto dura cada paso cuando corren.
- **Variantes**: `[variant.lcd]`, `[variant.crt]`, `[variant.crt15]` y `[variant.tv]` se superponen
  a la base según el tipo de pantalla. Una tabla se mezcla clave por clave (`fonts.body` cambia sólo
  esa fuente); una pieza o un efecto se reemplaza entero.
- **`safe_area`**: el margen de cada lado, como fracción de la pantalla; sin él, el del tipo de
  pantalla.
- **`[branding] title`**: el texto de la marquesina, uno solo (`title = "BAR PEPE"`) o uno por
  idioma; si falta el del idioma activo, se usa el que haya.

Nada es obligatorio: si falta el tema o está roto, la rocola arranca en blanco y negro.

## Tipos de pantalla

| Tipo | Qué es | Margen | Letra mínima | Tarjetas por página |
|------|--------|--------|--------------|---------------------|
| `lcd` | pantalla plana | 3 % | 18 px | 10 |
| `crt` | monitor de tubo de PC (VGA, 31 kHz o más) | 5 % | 16 px | 8 |
| `crt15` | tubo por RGB a 15 kHz (arcade o SCART) | 8 % | 10 px | 6 |
| `tv` | TV por compuesto, S-Video o conversor | 10 % | 14 px | 6 |

El tipo sale de `display` en `/etc/rocola/rocola.toml` (ver [07](07-rocola-app.md)); si no está, de
`/etc/rocola/display.conf` (`MODE=crt15` es `crt15`) y, si no, es `lcd`. Que la rocola detecte la
pantalla sola llega en una versión siguiente.

Las tarjetas van en dos columnas, primero la de la izquierda de arriba abajo. Su código es la página
y el lugar en ella: con 10 por página, la undécima es B1 (las letras saltean la I y la O, y después
de la Z siguen AA, AB…). No se guarda en ningún lado: sale del orden de la lista y cambia con el
tipo de pantalla.

## Efectos

`effects` en `/etc/rocola/rocola.toml` es `completo`, `suave` o `apagado` (también `full`, `soft`,
`off`). Si los cuadros tardan en promedio más de 20 ms, la rocola baja un nivel sola y no vuelve a
subir hasta que se reinicia.

Cuando arranca un tema, las lámparas de la marquesina corren 4 segundos (2 en `suave`, nunca en
`apagado`) y después quedan prendidas; en el modo atracción corren todo el tiempo. Mientras corren,
la rocola dibuja y manda a la pantalla sólo esa fila, un cuadro por paso. Al prender, la marquesina
se enciende en un segundo (en `apagado`, ya prendida).

`bubbles = { tubes = 2, per_tube = 7 }` pone un tubo a cada lado de las pantallas de la rocola
(`tubes = 0` los saca) con esas burbujas, que suben por reloj: 15 cuadros por segundo en `completo`,
8 en `suave` y quietas en `apagado`. En esos cuadros se mandan a la pantalla sólo los tubos y la
fila de lámparas.

## Herramientas

- `make theme-check [THEME=ambar]` (o `python -m rocola.theme check <tema>`): para cada tipo de pantalla,
  el contraste de cada texto contra lo que tiene detrás (en el TV, por luminancia), que las fuentes
  tengan «ÁÉÍÓÚÜÑ¿¡» y que existan y carguen los archivos que nombra el tema. Los tests lo corren
  sobre cada tema incluido.
- `make theme-assets`: pasa cada `src/<ruta>.svg` de cada tema a `<ruta>.png`, en un contenedor de
  Podman. Los PNG se commitean.
- `make theme-shots THEME=ambar`: una captura de cada pantalla en cada tipo de pantalla, en
  `out/shots/<tema>/`, con música de mentira (`app/tools/fake-mpd.py`): la biblioteca con varios
  artistas y, en `<tipo>-songs.png`, con uno solo, para ver las tarjetas de canción.

## Cambiar de tema

El tema activo se elige con `theme` en `/etc/rocola/rocola.toml` (o con la variable
`ROCOLA_THEME`), con el nombre de una carpeta de `themes/`. Se pueden tener varios temas y elegir
uno en cada instalación (ver [07](07-rocola-app.md)).

## Fuentes y licencias

Las tipografías incluidas tienen que tener licencia OFL o Apache. Cada una se anota en
`app/assets/fonts/README.md`.

Siguiente: [10 · Grabar el pendrive](10-flashing-usb.md).
