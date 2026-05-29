# Builder de la imagen booteable de la rocola.
# Consume out/rootfs.tar (exportado del SO) y produce rocola-i386.img.
# Usa grub-mkrescue (xorriso + mtools): NO requiere privilegios ni loop devices,
# así funciona en WSL2/CI. Genera una ISO híbrida booteable por BIOS y UEFI x64.
FROM debian:bookworm

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

ENTRYPOINT []
CMD ["/usr/local/bin/build-image.sh"]
