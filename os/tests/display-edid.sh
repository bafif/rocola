#!/bin/bash
# Tests for display/rocola-edid against a fake /sys/class/drm (ROCOLA_DRM_DIR): the EDIDs
# are built here byte by byte. Needs bash and coreutils. Run: make os-test
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/display/rocola-edid"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }

# make_edid [name]: fills E with a 128-byte EDID 1.4 base block, with the fixed header, the
# monitor name in a 0xFC descriptor (second slot, byte 72) when given, and a valid checksum.
make_edid() {
    local name="${1-}" i sum=0 off=72
    E=()
    for ((i = 0; i < 128; i++)); do E[i]=0; done
    for i in 1 2 3 4 5 6; do E[i]=255; done
    E[18]=1
    E[19]=4
    if [ -n "$name" ]; then
        E[off + 3]=252
        for ((i = 0; i < 13; i++)); do
            if ((i < ${#name})); then
                E[off + 5 + i]=$(printf '%d' "'${name:i:1}")
            elif ((i == ${#name})); then
                E[off + 5 + i]=10
            else
                E[off + 5 + i]=32
            fi
        done
    fi
    for ((i = 0; i < 127; i++)); do sum=$((sum + E[i])); done
    E[127]=$(((256 - sum % 256) % 256))
}

# write_edid <connector dir> [bytes]: writes the first [bytes] of E (all by default) as
# <fake drm>/<connector dir>/edid.
write_edid() {
    local dir="$WORK/drm/$1" n="${2:-${#E[@]}}" i out=
    mkdir -p "$dir"
    for ((i = 0; i < n; i++)); do out+="$(printf '\\x%02x' "${E[i]}")"; done
    printf '%b' "$out" >"$dir/edid"
}

run_edid() { ROCOLA_DRM_DIR="$WORK/drm" bash "$SCRIPT"; }

# --- the builder itself: a real 128-byte file with the header
make_edid "ROCOLA TEST"
write_edid card0-HDMI-A-1
[ "$(stat -c %s "$WORK/drm/card0-HDMI-A-1/edid")" -eq 128 ] || fail "the fake EDID is not 128 bytes"

# --- what gets listed: valid EDIDs, with or without a name; a 13-letter name has no 0x0A
make_edid
write_edid card1-DVI-I-1
make_edid "ABCDEFGHIJKLM"
write_edid card0-DP-1

# --- what does not: an empty connector, a bad checksum, a short read, a wrong header
mkdir -p "$WORK/drm/card0-HDMI-A-2"
: >"$WORK/drm/card0-HDMI-A-2/edid"
make_edid "BROKEN"
E[127]=$(((E[127] + 1) % 256))
write_edid card0-VGA-1
make_edid "SHORT"
write_edid card0-DVI-D-1 64
make_edid "NOHEADER"
E[0]=1
E[127]=$(((E[127] + 255) % 256))
write_edid card0-DP-2
mkdir -p "$WORK/drm/card0" "$WORK/drm/renderD128"

out="$(run_edid)" || fail "exit status $? with valid EDIDs"
expected="$(printf '%s\n' "DP-1 ABCDEFGHIJKLM" "HDMI-A-1 ROCOLA TEST" "DVI-I-1" | sort)"
[ "$(sort <<<"$out")" = "$expected" ] || fail "listed «$out», expected «$expected»"

# --- no KMS: no connectors at all
rm -rf "$WORK/drm"
mkdir -p "$WORK/drm"
if out="$(run_edid)"; then fail "exit status 0 without connectors"; fi
[ -z "$out" ] || fail "printed «$out» without connectors"

if [ "$FAILS" -gt 0 ]; then
    echo "$FAILS failure(s)"
    exit 1
fi
echo "rocola-edid: OK"
