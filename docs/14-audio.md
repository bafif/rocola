# 14 · Audio: salida, PipeWire y Bluetooth

La idea es que suene en la mayor variedad posible de PCs viejas: salida analógica (line-out o
auriculares de la placa madre), HDMI o DisplayPort, USB (un DAC o auriculares) y Bluetooth
(parlante o auricular A2DP). Y que la salida se pueda ver y elegir desde la UI con los controles
de arcade.

## El problema

Una placa de audio «por defecto» no alcanza:

- En una PC con varias placas (la de la placa madre, HDMI, USB), el `default` de ALSA apunta a
  una sola, normalmente la de la placa madre. Si conectás auriculares USB, el audio sale por
  donde no estás escuchando.
- Muchas placas arrancan con el mixer de hardware en mute o en 0, y no se escucha nada aunque la
  placa sea la correcta.
- El Bluetooth no es una placa ALSA: necesita un servidor de audio que lo enrute.

## Cómo lo resolví

El audio pasa por **PipeWire** (con WirePlumber y `pipewire-pulse`), que corre en la sesión
gráfica del usuario `rocola`. **MPD**, el motor de la rocola, corre en esa misma sesión y no como
servicio del sistema, para compartir ese PipeWire, y reproduce en el sink por defecto. Elegir la
salida es elegir el sink por defecto de PipeWire, y el mismo mecanismo sirve para la analógica,
HDMI, USB y Bluetooth.

```
sesión de rocola (startx → rocola-session)
   ├─ desmutea el mixer de hardware (amixer, red de seguridad)
   ├─ levanta PipeWire + WirePlumber + pipewire-pulse
   ├─ rocola-audio-default → elige el sink por defecto (heurística / audio.conf)
   └─ MPD (type "pulse") ─→ pipewire-pulse ─→ sink por defecto
                                                  ├─ analógica / HDMI / USB (ALSA)
                                                  └─ Bluetooth A2DP (libspa-bluetooth)
```

### Elección del sink por defecto

Lo hace `rocola-audio-default` al arrancar (dentro de la sesión), leyendo
`/etc/rocola/audio.conf`:

- `OUTPUT=auto` (el valor por defecto) usa este orden: Bluetooth conectado, USB, analógica,
  HDMI y, si no hay ninguna, el primer sink. USB va antes que la analógica de la placa madre
  porque la analógica siempre existe aunque no haya nada enchufado; con la analógica primero,
  unos auriculares USB quedarían mudos al arrancar.
- `OUTPUT=<texto>` fija el primer sink cuyo nombre contenga `<texto>` (por ejemplo `usb`,
  `analog`, `hdmi`, `bluez`, o un nombre exacto de `pactl list short sinks`).
- `VOLUME=80` es el volumen inicial del sink elegido.

La salida que elegís desde el menú de la app se guarda en `audio.conf` (`OUTPUT=<sink>`), así que
sobrevive a un reinicio.

## En la UI

En el menú (tecla **F10** o el botón de menú):

- **Salida de audio** lista los sinks de PipeWire y marca el actual con `●`. Con las flechas te
  movés, y Enter fija la salida y reproduce un tono de prueba para confirmarlo de oído. Al final
  está «+ Emparejar Bluetooth…».
- **Información del sistema** muestra la salida de audio activa, el driver de audio
  (`/proc/asound/modules`) y el de video, la resolución, la IP, el kernel y algunas cosas más.
  Sirve para diagnosticar y para saber a qué IP conectarse por SSH.

## Bluetooth

- `bluez` trae el demonio (`bluetooth.service`) y `bluetoothctl`; el plugin
  `libspa-0.2-bluetooth` hace que un parlante o auricular conectado aparezca como un sink de
  PipeWire. `/etc/bluetooth/main.conf` enciende el adaptador al arrancar (`AutoEnable=true`) y los
  dispositivos marcados como *trusted* se reconectan solos.
- Para emparejar: menú, «Salida de audio», «Emparejar Bluetooth…». Se abre una pantalla dentro de
  la app (con flechas y Enter) que busca dispositivos, los lista y hace `pair`, `trust` y
  `connect` con un agente «just works», sin PIN. Funciona como usuario `rocola`, sin root, gracias
  a la política de D-Bus del grupo `bluetooth`. Al volver, el sink Bluetooth aparece en el
  selector: elegilo y probá el tono.
- Por SSH o desde la consola está `rocola-bt-pair` (una TUI con whiptail), que hace el mismo
  emparejamiento sin la interfaz gráfica.
- Ojo con el hardware: muchas PCs de escritorio viejas no traen Bluetooth y hace falta un dongle
  USB (su firmware suele estar en los paquetes `firmware-*` que ya vienen en la imagen).

## Problemas comunes

PipeWire y MPD viven en la sesión de `rocola` (tty1). Por SSH hay que apuntar a esa sesión y no a
la del SSH:

```bash
U=$(id -u rocola)
RUN="sudo -u rocola env XDG_RUNTIME_DIR=/run/user/$U"

$RUN pactl info                      # ¿PipeWire responde?
$RUN pactl list short sinks          # sinks disponibles (nombres estables)
$RUN pactl get-default-sink          # salida actual
$RUN pactl set-default-sink NOMBRE   # cambiar salida a mano
$RUN paplay --device=NOMBRE "/music/01 - Tono de prueba La (440 Hz).wav"
$RUN wpctl status                    # árbol de PipeWire/WirePlumber
$RUN rocola-audio-default            # re-aplicar la heurística / audio.conf

bluetoothctl                         # scan on / pair / trust / connect
amixer -c 0 scontrols                # mixer de hardware (mute/volumen) de la placa 0
mpc status; mpc outputs              # estado de MPD
```

Si no se escucha nada, en este orden:

1. ¿Responde `pactl info`? Si no, PipeWire no levantó en la sesión.
2. ¿El sink por defecto es el correcto? (`get-default-sink`). Cambialo y probá el tono.
3. ¿El mixer de hardware está en mute? `amixer -c N` y después `sset Master/Speaker/Headphone
   unmute 80%` (la sesión ya lo intenta al arrancar, por las dudas).
4. Si es Bluetooth, ¿hay adaptador? (`bluetoothctl list`). Sin dongle no hay Bluetooth.

Siguiente: [01 · Visión general](01-overview.md) · Volver a la
[documentación](../README.es.md#documentación).
