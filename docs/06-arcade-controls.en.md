# 06 · Arcade controls

*English · [Español](06-arcade-controls.md)*

The jukebox is operated with **arcade controls** (joystick + buttons), with no keyboard or mouse in
day-to-day use.

## Typical hardware

Arcade cabinets use a **USB encoder** that wires up the joystick/button microswitches and presents
them to the PC as an input device. The most common ones:

- **Keyboard mode** (iPAC, and many "zero-delay" boards): each button = one key.
- **Joystick/gamepad mode** (Xin-Mo, "zero-delay" in gamepad mode): axes + buttons.

Some encoders can work in either mode.

## Approach: autodetection (keyboard **and** joystick)

The app uses **SDL2**, which already abstracts keyboard and joystick. On startup it:

1. Enumerates and initializes **all** connected joysticks (and enumerates them again whenever one
   is plugged in or unplugged).
2. Also keeps the **keyboard** mapping always active.
3. Needs no choice: joystick and keyboard work at the same time.

## Jukebox actions

Button numbers are SDL indices (they start at 0); `jstest` or `evtest` show which one each button
on the encoder sends.

| Action | Joystick | Keyboard (default) |
|--------|----------|-------------------|
| Navigate up/down | Y axis (odd axes) / D-pad | ↑ / ↓ |
| Navigate left/right (pages, letters) | X axis (even axes) / D-pad | ← / → |
| Select / Play | button 0 | Enter |
| Back / Cancel | button 1 | Esc / Backspace |
| Play/Pause | button 2 | Space |
| Menu (audio, info, installer) | button 3 | F10 |
| Previous / Next | buttons 4 / 5 | P / N |
| Volume − / + | buttons 6 / 7 | − / + (or =) |

Analog axes have a dead zone of 0.5 and fire a single action per movement (holding the stick
doesn't repeat).

The default mappings live in `app/rocola/input.py` (`DEFAULT_KEYMAP` and `DEFAULT_BUTTONMAP`). You
can change them without touching code through the `[keys]` and `[buttons]` tables in
`/etc/rocola/rocola.toml`, which are added on top of the defaults:

```toml
[keys]          # SDL key name -> action
m = "menu"
f10 = "none"    # "none" removes a default mapping

[buttons]       # joystick button index -> action
8 = "menu"
3 = "none"
```

Actions: `up`, `down`, `left`, `right`, `select`, `back`, `playpause`, `next`, `prev`, `volup`,
`voldown` and `menu`. An unknown key or action is ignored: the configuration never keeps the app
from starting. In live mode `/etc` lives in RAM; for the file to ship in the image it goes in
`os/rootfs-overlay/etc/rocola/rocola.toml` before `make rootfs`. On the installed system you edit
it directly.

## Calibration

The app reads the joystick by **button index** (SDL's joystick API, not the GameController one), so
a mapping from SDL_GameControllerDB changes nothing. For an encoder with different numbering you
need to adjust `[buttons]`. To see which index each button sends: menu → **Test controls**. Each
key or button shows up with the name or index that goes in `[keys]`/`[buttons]` and the action it
currently maps to. You exit with Back twice in a row or after 15 s without touching anything, so a
badly mapped encoder doesn't leave anyone stuck in there. Screenshot:
[screenshots/ui-inputtest.png](screenshots/ui-inputtest.png).

## Accessing the installer

The **guided installer** is opened from the menu (button 3 or F10) → "Install to disk". There's no
direct shortcut, so it can't be triggered by accident during normal use, and the installer asks for
confirmation before touching a disk. The option only appears when the jukebox is running from the
USB stick.

The installer is a text screen operated with a **keyboard**: the confirmation is typed, and an
encoder in joystick mode doesn't send keys to the console. To install, you have to plug one in.

Next: [07 · The app](07-rocola-app.en.md).