# 13 · Grabar con Rufus (Windows)

[Rufus](https://rufus.ie) es la forma más común de grabar el `.iso` a un pendrive en Windows. La
imagen de la rocola es una **ISO 9660 híbrida (isohybrid)**: ya trae MBR protectivo + GPT,
`grub2-mbr` para BIOS, partición EFI (`/efi.img`) para UEFI x64 y El Torito con *boot-info-table*.
O sea: **el medio booteable está completo dentro del archivo**. Lo único que hay que hacer es
copiarlo tal cual.

Por eso Rufus pregunta menos de lo que parece: la respuesta corta es **grabar en modo DD**, y en
ese modo **todas las demás opciones se deshabilitan y se ignoran**.

## TL;DR

1. **Device** → tu pendrive (¡el correcto! se borra entero).
2. **Boot selection** → *Disk or ISO image* → **SELECT** → `rocola-i386-<versión>.iso`.
3. **START**.
4. Aparece *ISOHybrid image detected*. Elegí **"Escribir en modo Imagen DD" (Write in DD Image mode)**.
5. Confirmá el borrado → esperá → listo.

En modo DD, Rufus clona la imagen **byte a byte** — idéntico a `dd if=…iso of=/dev/sdX`, que es
como se verificó el arranque (BIOS y UEFI) en QEMU. No tenés que elegir MBR/GPT, file system,
cluster, formato ni "fixes": Rufus no arma nada, solo copia.

## ¿Por qué modo DD y no modo ISO?

Rufus solo ofrece esta elección con imágenes híbridas:

- **Modo DD** — copia la imagen byte a byte. Preserva el MBR, la GPT, la partición EFI y el GRUB
  embebido exactamente como se construyeron. Es lo que queremos para esta imagen.
- **Modo ISO** — Rufus **descarta** la estructura del ISO, crea su propia partición FAT, copia los
  archivos y le instala su propio gestor de arranque. Para imágenes basadas en GRUB (como ésta,
  hecha con `grub-mkrescue`) eso puede **no reproducir** bien el arranque y fallar al bootear.

> Regla práctica: imagen de la rocola → **siempre modo DD**.

## Qué significa cada opción (y por qué no la tocás en modo DD)

Todas estas viven en la ventana de Rufus (algunas bajo *Show advanced drive/format properties*).
**En modo DD quedan deshabilitadas/ignoradas**; solo importan si grabaras en modo ISO.

| Opción de Rufus | Qué hace | En modo DD |
|-----------------|----------|------------|
| **Partition scheme: MBR / GPT** | Tabla de particiones que arma Rufus (MBR = BIOS viejo; GPT = UEFI puro). | Ignorada: se usa la del ISO (MBR protectivo + GPT). |
| **Target system: BIOS / UEFI** | Para qué firmware prepara el arranque Rufus. | Ignorada: la imagen ya arranca por BIOS **y** UEFI x64. |
| **Add fixes for old BIOSes (extra partition, align, etc.)** | Tweak de Rufus que agrega una partición chica y alinea, para BIOS que se niegan a bootear de USB. | Ignorada. La imagen ya trae arranque BIOS real (`grub2-mbr` + boot-info-table); **no** son "los fixes de Rufus", es otro mecanismo. |
| **Enable UEFI media validation** | (Rufus 4.5+) Inserta un validador que al **arrancar** recalcula un MD5 de los archivos para detectar corrupción/alteración del pendrive. Modifica el medio → **solo modo ISO**. | No aplica. (Para verificar la descarga, usá el `SHA256SUMS.txt`, ver abajo.) |
| **File system / Cluster size** | Qué FAT/NTFS y tamaño de cluster usa la partición que crea Rufus. | Ignorado: el contenido lo define el ISO. |
| **Quick format** | Formato rápido (solo metadata) vs completo (chequea bloques dañados, lento). | Irrelevante. |

## "Pero vos ya le pusiste los fixes a la imagen, ¿no?"

Sí y no, y conviene tener clara la diferencia:

- **Sí**: la imagen ya es **completamente booteable** por BIOS (32/64-bit) y por UEFI x64, sin
  ayuda externa. Eso viene del layout que arma `grub-mkrescue` (ver
  [02 · Build pipeline](02-build-pipeline.md) y [12 · Verificación](12-verificacion.md)).
- **No**: el casillero *"Add fixes for old BIOSes"* de Rufus es una intervención **de Rufus en
  modo ISO**, no algo que esté "dentro" de la imagen. Como grabás en modo DD, ese casillero ni
  participa.

## UEFI y Secure Boot (importante)

En PCs con **UEFI**, **desactivá Secure Boot** en el firmware antes de bootear: el
`EFI/BOOT/BOOTX64.EFI` de la imagen es de `grub-efi-amd64` y **no está firmado**, así que con Secure
Boot activo el arranque UEFI se bloquea. Por **BIOS / Legacy** esto no aplica.

> *Aclaración:* el cargador UEFI x64 carga un kernel **i386**. UEFI 32-bit queda fuera de alcance
> (ver [CLAUDE.md](../CLAUDE.md) / [ARCHITECTURE.md](../ARCHITECTURE.md)).

## Verificar la descarga

Antes de grabar conviene confirmar que el `.iso` se bajó completo y sin corrupción, comparando con
el `SHA256SUMS.txt` del Release:

```powershell
# PowerShell
Get-FileHash rocola-i386-<versión>.iso -Algorithm SHA256
```

El valor debe coincidir con el de `SHA256SUMS.txt`.

## Si Rufus no te ofrece el modo DD

Es raro con esta imagen, pero si solo te deja modo ISO (o el arranque falla), usá una herramienta
que siempre escribe en crudo:

- **balenaEtcher** (multiplataforma): *Flash from file* → el `.iso` → pendrive → *Flash*. Siempre DD.
- **Ventoy**: instalalo una vez en el pendrive y **copiá** el `.iso` a su partición (ver
  [10 · Grabar el pendrive](10-flashing-usb.md)).
- En Linux/macOS: `dd if=rocola-i386-<versión>.iso of=/dev/sdX bs=4M status=progress conv=fsync`.

---

Ver también: [10 · Grabar el pendrive](10-flashing-usb.md) ·
[11 · Resolución de problemas](11-troubleshooting.md).
