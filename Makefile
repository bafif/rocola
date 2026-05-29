# Rocola — orquestación del build
# Uso rápido:
#   make rootfs     # construye la imagen Docker del SO (FROM i386/debian:bookworm)
#   make image      # rootfs -> out/rocola-i386.img (booteable BIOS + UEFI x64)
#   make flash DEV=/dev/sdX   # escribe la imagen al pendrive (¡destructivo!)
#   make app-run    # corre la UI de la rocola localmente (dev)
#   make clean      # borra artefactos de build

SHELL := /bin/bash
ARCH ?= i386
SUITE ?= bookworm
OS_IMAGE ?= rocola-os:$(SUITE)-$(ARCH)
OUT ?= out
IMG ?= $(OUT)/rocola-$(ARCH).img
ROOTFS_TAR ?= $(OUT)/rootfs.tar

.DEFAULT_GOAL := help

.PHONY: help
help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(OUT):
	mkdir -p $(OUT)

.PHONY: rootfs
rootfs: ## Construye la imagen Docker del SO de la rocola
	docker build --platform linux/386 -t $(OS_IMAGE) -f os/Dockerfile .

.PHONY: export
export: rootfs | $(OUT) ## Exporta el rootfs de la imagen Docker a un tar
	cid=$$(docker create --platform linux/386 $(OS_IMAGE)); \
	docker export $$cid -o $(ROOTFS_TAR); \
	docker rm $$cid

.PHONY: image
image: export ## Arma la imagen booteable rocola-i386.img
	docker build -t rocola-builder -f image/Dockerfile.builder image/
	docker run --rm --privileged \
		-v /dev:/dev \
		-v "$(CURDIR)/$(OUT)":/out \
		rocola-builder /usr/local/bin/build-image.sh /out/rootfs.tar /out/rocola-$(ARCH).img

.PHONY: flash
flash: ## Escribe la imagen al pendrive: make flash DEV=/dev/sdX
	@test -n "$(DEV)" || { echo "ERROR: pasá DEV=/dev/sdX"; exit 1; }
	@echo "ATENCIÓN: esto BORRA $(DEV) por completo."; \
	read -p "Escribí 'si' para continuar: " ok; [ "$$ok" = "si" ] || exit 1
	sudo dd if=$(IMG) of=$(DEV) bs=4M status=progress conv=fsync
	sync

.PHONY: app-run
app-run: ## Corre la UI de la rocola localmente (requiere MPD + python3-pygame)
	cd app && python3 -m rocola

.PHONY: app-deps
app-deps: ## Instala deps de desarrollo de la app (pip)
	cd app && pip install -e .

.PHONY: clean
clean: ## Borra artefactos de build
	rm -rf $(OUT)
	-docker image rm $(OS_IMAGE) rocola-builder 2>/dev/null || true
