# Rocola — orquestación del build
# Uso rápido:
#   make rootfs     # construye la imagen de contenedor del SO (Podman, FROM i386/debian:bookworm)
#   make image      # rootfs -> out/rocola-i386.img (booteable BIOS + UEFI x64)
#   make release VERSION=vX.Y.Z   # empaqueta el .iso + checksum para subir a un Release
#   make flash DEV=/dev/sdX   # escribe la imagen al pendrive (¡destructivo!)
#   make app-run    # corre la UI de la rocola localmente (dev)
#   make app-test   # tests de la app (pytest, con uv)
#   make app-lint   # lint de la app (ruff, con uv)
#   make os-test    # tests de los scripts del SO (sin root)
#   make clean      # borra artefactos de build

SHELL := /bin/bash
ARCH ?= i386
SUITE ?= bookworm
OS_IMAGE ?= rocola-os:$(SUITE)-$(ARCH)
OUT ?= out
IMG ?= $(OUT)/rocola-$(ARCH).img
ROOTFS_TAR ?= $(OUT)/rootfs.tar
RELEASE_DIR ?= $(OUT)/release

.DEFAULT_GOAL := help

.PHONY: help
help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(OUT):
	mkdir -p $(OUT)

.PHONY: rootfs
rootfs: ## Construye la imagen de contenedor del SO de la rocola (Podman)
	podman build --platform linux/386 -t $(OS_IMAGE) -f os/Containerfile .

# Asegura que la imagen del SO exista, SIN forzar un rebuild en cada `make image`.
# (Si `export`/`image` dependieran del target `rootfs`, se reconstruiría la imagen
#  cada vez. Con esto sólo se construye si falta; para forzar: `make rootfs`.)
.PHONY: ensure-os
ensure-os: | $(OUT)
	@if ! podman image exists $(OS_IMAGE); then \
		echo "Imagen $(OS_IMAGE) no existe; construyendo…"; $(MAKE) rootfs; \
	else echo "Usando $(OS_IMAGE) existente (usá 'make rootfs' para reconstruir)"; fi

# Exporta a un .tmp y lo renombra solo si salió bien: si el export falla, make se corta
# en vez de seguir con el rootfs.tar de un build anterior (o con uno a medias).
.PHONY: export
export: ensure-os ## Exporta el rootfs de la imagen del SO a un tar
	cid=$$(podman create --platform linux/386 $(OS_IMAGE)) && \
	trap 'podman rm -f $$cid >/dev/null; rm -f $(ROOTFS_TAR).tmp' EXIT && \
	podman export $$cid -o $(ROOTFS_TAR).tmp && \
	mv -f $(ROOTFS_TAR).tmp $(ROOTFS_TAR)

# El builder no monta nada del repo: el rootfs entra con `podman cp` y la imagen sale igual, así ningún
# contenedor escribe en el repo.
.PHONY: image
image: export ## Arma la imagen booteable rocola-i386.img (híbrida BIOS+UEFI)
	podman build -t rocola-builder -f image/Containerfile.builder image/
	cid=$$(podman create rocola-builder /usr/local/bin/build-image.sh /work/rootfs.tar /work/rocola-$(ARCH).img); \
	trap 'podman rm -f $$cid >/dev/null' EXIT; \
	podman cp $(ROOTFS_TAR) $$cid:/work/rootfs.tar && \
	podman start -a $$cid && \
	podman cp $$cid:/work/rocola-$(ARCH).img $(OUT)/rocola-$(ARCH).img

.PHONY: release
release: ## Empaqueta el .iso + checksum para subir a un Release: make release VERSION=vX.Y.Z
	@test -n "$(VERSION)" || { echo "ERROR: pasá VERSION=vX.Y.Z"; exit 1; }
	@test -f "$(IMG)" || { echo "ERROR: no existe $(IMG); corré 'make image' primero"; exit 1; }
	image/package-release.sh "$(IMG)" "$(VERSION)" "$(RELEASE_DIR)"

.PHONY: flash
flash: ## Escribe la imagen al pendrive: make flash DEV=/dev/sdX
	@test -n "$(DEV)" || { echo "ERROR: pasá DEV=/dev/sdX"; exit 1; }
	@echo "ATENCIÓN: esto BORRA $(DEV) por completo."; \
	read -p "Escribí 'si' para continuar: " ok; [ "$$ok" = "si" ] || exit 1
	sudo dd if=$(IMG) of=$(DEV) bs=4M status=progress conv=fsync
	sync

.PHONY: app-run
app-run: ## Corre la UI de la rocola localmente en ventana (requiere un MPD local)
	cd app && ROCOLA_WINDOWED=$${ROCOLA_WINDOWED:-1} uv run python -m rocola

.PHONY: app-deps
app-deps: ## Crea el entorno de desarrollo de la app (uv: pygame-ce, pytest, ruff)
	cd app && uv sync

.PHONY: app-test
app-test: ## Corre los tests de la app (pytest, sin display ni audio)
	cd app && uv run pytest

.PHONY: app-lint
app-lint: ## Lint y formato de la app (ruff)
	cd app && uv run ruff check . && uv run ruff format --check .

.PHONY: os-test
os-test: ## Tests de los scripts del SO que corren sin root (import de música)
	bash os/tests/music-import.sh

.PHONY: clean
clean: ## Borra artefactos de build
	rm -rf $(OUT)
	-podman image rm $(OS_IMAGE) rocola-builder 2>/dev/null || true
