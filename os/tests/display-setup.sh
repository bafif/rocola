#!/bin/bash
# Tests for display/rocola-display-setup on a fake root (ROCOLA_ROOT): the kernel command line,
# /dev/dri, the framebuffer depth and display.conf are made up here, and a fake udevadm stands
# in for udev (ROCOLA_UDEVADM). Needs bash and coreutils. Run: make os-test
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$REPO/display/rocola-display-setup"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
ROOT="$WORK/root"
FAILS=0

fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }

# The fake udevadm logs each call. With $WORK/late-driver present it plays a GPU driver that
# finishes loading while udev settles: it creates /dev/dri/card0.
cat >"$WORK/udevadm" <<EOF
#!/bin/bash
echo "\$*" >>"$WORK/udevadm.log"
if [ -e "$WORK/late-driver" ]; then : >"$ROOT/dev/dri/card0"; fi
EOF
chmod +x "$WORK/udevadm"

# new_root <kernel command line> [framebuffer bpp]: a clean fake root with the real modelines
# and EDID reader, no GPU node and no display.conf.
new_root() {
    rm -rf "$ROOT" "$WORK/late-driver"
    mkdir -p "$ROOT/proc" "$ROOT/dev/dri" "$ROOT/etc/rocola" "$ROOT/sys/class/drm" \
        "$ROOT/sys/class/graphics/fb0" "$ROOT/opt/rocola-display"
    echo "$1" >"$ROOT/proc/cmdline"
    echo "${2:-32}" >"$ROOT/sys/class/graphics/fb0/bits_per_pixel"
    ln -s "$REPO/display/modelines" "$ROOT/opt/rocola-display/modelines"
    ln -s "$REPO/display/rocola-edid" "$ROOT/opt/rocola-display/rocola-edid"
    : >"$WORK/udevadm.log"
}

# run_setup <case>: runs the script and leaves the generated config in CONFIG and the number
# of times it waited for udev in SETTLES.
run_setup() {
    ROCOLA_ROOT="$ROOT" ROCOLA_UDEVADM="$WORK/udevadm" bash "$SCRIPT" >"$WORK/log" 2>&1 ||
        fail "$1: exit status $?"
    CONFIG="$(cat "$ROOT/etc/X11/xorg.conf.d/10-rocola-display.conf" 2>/dev/null || true)"
    SETTLES="$(grep -c '^settle' "$WORK/udevadm.log" || true)"
}

# expect <case> <driver> <udev waits>
expect() {
    grep -qF "Driver \"$2\"" <<<"$CONFIG" || fail "$1: expected driver $2, got «$CONFIG»"
    [ "$SETTLES" -eq "$3" ] || fail "$1: waited for udev $SETTLES time(s), expected $3"
}

KMS_CMDLINE="boot=live components quiet loglevel=3"

# --- default entry (nomodeset): fbdev at once, without waiting for udev
new_root "$KMS_CMDLINE nomodeset"
run_setup nomodeset
expect nomodeset fbdev 0
grep -qF 'Option "fbdev" "/dev/fb0"' <<<"$CONFIG" || fail "nomodeset: no fbdev device option"
if grep -q DefaultDepth <<<"$CONFIG"; then fail "nomodeset at 32 bpp: unexpected DefaultDepth"; fi
grep -qF 'sin KMS no hay EDID' "$WORK/log" || fail "nomodeset: no note about the missing EDID"

# --- a 16 bpp firmware framebuffer: Xorg has to use its depth
new_root "$KMS_CMDLINE nomodeset" 16
run_setup "16 bpp"
grep -q 'DefaultDepth 16' <<<"$CONFIG" || fail "16 bpp: no DefaultDepth 16"

# --- KMS entry with the GPU driver already loaded: no wait
new_root "$KMS_CMDLINE"
: >"$ROOT/dev/dri/card0"
run_setup "KMS, driver loaded"
expect "KMS, driver loaded" modesetting 0

# --- KMS entry on a slow machine: the driver shows up while udev settles
new_root "$KMS_CMDLINE"
: >"$WORK/late-driver"
run_setup "KMS, late driver"
expect "KMS, late driver" modesetting 1
grep -qx 'settle --timeout=10' "$WORK/udevadm.log" || fail "KMS, late driver: udev settle without a 10 s limit"

# --- KMS entry, but the kernel has no driver for this GPU: fbdev after the wait
new_root "$KMS_CMDLINE"
run_setup "KMS, no driver"
expect "KMS, no driver" fbdev 1

# --- 15 kHz on a PAL set: every fixed modeline and the PAL resolution
new_root "$KMS_CMDLINE"
: >"$ROOT/dev/dri/card0"
printf 'MODE=crt15\nTV_STANDARD=pal\n' >"$ROOT/etc/rocola/display.conf"
run_setup "crt15 PAL"
expect "crt15 PAL" modesetting 0
modelines="$(grep -c '^[[:space:]]*Modeline' "$REPO/display/modelines/15khz.conf")"
[ "$(grep -c Modeline <<<"$CONFIG")" -eq "$modelines" ] || fail "crt15 PAL: not all $modelines modelines"
grep -qF 'Option "PreferredMode" "768x576i_50"' <<<"$CONFIG" || fail "crt15 PAL: preferred mode is not 768x576i_50"

if [ "$FAILS" -gt 0 ]; then
    echo "$FAILS failure(s)"
    exit 1
fi
echo "rocola-display-setup: OK"
