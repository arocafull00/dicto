import threading

import Quartz

KEYCODES = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x", 8: "c", 9: "v", 11: "b",
    12: "q", 13: "w", 14: "e", 15: "r", 16: "y", 17: "t", 18: "1", 19: "2", 20: "3", 21: "4",
    22: "6", 23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8", 29: "0", 30: "]", 31: "o",
    32: "u", 33: "[", 34: "i", 35: "p", 36: "enter", 37: "l", 38: "j", 39: "'", 40: "k", 41: ";",
    42: "\\", 43: ",", 44: "/", 45: "n", 46: "m", 47: ".", 48: "tab", 49: "space", 50: "`",
    51: "backspace", 53: "esc", 64: "f17", 79: "f18", 80: "f19", 96: "f5", 97: "f6", 98: "f7",
    99: "f3", 100: "f8", 101: "f9", 103: "f11", 105: "f13", 106: "f16", 107: "f14", 109: "f10",
    111: "f12", 113: "f15", 115: "home", 116: "page up", 117: "delete", 118: "f4", 119: "end",
    120: "f2", 121: "page down", 122: "f1", 123: "left", 124: "right", 125: "down", 126: "up",
}
MODIFIERS = {
    59: ("ctrl", 0x1),
    62: ("right ctrl", 0x2000),
    56: ("shift", 0x2),
    60: ("right shift", 0x4),
    55: ("cmd", 0x8),
    54: ("right cmd", 0x10),
    58: ("option", 0x20),
    61: ("right option", 0x40),
    63: ("fn", Quartz.kCGEventFlagMaskSecondaryFn),
}
FLAGS = {
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "shift": Quartz.kCGEventFlagMaskShift,
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "option": Quartz.kCGEventFlagMaskAlternate,
    "fn": Quartz.kCGEventFlagMaskSecondaryFn,
}
ALIASES = {
    "control": "ctrl",
    "command": "cmd",
    "alt": "option",
    "right control": "right ctrl",
    "right command": "right cmd",
    "right alt": "right option",
    "left ctrl": "ctrl",
    "left shift": "shift",
    "left cmd": "cmd",
    "left option": "option",
}
ORDER = [name for name, _ in MODIFIERS.values()]
CODES = {name: code for code, name in KEYCODES.items()}

_pressed = set()
_seen = set()
_changed = threading.Condition()
_tap = None


def _callback(proxy, kind, event, refcon):
    if kind in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
        Quartz.CGEventTapEnable(_tap, True)
        return event
    code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
    if code in MODIFIERS:
        name, bit = MODIFIERS[code]
        down = bool(Quartz.CGEventGetFlags(event) & bit)
    elif kind == Quartz.kCGEventFlagsChanged:
        return event
    else:
        name, down = KEYCODES.get(code, f"key {code}"), kind == Quartz.kCGEventKeyDown
    with _changed:
        if down:
            _pressed.add(name)
            _seen.add(name)
        else:
            _pressed.discard(name)
        _changed.notify_all()
    return event


def _loop(ready):
    global _tap
    mask = (
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
        | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
    )
    _tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionListenOnly,
        mask,
        _callback,
        None,
    )
    ready.set()
    if _tap is None:
        return
    source = Quartz.CFMachPortCreateRunLoopSource(None, _tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(_tap, True)
    Quartz.CFRunLoopRun()


def start():
    for request in ("CGRequestListenEventAccess", "CGRequestPostEventAccess"):
        fn = getattr(Quartz, request, None)
        if fn:
            fn()
    ready = threading.Event()
    threading.Thread(target=_loop, args=(ready,), daemon=True).start()
    ready.wait()
    return _tap is not None


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
    flags = 0
    for p in parts[:-1]:
        flags |= FLAGS[p.removeprefix("right ")]
    code = CODES[parts[-1]]
    for down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(None, code, down)
        Quartz.CGEventSetFlags(event, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
