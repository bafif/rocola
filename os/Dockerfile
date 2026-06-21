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

# --- Habilitar non-free-firmware ------------------------------------------
# El firmware de GPU (amdgpu/i915/nouveau) y de red vive en el componente
# 'non-free-firmware' de bookworm (deb822: /etc/apt/sources.list.d/debian.sources).
# Sin esto, amdgpu NO inicializa en hardware moderno ("amdgpu requires firmware
# installed") -> sin KMS -> Xorg no arranca -> la UI no levanta. Agregamos también
# contrib/non-free por si hiciera falta firmware adicional.
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i -E 's/^Components:.*/Components: main contrib non-free non-free-firmware/' \
            /etc/apt/sources.list.d/debian.sources; \
    else \
        printf 'deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware\n' \
            > /etc/apt/sources.list; \
    fi

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
 && usermod -aG audio,video,input,plugdev,tty,bluetooth rocola \
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
    install -d -o rocola -g rocola /music; \
    install -d -o rocola -g rocola /var/lib/rocola-mpd /var/lib/rocola-mpd/playlists; \
    chown rocola:rocola /home/rocola/.bash_profile; \
    chown rocola:rocola /etc/rocola/audio.conf

# --- Dependencias Python de la app (pygame-ce vía apt) --------------------
# (python3-pygame y demás vienen en packages.list; instalá extras acá si hiciera falta)

# --- Habilitar servicios + target por defecto -----------------------------
# En un build de Docker no hay systemd corriendo, así que `systemctl` puede
# fallar. Creamos los symlinks de "enable" y "set-default" a mano: es
# determinista y equivalente a lo que hace systemctl offline.
RUN set -eux; \
    ln -sf /lib/systemd/system/multi-user.target /etc/systemd/system/default.target; \
    mkdir -p /etc/systemd/system/multi-user.target.wants; \
    for unit in rocola-hostname.service rocola-display-setup.service rocola-selftest.service \
                rocola-music-import.service rocola-ssh.service systemd-networkd.service \
                bluetooth.service; do \
        if   [ -e "/etc/systemd/system/$unit" ]; then src="/etc/systemd/system/$unit"; \
        elif [ -e "/lib/systemd/system/$unit"  ]; then src="/lib/systemd/system/$unit"; \
        else echo "WARN: unit $unit no encontrada, se omite"; continue; fi; \
        ln -sf "$src" "/etc/systemd/system/multi-user.target.wants/$unit"; \
    done

# --- Audio: MPD fuera del sistema, PipeWire por-usuario -------------------
# MPD ya NO es servicio del sistema: lo lanza la sesión de 'rocola' (rocola-session)
# para compartir el PipeWire de la sesión gráfica. Enmascaramos service+socket para
# que la socket-activation de Debian no levante un segundo MPD peleando por :6600.
# PipeWire/WirePlumber/pipewire-pulse corren por-usuario: los habilitamos a nivel
# global (best-effort; rocola-session igual los arranca explícitamente con fallback).
RUN set -eux; \
    ln -sf /dev/null /etc/systemd/system/mpd.service; \
    ln -sf /dev/null /etc/systemd/system/mpd.socket; \
    rm -f /etc/systemd/system/multi-user.target.wants/mpd.service; \
    systemctl --global enable wireplumber.service pipewire.socket pipewire-pulse.socket 2>/dev/null || true

# --- SSH: instalado pero APAGADO por defecto (opt-in con rocola.ssh) -------
# El Release es público: sshd NO debe arrancar salvo que se pida explícitamente
# (entrada de GRUB "Troubleshooting (SSH)"). rocola-ssh.service lo prende sólo si
# 'rocola.ssh' está en la cmdline. Acá: (1) deshabilitamos el autostart que mete
# el postinst de openssh, (2) borramos las host keys fijas (se regeneran en RAM
# al habilitar SSH, así no se shippean claves compartidas), (3) fijamos permisos
# de la authorized_keys de root (StrictModes de sshd).
RUN set -eux; \
    rm -f /etc/systemd/system/multi-user.target.wants/ssh.service \
          /etc/systemd/system/sshd.service; \
    rm -f /etc/ssh/ssh_host_*; \
    if [ -f /root/.ssh/authorized_keys ]; then \
        chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys; \
        chown -R root:root /root/.ssh; \
    fi

# --- initramfs con live-boot ---------------------------------------------
# Regenerar el initrd para incluir los hooks de live-boot (arranque desde squashfs).
RUN update-initramfs -u || true

# La imagen no "corre" como contenedor normal: su filesystem es el rootfs del SO.
CMD ["/bin/bash"]
