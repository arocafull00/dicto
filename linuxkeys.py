import threading

from pynput import keyboard

NAMES = {
    keyboard.Key.ctrl: "ctrl",
    keyboard.Key.ctrl_l: "ctrl",
    keyboard.Key.ctrl_r: "right ctrl",
    keyboard.Key.shift: "shift",
    keyboard.Key.shift_l: "shift",
    keyboard.Key.shift_r: "right shift",
    keyboard.Key.alt: "alt",
    keyboard.Key.alt_l: "alt",
    keyboard.Key.alt_r: "right alt",
    keyboard.Key.alt_gr: "alt gr",
    keyboard.Key.cmd: "windows",
    keyboard.Key.cmd_l: "windows",
    keyboard.Key.cmd_r: "right windows",
}
ALIASES = {
    "control": "ctrl",
    "left ctrl": "ctrl",
    "right control": "right ctrl",
    "left shift": "shift",
    "option": "alt",
    "left alt": "alt",
    "right option": "right alt",
    "super": "windows",
    "cmd": "windows",
    "left windows": "windows",
    "right super": "right windows",
    "right cmd": "right windows",
    "return": "enter",
    "escape": "esc",
}
ORDER = ["ctrl", "right ctrl", "shift", "right shift", "alt", "right alt", "alt gr", "windows", "right windows"]
KEYS = {"ctrl": keyboard.Key.ctrl, "shift": keyboard.Key.shift, "alt": keyboard.Key.alt, "windows": keyboard.Key.cmd}

_pressed = set()
_seen = set()
_changed = threading.Condition()
_controller = keyboard.Controller()


def _name(key):
    if key in NAMES:
        return NAMES[key]
    if isinstance(key, keyboard.Key):
        return key.name.replace("_", " ")
    if key.char:
        return key.char.lower()
    return f"key {key.vk}"


def _on_press(key):
    name = _name(key)
    with _changed:
        _pressed.add(name)
        _seen.add(name)
        _changed.notify_all()


def _on_release(key):
    with _changed:
        _pressed.discard(_name(key))
        _changed.notify_all()


def start():
    try:
        keyboard.Listener(on_press=_on_press, on_release=_on_release, daemon=True).start()
    except Exception:
        return False
    return True


def _parts(hotkey):
    return [ALIASES.get(p.strip(), p.strip()) for p in hotkey.lower().split("+") if p.strip()]


def is_pressed(hotkey):
    parts = _parts(hotkey)
    with _changed:
        return bool(parts) and all(p in _pressed or f"right {p}" in _pressed for p in parts)


def _rank(name):
    return (ORDER.index(name), "") if name in ORDER else (len(ORDER), name)


def read_hotkey(suppress=False):
    with _changed:
        _seen.clear()
        _changed.wait_for(lambda: _seen and not _pressed)
        return "+".join(sorted(_seen, key=_rank))


def send(combo):
    parts = _parts(combo)
    mods = [KEYS[p.removeprefix("right ")] for p in parts[:-1]]
    for m in mods:
        _controller.press(m)
    _controller.tap(parts[-1])
    for m in reversed(mods):
        _controller.release(m)
