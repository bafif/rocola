# 08 · Gestión de música

Dos vías para cargar canciones, combinables: **precargada en la imagen** y **import desde un 2º USB**.
La biblioteca vive en una **partición de datos persistente** (`/music`).

## Dónde vive la música

| Contexto | Ruta | Persiste |
|----------|------|----------|
| Live (pendrive) | música precargada incluida en el squashfs (solo lectura) | n/a |
| Instalado | partición **`/music`** (ext4, separada de ROOT) | **sí** |

MPD apunta su `music_directory` a `/music`. Separarla de ROOT permite **reinstalar/actualizar el SO
sin perder las canciones**.

## Vía 1 — Precargada en la imagen

Antes de construir, poné carpetas de música en:

```
os/rootfs-overlay/opt/rocola/music/
```

(esa ruta se ignora en git salvo `.gitkeep`, para no versionar audio pesado). En el primer arranque,
`rocola-music-import` copia/enlaza esa música a `/music` y MPD la escanea. Útil para entregar el
pendrive "con música puesta".

## Vía 2 — Import desde un 2º USB

1. Enchufá un pendrive con tus canciones (idealmente en una carpeta, p. ej. `Música/` o en la raíz).
2. La rocola **detecta** el USB nuevo y ofrece importarlo (o se dispara desde el menú).
3. `rocola-music-import` copia las carpetas a `/music`, evitando duplicados.
4. Dispara un **re-scan** de MPD (`mpc update` / comando `update`) y la biblioteca aparece en la UI.

Formatos: lo que soporte MPD (MP3, FLAC, OGG, etc.). Las **carátulas** se toman de tags embebidos o
de `cover.jpg`/`folder.jpg` en la carpeta del álbum.

```
2º USB (Música/)
   └─ rocola-music-import ──► /music/… ──► mpc update ──► UI actualizada
```

## Organización recomendada

```
/music/
  Artista/
    Álbum/
      01 - Tema.flac
      cover.jpg
```

No es obligatorio: MPD también navega por carpetas sueltas. La UI puede mostrar por carpeta o por tags.

## Re-escanear manualmente

Desde el menú de la rocola ("Actualizar biblioteca") o, por consola, `mpc update`.

Siguiente: [09 · Branding](09-branding-theming.md).
