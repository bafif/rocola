#!/bin/bash
# Tests for rocola-music-import, without root: /music and the preloaded library are
# temporary folders (ROCOLA_MUSIC_DIR, ROCOLA_PRELOAD_DIR) and `mpc` is a fake that
# records its calls. Needs bash, rsync and coreutils. Run: make os-test
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/rootfs-overlay/usr/local/bin/rocola-music-import"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }
has() { [ -e "$1" ] || fail "missing $1"; }
lacks() { [ ! -e "$1" ] || fail "should not exist: $1"; }
same_file() { [ "$1" -ef "$2" ] || cmp -s "$1" "$2" || fail "$1 is not $2"; }
content() { [ "$(cat "$1" 2>/dev/null)" = "$2" ] || fail "$1 is «$(cat "$1" 2>/dev/null)», expected «$2»"; }

mkdir -p "$WORK/bin"
cat >"$WORK/bin/mpc" <<'MPC'
#!/bin/sh
echo "$*" >>"$MPC_LOG"
MPC
chmod +x "$WORK/bin/mpc"

# Fresh /music, preloaded library and stick for each case.
setup() {
    rm -rf "$WORK/music" "$WORK/preload" "$WORK/stick" "$WORK/mpc.log"
    mkdir -p "$WORK/music" "$WORK/preload" "$WORK/stick"
}

run_import() {
    PATH="$WORK/bin:$PATH" MPC_LOG="$WORK/mpc.log" \
        ROCOLA_MUSIC_DIR="$WORK/music" ROCOLA_PRELOAD_DIR="$WORK/preload" \
        bash "$SCRIPT" "$@" >/dev/null
}

file() { mkdir -p "$(dirname "$1")"; printf '%s' "${2:-x}" >"$1"; }

# --- the preloaded library goes in only while /music is empty
setup
file "$WORK/preload/Demo/01.ogg"
run_import "$WORK/stick"
has "$WORK/music/Demo/01.ogg"
content "$WORK/mpc.log" "update"

setup
file "$WORK/preload/Demo/01.ogg"
file "$WORK/music/Mine/a.mp3"
run_import "$WORK/stick"
lacks "$WORK/music/Demo"

# --- from a stick: audio in any case, folder covers; no photos, no empty folders
setup
file "$WORK/stick/Album/TEMA01.MP3"
file "$WORK/stick/Album/b.flac"
file "$WORK/stick/Album/Folder.JPG" "jpgA"
file "$WORK/stick/Album/notes.txt"
file "$WORK/stick/DCIM/IMG_0001.JPG"
file "$WORK/stick/Fotos/cover-art-final.png"
run_import "$WORK/stick"
has "$WORK/music/Album/TEMA01.MP3"
has "$WORK/music/Album/b.flac"
has "$WORK/music/Album/Folder.JPG"
lacks "$WORK/music/Album/notes.txt"
lacks "$WORK/music/DCIM"
lacks "$WORK/music/Fotos"

# --- cover names MPD finds (cover.png/jpg/webp, written exactly so)
content "$WORK/music/Album/cover.jpg" "jpgA"
same_file "$WORK/music/Album/cover.jpg" "$WORK/music/Album/Folder.JPG"

setup
file "$WORK/stick/C/01.mp3"
file "$WORK/stick/C/COVER.PNG" "pngC"
file "$WORK/stick/C/folder.jpg" "jpgC"
file "$WORK/stick/D/01.mp3"
file "$WORK/stick/D/cover.jpg" "jpgD"
file "$WORK/stick/D/Folder.jpg" "otherD"
file "$WORK/stick/E/01.mp3"
file "$WORK/stick/E/folder.jpeg" "jpegE"
file "$WORK/stick/F/01.mp3"
file "$WORK/music/Old/a.mp3"
file "$WORK/music/Old/folder.webp" "webpOld"
run_import "$WORK/stick"
content "$WORK/music/C/cover.png" "pngC" # cover.* wins over folder.*
lacks "$WORK/music/C/cover.jpg"
content "$WORK/music/D/cover.jpg" "jpgD" # an existing cover stays as it is
content "$WORK/music/E/cover.jpg" "jpegE" # .jpeg becomes .jpg
lacks "$WORK/music/F/cover.jpg"           # no image, no cover
content "$WORK/music/Old/cover.webp" "webpOld" # music imported earlier too

# --- importing the same stick again does not overwrite anything
setup
file "$WORK/stick/A/01.mp3" "new"
file "$WORK/music/A/01.mp3" "old"
run_import "$WORK/stick"
content "$WORK/music/A/01.mp3" "old"

# --- a fresh partition (only lost+found) counts as empty; .gitkeep is not music
setup
mkdir "$WORK/music/lost+found"
file "$WORK/preload/.gitkeep" ""
file "$WORK/preload/Demo/01.ogg"
run_import "$WORK/stick"
has "$WORK/music/Demo/01.ogg"
lacks "$WORK/music/.gitkeep"

# --- symbolic links on the stick stay out (they can point anywhere)
setup
file "$WORK/outside/secret.mp3"
mkdir -p "$WORK/stick/Album"
ln -s "$WORK/outside/secret.mp3" "$WORK/stick/Album/link.mp3"
ln -s "$WORK/outside" "$WORK/stick/Linked"
file "$WORK/stick/Album/real.mp3"
run_import "$WORK/stick"
has "$WORK/music/Album/real.mp3"
lacks "$WORK/music/Album/link.mp3"
lacks "$WORK/music/Linked"

if [ "$FAILS" -gt 0 ]; then
    echo "$FAILS check(s) failed"
    exit 1
fi
echo "music-import: all checks passed"
