# ~/.bash_profile del usuario rocola.
#
# Autostart de la rocola: el autologin de getty en tty1 deja una sesión de login
# ACTIVA en seat0; acá lanzamos la UI con `startx` (X + la app como cliente único),
# heredando esa sesión activa para que Xorg consiga el DRM de logind sin "paused fd".
# Si X o la app terminan, el login se cierra, getty re-autologuea y la UI vuelve a
# arrancar sola (comportamiento kiosko).
#
# Flags de cmdline:
#   rocola.noui  -> NO arrancar la UI (caer a consola; entrada de recuperación de GRUB).

# Login interactivo normal (otra tty, o SSH): cargar la config de bash habitual.
[ -f ~/.bashrc ] && . ~/.bashrc

# Cookie X en tmpfs — FUERA del bloque de autostart, a propósito: el home de 'rocola'
# vive en overlayfs (el live corre en RAM) y el lock link-based de xauth sobre
# ~/.Xauthority NO funciona en overlayfs -> falla con "timeout in locking authority
# file" tras ~20 s -> X sin cookie -> "Authorization required, but no authorization
# protocol specified" -> pantalla negra. /run/user/$UID es tmpfs (lo crea pam_systemd),
# donde el file-locking funciona. Al estar acá (y no dentro del if) cubre TODO startx:
# el del autologin Y uno tipeado a mano en consola. Verificado por SSH. Ver docs/03.
export XAUTHORITY="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/Xauthority"

# Autostart de la UI. Aceptamos tty1 O console: 'console-getty' (el getty de /dev/console
# que systemd-getty-generator activa aunque la consola sea una VT normal) puede ganarle
# la consola física a getty@tty1 y dejar el login en /dev/console, donde $(tty) != tty1
# -> no arrancaba startx. Lo enmascaramos en el build (os/Containerfile), pero esto lo cubre igual.
case "$(tty)" in
    /dev/tty1|/dev/console)
        if [ -z "${DISPLAY:-}" ] && ! grep -qw rocola.noui /proc/cmdline; then
            # Tope de reintentos: si la UI se cierra 5 veces en 2 minutos no se relanza
            # más y tty1 queda en esta consola con el motivo a la vista. Sin tope, una UI
            # que no puede arrancar (driver, Xorg) entraba en un bucle sin fin que tapaba
            # la pantalla. /tmp se vacía en cada arranque.
            starts=/tmp/rocola-ui-starts
            now=$(date +%s)
            recent=$(awk -v now="$now" 'now - $1 < 120' "$starts" 2>/dev/null | wc -l)
            if [ "$recent" -ge 5 ]; then
                echo
                if [ "$(rocola-lang 2>/dev/null)" = es ]; then
                    echo "La interfaz de la rocola se cerró 5 veces en 2 minutos: no se vuelve a abrir sola."
                    echo "  Por qué:      journalctl -b | grep -iE 'startx|Xorg|rocola-session'"
                    echo "                less /var/log/Xorg.0.log  (o ~/.local/share/xorg/Xorg.0.log)"
                    echo "  Reintentar:   rm $starts; exit"
                else
                    echo "The jukebox screen closed 5 times in 2 minutes: it will not open again on its own."
                    echo "  Why:          journalctl -b | grep -iE 'startx|Xorg|rocola-session'"
                    echo "                less /var/log/Xorg.0.log  (or ~/.local/share/xorg/Xorg.0.log)"
                    echo "  Try again:    rm $starts; exit"
                fi
                echo
            else
                { tail -n 9 "$starts" 2>/dev/null; echo "$now"; } >"$starts.new" \
                    && mv -f "$starts.new" "$starts"
                # NO pasar 'vt1' explícito: startx ya detecta la vt del login y, como la
                # sesión del autologin queda activa en seat0, logind le entrega input+DRM.
                # Forzar 'vt1' provocaba "xf86OpenConsole: Switching VT failed".
                exec startx /usr/local/bin/rocola-session -- -nolisten tcp
            fi
        fi
        ;;
esac
