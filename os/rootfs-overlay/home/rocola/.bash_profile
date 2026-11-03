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
# -> no arrancaba startx. Lo enmascaramos en el build (os/Dockerfile), pero esto lo cubre igual.
case "$(tty)" in
    /dev/tty1|/dev/console)
        if [ -z "${DISPLAY:-}" ] && ! grep -qw rocola.noui /proc/cmdline; then
            # NO pasar 'vt1' explícito: startx ya detecta la vt del login y, como la
            # sesión del autologin queda activa en seat0, logind le entrega input+DRM.
            # Forzar 'vt1' provocaba "xf86OpenConsole: Switching VT failed".
            exec startx /usr/local/bin/rocola-session -- -nolisten tcp
        fi
        ;;
esac
