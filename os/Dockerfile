# Rocola — SO base (i386, Debian bookworm)
# Construir con:  docker build --platform linux/386 -t rocola-os -f os/Dockerfile .
# (requiere binfmt/qemu para linux/386 en hosts no-i386)
#
# bookworm a propósito: Debian 13 (trixie) discontinuó kernel/booteable i386.
FROM i386/debian:bookworm

LABEL org.opencontainers.image.title="rocola-os" \
      org.opencontainers.image.description="SO de la rocola (Debian i386) — live + instalable" \
      org.opencontainers.image.licenses="MIT"

# Durante el build dejamos el locale en C (el locale es_AR todavía no está
# generado; setear LC_ALL acá sólo produce warnings de perl). El locale real se
# fija más abajo, después de locale-gen, vía /etc/default/locale.
ENV DEBIAN_FRONTEND=noninteractive

# --- Paquetes -------------------------------------------------------------
COPY os/packages.list /tmp/packages.list
# Reintentos a nivel apt (Acquire::Retries) + reintento del update y del install:
# deb.debian.org a veces corta conexiones a mitad de descarga. Sin esto, un blip
# de red rompe todo el build de ~10 min. Con --fix-missing reanuda lo que falte.
RUN set -eux; \
    echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries; \
    for i in 1 2 3; do apt-get update && break || { echo "apt update retry $i"; sleep 5; }; done; \
    PKGS="$(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' /tmp/packages.list)"; \
    ok=0; \
    for i in 1 2 3 4 5; do \
        if apt-get install -y --no-install-recommends --fix-missing $PKGS; then ok=1; break; fi; \
        echo "apt install retry $i (blip de red); reintentando…"; sleep 8; apt-get update || true; \
    done; \
    [ "$ok" = 1 ]; \
    rm -rf /var/lib/apt/lists/* /tmp/packages.list

# --- Locale + zona horaria (Argentina) ------------------------------------
RUN sed -i 's/# es_AR.UTF-8/es_AR.UTF-8/' /etc/locale.gen \
 && locale-gen \
 && printf 'LANG=es_AR.UTF-8\n' > /etc/default/locale \
 && ln -sf /usr/share/zoneinfo/America/Argentina/Buenos_Aires /etc/localtime

# --- Usuario de la rocola -------------------------------------------------
RUN useradd -m -s /bin/bash rocola \
 && usermod -aG audio,video,input,plugdev,tty rocola \
 && passwd -d rocola

# --- App, instalador y subsistema de video --------------------------------
COPY app/        /opt/rocola/
COPY installer/  /opt/rocola-installer/
COPY display/    /opt/rocola-display/

# --- Overlay de configuración del SO --------------------------------------
COPY os/rootfs-overlay/ /

# --- Permisos de ejecutables y enlaces ------------------------------------
RUN set -eux; \
    chmod +x /usr/local/bin/* /opt/rocola-installer/rocola-install /opt/rocola-display/rocola-display-setup 2>/dev/null || true; \
    ln -sf /opt/rocola-installer/rocola-install   /usr/local/bin/rocola-install; \
    ln -sf /opt/rocola-display/rocola-display-setup /usr/local/bin/rocola-display-setup; \
    install -d -o rocola -g rocola /music

# --- Dependencias Python de la app (pygame-ce vía apt) --------------------
# (python3-pygame y demás vienen en packages.list; instalá extras acá si hiciera falta)

# --- Habilitar servicios + target por defecto -----------------------------
# En un build de Docker no hay systemd corriendo, así que `systemctl` puede
# fallar. Creamos los symlinks de "enable" y "set-default" a mano: es
# determinista y equivalente a lo que hace systemctl offline.
RUN set -eux; \
    ln -sf /lib/systemd/system/multi-user.target /etc/systemd/system/default.target; \
    mkdir -p /etc/systemd/system/multi-user.target.wants; \
    for unit in mpd.service rocola-display-setup.service rocola.service rocola-selftest.service; do \
        if   [ -e "/etc/systemd/system/$unit" ]; then src="/etc/systemd/system/$unit"; \
        elif [ -e "/lib/systemd/system/$unit"  ]; then src="/lib/systemd/system/$unit"; \
        else echo "WARN: unit $unit no encontrada, se omite"; continue; fi; \
        ln -sf "$src" "/etc/systemd/system/multi-user.target.wants/$unit"; \
    done

# --- initramfs con live-boot ---------------------------------------------
# Regenerar el initrd para incluir los hooks de live-boot (arranque desde squashfs).
RUN update-initramfs -u || true

# La imagen no "corre" como contenedor normal: su filesystem es el rootfs del SO.
CMD ["/bin/bash"]
