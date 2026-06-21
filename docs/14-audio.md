# 14 · Audio: salida, PipeWire y Bluetooth

El objetivo es que **suene** en la mayor variedad realista de PCs viejas: salida
**analógica** (line-out/auriculares onboard), **HDMI/DisplayPort**, **USB** (DAC o
auriculares) y **Bluetooth** (parlante/auricular A2DP). Y que el usuario pueda **ver y
elegir** la salida desde la UI con los controles de arcade.

## El problema

Una placa de audio "default" no alcanza:

- En una PC con varias placas (onboard + HDMI + USB), el `default` de ALSA apunta a
  **una sola** (típicamente la onboard). Si conectás **auriculares USB**, el audio
  sale por donde no escuchás.
- Muchas placas arrancan con el mixer de hardware en **mute** o en 0 → silencio
  aunque la placa sea la correcta.
- El Bluetooth no es "una placa ALSA": necesita un servidor de audio que lo enrute.

## Estrategia

El audio rutea por **PipeWire** (+ WirePlumber + `pipewire-pulse`), que corre **en la
sesión gráfica** del usuario `rocola`. **MPD** (el motor de la rocola) también corre
en esa sesión —no como servicio del sistema— para compartir ese PipeWire, y reproduce
al **sink por defecto**. "Elegir salida" = elegir el sink por defecto de PipeWire; el
mismo mecanismo cubre analógica, HDMI, USB y Bluetooth.

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

- `OUTPUT=auto` (default) → heurística **Bluetooth conectado → USB → analógica →
  HDMI → primer sink**. Se prioriza USB sobre la analógica onboard porque la analógica
  "siempre existe" aunque no haya nada enchufado: con "analógica primero" unos
  auriculares USB quedarían mudos al arrancar.
- `OUTPUT=<texto>` → fija el primer sink cuyo **nombre contenga** `<texto>` (ej.:
  `usb`, `analog`, `hdmi`, `bluez`, o un nombre exacto de `pactl list short sinks`).
- `VOLUME=80` → volumen inicial del sink elegido.

Cuando elegís una salida desde el menú de la app, se **persiste** en `audio.conf`
(`OUTPUT=<sink>`), así sobrevive al reinicio.

## En la UI

Menú (tecla **F10** / botón de menú):

- **Salida de audio** → lista los sinks de PipeWire (marca el actual con `●`), flechas
  para moverse, **Enter** fija la salida y **reproduce un tono de prueba** para
  confirmar al oído. Incluye **"+ Emparejar Bluetooth…"**.
- **Información del sistema** → salida de audio activa, driver de audio
  (`/proc/asound/modules`) y de video, resolución, IP, kernel, etc. Útil para
  diagnosticar (y para saber a qué IP conectarse por SSH).

## Bluetooth

- `bluez` provee el demonio (`bluetooth.service`) y `bluetoothctl`; el plugin
  `libspa-0.2-bluetooth` hace que un parlante/auricular conectado aparezca como **sink
  de PipeWire**. `/etc/bluetooth/main.conf` enciende el adaptador al boot
  (`AutoEnable=true`) y los dispositivos *trusted* reconectan solos.
- **Emparejar**: menú → "Salida de audio" → "Emparejar Bluetooth…" abre una pantalla
  **dentro de la app** (controles de arcade: flechas + Enter) que escanea, lista los
  dispositivos y hace `pair`/`trust`/`connect` con un agente "just works" (sin PIN).
  Funciona como usuario `rocola` (sin root) gracias a la política D-Bus del grupo
  `bluetooth`. Al volver, el sink BT aparece en el selector; elegilo y probá el tono.
- También existe `rocola-bt-pair` (TUI whiptail) como **alternativa por SSH/consola**
  (mismo flujo de emparejamiento, sin la UI gráfica).
- **Salvedad de hardware**: muchas PCs de escritorio viejas **no traen Bluetooth**.
  Hace falta un **dongle USB** (su firmware suele venir en los `firmware-*` incluidos).

## Troubleshooting

PipeWire y MPD viven en la **sesión de `rocola`** (tty1). Por SSH hay que apuntar a esa
sesión (no a la del SSH):

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

Cosas a chequear si **no se escucha**:

1. ¿`pactl info` responde? Si no, PipeWire no levantó en la sesión.
2. ¿El sink correcto es el default? (`get-default-sink`). Cambialo y probá el tono.
3. ¿El mixer de hardware está muteado? `amixer -c N` → `sset Master/Speaker/Headphone
   unmute 80%` (la sesión ya intenta esto como red de seguridad).
4. Bluetooth: ¿hay adaptador? (`bluetoothctl list`). Sin dongle no hay BT.

Siguiente: [01 · Visión general](01-overview.md) · Volver a la
[documentación](../README.md#-documentación).
