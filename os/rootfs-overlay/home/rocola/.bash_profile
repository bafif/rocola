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

if [ "$(tty)" = "/dev/tty1" ] && [ -z "${DISPLAY:-}" ] && ! grep -qw rocola.noui /proc/cmdline; then
    # NO pasar 'vt1' explícito: startx ya detecta la vt del login (tty1) y, como la
    # sesión del autologin queda activa en seat0, logind le entrega input+DRM. Forzar
    # 'vt1' provocaba "xf86OpenConsole: Switching VT failed". Sin él, X usa la vt
    # actual y todo queda en la misma sesión activa.
    exec startx /usr/local/bin/rocola-session -- -nolisten tcp
fi
