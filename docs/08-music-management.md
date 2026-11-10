# 08 · Gestión de música

Dos vías para cargar canciones, combinables: **precargada en la imagen** y **import desde un 2º USB**.
La biblioteca vive en una **partición de datos persistente** (`/music`).

## Dónde vive la música

| Contexto | Ruta | Persiste |
|----------|------|----------|
| Live (pendrive) | `/music` es la carpeta precargada del squashfs, montada encima; lo importado queda en RAM | no (el instalador lo lleva al disco) |
| Instalado | partición **`/music`** (ext4, separada de ROOT) | **sí** |

MPD apunta su `music_directory` a `/music`. Separarla de ROOT permite **reinstalar/actualizar el SO
sin perder las canciones**.

## Vía 1 — Precargada en la imagen

Antes de construir, poné carpetas de música en:

```
os/rootfs-overlay/opt/rocola/music/
```

(esa ruta se ignora en git salvo `.gitkeep`, para no versionar audio pesado). En el pendrive,
`rocola-music-import` monta esa carpeta encima de `/music` en vez de copiarla: el sistema en vivo
corre en RAM y una copia ocupaba la biblioteca dos veces en memoria. Al instalar, el instalador la
copia a la partición `/music` del disco (con lo que se haya importado en la sesión en vivo) si esa
partición no tiene música, así no ocupa los 12 GB del sistema. MPD la escanea al arrancar. Útil
para entregar el pendrive "con música puesta".

## Vía 2 — Import desde un 2º USB

1. Enchufá un pendrive con tus canciones (en la raíz o en carpetas, p. ej. `Música/Artista/Álbum/`),
   con la rocola andando o antes de prenderla. Sirven FAT32, exFAT, NTFS y ext2/3/4.
2. udev lo detecta (`/etc/udev/rules.d/90-rocola-usb-music.rules`) y arranca
   `rocola-usb-music@<dispositivo>.service`, que monta cada partición **solo lectura** en
   `/run/rocola-usb/`. No hay nada que confirmar: el pendrive nunca se modifica.
3. `rocola-music-import` copia el audio (mp3, flac, ogg, m4a, wav, opus, aac, sin importar
   mayúsculas: `TEMA01.MP3` también entra) y las carátulas de carpeta (`cover.*`, `folder.*`) a
   `/music`, sin pisar lo que ya está, y pide un re-escaneo a MPD. Otras imágenes (las fotos de
   un pendrive) y las carpetas sin audio no se copian.
4. La biblioteca de la UI se recarga sola cuando MPD termina de escanear.
5. El pendrive queda desmontado: se puede sacar cuando termina el servicio
   (`journalctl -u 'rocola-usb-music@*'` muestra el «done»).

Lo que ya está montado (el propio pendrive de la rocola, o un disco USB donde se instaló el sistema)
no se toca. En el modo en vivo `/music` vive en RAM: lo importado se pierde al apagar; en el sistema
instalado queda en la partición de música.

```
2º USB ──udev──► rocola-usb-music@sdX1 ──mount ro──► rocola-music-import ──► /music/… ──► MPD ──► UI
```

## Organización recomendada

```
/music/
  Artista/
    Álbum/
      01 - Tema.flac
      cover.jpg
```

La portada de un álbum es el `cover.jpg` (o `.png`/`.webp`) de su carpeta, o la imagen embebida
en los archivos. MPD solo encuentra `cover.*` escrito así; el import desde USB le agrega un
`cover.<ext>` (enlace duro, sin ocupar lugar) a cada carpeta que trae solo `Folder.jpg`,
`COVER.JPG` o parecidos.

No es obligatorio: MPD indexa cualquier carpeta. La UI agrupa por los **tags** (artista, álbum,
número de pista), no por las carpetas; un tema sin tags aparece con el nombre del archivo, en
«(sin artista)». Ver [07](07-rocola-app.md).

## Re-escanear manualmente

Desde el menú de la rocola ("Actualizar biblioteca") o, por consola, `mpc update`.

Siguiente: [09 · Branding](09-branding-theming.md).
