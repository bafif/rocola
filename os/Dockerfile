# Rocola — SO base (i386, Debian bookworm)
# Construir con:  docker build --platform linux/386 -t rocola-os -f os/Dockerfile .
# (requiere binfmt/qemu para linux/386 en hosts no-i386)
#
# bookworm a propósito: Debian 13 (trixie) discontinuó kernel/booteable i386.
FROM i386/debian:bookworm

LABEL org.opencontainers.image.title="rocola-os" \
      org.opencontainers.image.description="SO de la rocola (Debian i386) — live + instalable" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=es_AR.UTF-8 \
    LC_ALL=es_AR.UTF-8

# --- Paquetes -------------------------------------------------------------
COPY os/packages.list /tmp/packages.list
RUN apt-get update \
 && sed -e 's/#.*//' -e '/^[[:space:]]*$/d' /tmp/packages.list | xargs apt-get install -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* /tmp/packages.list

# --- Locale + zona horaria (Argentina) ------------------------------------
RUN sed -i 's/# es_AR.UTF-8/es_AR.UTF-8/' /etc/locale.gen \
 && locale-gen \
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

# --- Habilitar servicios + autologin --------------------------------------
RUN set -eux; \
    systemctl enable mpd.service || true; \
    systemctl enable rocola-display-setup.service || true; \
    systemctl enable rocola.service || true; \
    systemctl set-default multi-user.target

# --- initramfs con live-boot ---------------------------------------------
# Regenerar el initrd para incluir los hooks de live-boot (arranque desde squashfs).
RUN update-initramfs -u || true

# La imagen no "corre" como contenedor normal: su filesystem es el rootfs del SO.
CMD ["/bin/bash"]
