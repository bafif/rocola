# Builder de la imagen booteable de la rocola.
# Consume out/rootfs.tar (exportado del SO) y produce rocola-i386.img.
# Se corre PRIVILEGIADO (usa loop devices + grub-install).
FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        squashfs-tools \
        dosfstools \
        mtools \
        parted \
        gdisk \
        e2fsprogs \
        util-linux \
        grub-pc-bin \
        grub-efi-amd64-bin \
        grub-common \
        xz-utils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY build-image.sh /usr/local/bin/build-image.sh
COPY genimage.cfg   /usr/local/share/rocola/genimage.cfg
RUN chmod +x /usr/local/bin/build-image.sh

ENTRYPOINT []
CMD ["/usr/local/bin/build-image.sh"]
