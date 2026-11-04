# Builder de la imagen booteable de la rocola.
# `make image` copia out/rootfs.tar (exportado del SO) a /work con `podman cp`, y
# saca de ahí rocola-i386.img: el contenedor no monta nada del repo.
# Usa grub-mkrescue (xorriso + mtools): no requiere privilegios ni loop devices,
# así funciona en WSL2/CI. Genera una ISO híbrida booteable por BIOS y UEFI x64.
FROM docker.io/library/debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        squashfs-tools \
        xorriso \
        mtools \
        dosfstools \
        grub-pc-bin \
        grub-efi-amd64-bin \
        grub-common \
        xz-utils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY build-image.sh /usr/local/bin/build-image.sh
RUN chmod +x /usr/local/bin/build-image.sh
# The folder exists in the image itself: `make image` copies the rootfs into a created, not yet started, container.
RUN mkdir -p /work
WORKDIR /work

ENTRYPOINT []
CMD ["/usr/local/bin/build-image.sh"]
