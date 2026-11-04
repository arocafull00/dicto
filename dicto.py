import ctypes
import difflib
import json
import os
import plistlib
import queue
import re
import shlex
import shutil
import subprocess
import sys
import string
import threading
import time
import tkinter as tk
import unicodedata

if __name__ == "__main__" and sys.argv[1:] == ["--ui"]:
    import ui

    ui.main()

MAC = sys.platform == "darwin"
WIN = sys.platform == "win32"
LINUX = not MAC and not WIN
FROZEN = getattr(sys, "frozen", False)
if WIN:
    import winreg
    import winsound
else:
    import fcntl

APP = "Dicto"
HERE = os.path.dirname(os.path.abspath(__file__))
if MAC:
    CONFIG_DIR = os.path.expanduser(f"~/Library/Application Support/{APP}")
elif LINUX:
    CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), APP)
else:
    CONFIG_DIR = os.path.join(os.environ["APPDATA"], APP)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
HISTORY_PATH = os.path.join(CONFIG_DIR, "history.json")
HISTORY_LIMIT = 500
LOG_PATH = os.path.join(CONFIG_DIR, "dicto.log")
ICON_PATH = os.path.join(HERE, "dicto.ico")
PNG_PATH = os.path.join(HERE, "assets", "dicto.png")
PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe") if WIN else sys.executable
LAUNCH = [sys.executable] if FROZEN else [PYTHONW, os.path.join(HERE, "dicto.py")]
UI_COMMAND = [sys.executable, "--ui"] if FROZEN else [sys.executable, os.path.join(HERE, "ui.py")]
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
BUNDLE_ID = "io.github.arocafull00.dicto"
if MAC and FROZEN:
    APP_BUNDLE = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
else:
    APP_BUNDLE = os.path.expanduser(f"~/Applications/{APP}.app")
LAUNCH_AGENT = os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")
XDG_DATA = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
DESKTOP_FILE = os.path.join(XDG_DATA, "applications", "dicto.desktop")
AUTOSTART_FILE = os.path.join(os.path.dirname(CONFIG_DIR), "autostart", "dicto.desktop")
RATE = 16000
CHUNK_MIN = 8
CHUNK_MAX = 20
PARAKEET_REPO = "istupakov/parakeet-tdt-0.6b-v3-onnx"
PARAKEET_DIR = os.path.join(CONFIG_DIR, "models", "parakeet-tdt-0.6b-v3")
PARAKEET_FILES = ["encoder-model.int8.onnx", "decoder_joint-model.int8.onnx", "nemo128.onnx", "vocab.txt", "config.json"]
PUNCT = string.punctuation + "¿¡«»…—“”‘’"

os.makedirs(CONFIG_DIR, exist_ok=True)
if sys.stdout is None or sys.stderr is None:
    sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
else:
    sys.stdout.reconfigure(line_buffering=True)


import numpy as np
import onnx_asr
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

if MAC:
    import AppKit
    import mackeys as keyboard
elif LINUX:
    import linuxkeys as keyboard
else:
    import keyboard

DEFAULTS = {
    "hotkey": "right option" if MAC else "right ctrl",
    "mode": "hold",
    "device": "",
    "vocabulary": "",
    "sounds": True,
    "overlay": True,
    "autostart": False,
}

MODES = {"Mantener pulsado": "hold", "Pulsar para empezar y parar": "toggle"}
DEFAULT_MIC = "Predeterminado del sistema"

COLORS = {"loading": "#8a8f98", "idle": "#216B50", "recording": "#e5484d", "processing": "#f5a524"}
STATUS_TEXT = {
    "loading": "Cargando modelo…",
    "idle": "Listo",
    "recording": "Escuchando…",
    "processing": "Transcribiendo…",
}


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_history():
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"words": 0, "seconds": 0.0, "items": []}


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)


def make_icon(color, size=64):
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = big / 256
    d.rounded_rectangle((0, 0, big - 1, big - 1), radius=57.6 * s, fill=color)
    for x, top, bottom in ((64, 96, 158), (128, 40, 214), (192, 64, 190)):
        d.rounded_rectangle(((x - 19) * s, top * s, (x + 19) * s, bottom * s), radius=19 * s, fill="white")
    return img.resize((size, size), Image.LANCZOS)


ICONS = {k: make_icon(c) for k, c in COLORS.items()}


def set_autostart(on):
    if MAC:
        if on:
            os.makedirs(os.path.dirname(LAUNCH_AGENT), exist_ok=True)
            with open(LAUNCH_AGENT, "wb") as f:
                plistlib.dump({"Label": BUNDLE_ID, "ProgramArguments": ["/usr/bin/open", APP_BUNDLE], "RunAtLoad": True}, f)
        elif os.path.exists(LAUNCH_AGENT):
            os.remove(LAUNCH_AGENT)
        return
    if LINUX:
        if on:
            write_desktop_entry(AUTOSTART_FILE)
        elif os.path.exists(AUTOSTART_FILE):
            os.remove(AUTOSTART_FILE)
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, subprocess.list2cmdline(LAUNCH))
        else:
            try:
                winreg.DeleteValue(k, APP)
            except FileNotFoundError:
                pass


def ensure_mac_app():
    contents = os.path.join(APP_BUNDLE, "Contents")
    os.makedirs(os.path.join(contents, "MacOS"), exist_ok=True)
    os.makedirs(os.path.join(contents, "Resources"), exist_ok=True)
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(
            {
                "CFBundleName": APP,
                "CFBundleDisplayName": APP,
                "CFBundleIdentifier": BUNDLE_ID,
                "CFBundleExecutable": APP,
                "CFBundleIconFile": "dicto",
                "CFBundlePackageType": "APPL",
                "LSUIElement": True,
                "NSMicrophoneUsageDescription": "Dicto usa el micrófono para transcribir lo que dictas.",
            },
            f,
        )
    launcher = os.path.join(contents, "MacOS", APP)
    with open(launcher, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/sh\n"
            f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(HERE, 'dicto.py'))}"
            f" >> {shlex.quote(LOG_PATH)} 2>&1\n"
        )
    os.chmod(launcher, 0o755)
    icns = os.path.join(HERE, "assets", "dicto.icns")
    if os.path.exists(icns):
        shutil.copy(icns, os.path.join(contents, "Resources", "dicto.icns"))


def write_desktop_entry(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP}\n"
            "Comment=Dictado por voz 100 % local\n"
            f"Exec={shlex.join(LAUNCH)}\n"
            "Icon=dicto\n"
            "Terminal=false\n"
            "Categories=Utility;Accessibility;AudioVideo;\n"
            "Keywords=dictado;voz;parakeet;transcripción;\n"
            f"StartupWMClass={APP}\n"
        )


def ensure_linux_app():
    write_desktop_entry(DESKTOP_FILE)
    icons = os.path.join(HERE, "assets", "linux", "icons")
    if os.path.isdir(icons):
        shutil.copytree(icons, os.path.join(XDG_DATA, "icons"), dirs_exist_ok=True)


def ensure_shortcuts():
    if MAC:
        if not FROZEN:
            ensure_mac_app()
        return
    if LINUX:
        ensure_linux_app()
        return
    if FROZEN:
        return
    start_menu = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs", f"{APP}.lnk")
    if os.path.exists(start_menu):
        return
    script = (
        "$s = New-Object -ComObject WScript.Shell; "
        "foreach ($p in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) { "
        "$l = $s.CreateShortcut((Join-Path $p 'Dicto.lnk')); "
        "$l.TargetPath = $env:DICTO_TARGET; $l.Arguments = $env:DICTO_ARGS; "
        "$l.WorkingDirectory = $env:DICTO_DIR; $l.IconLocation = $env:DICTO_ICON; "
        "$l.Description = 'Dictado por voz local'; $l.Save() }"
    )
    env = dict(
        os.environ,
        DICTO_TARGET=PYTHONW,
        DICTO_ARGS=f'"{os.path.join(HERE, "dicto.py")}"',
        DICTO_DIR=HERE,
        DICTO_ICON=ICON_PATH,
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


def uninstall_plan():
    """Rutas que se borran al desinstalar, el desinstalador de Windows y lo que quede por hacer a mano."""
    paths, uninstaller, note = [CONFIG_DIR], "", ""
    real = os.path.realpath(HERE)
    if FROZEN and MAC:
        paths.append(APP_BUNDLE)
    elif FROZEN and WIN:
        exe_dir = os.path.dirname(sys.executable)
        uninstaller = next((os.path.join(exe_dir, f) for f in sorted(os.listdir(exe_dir)) if f.lower().startswith("unins") and f.lower().endswith(".exe")), "")
    elif FROZEN:
        paths.append(os.path.dirname(sys.executable))
    elif "/Cellar/" in real:
        note = "Para quitar el resto, ejecuta en la Terminal: brew uninstall dicto"
    elif "\\scoop\\apps\\" in real.lower():
        note = "Para quitar el resto, ejecuta en PowerShell: scoop uninstall dicto"
    elif os.path.isdir(os.path.join(HERE, ".git")):
        # Es un clon de Git: se borra el entorno de Python, pero no el código.
        paths.append(os.path.join(HERE, ".venv"))
        note = f"La carpeta del código sigue en {HERE}. Bórrala si ya no la necesitas."
    else:
        paths.append(HERE)
    if MAC and not FROZEN:
        paths.append(APP_BUNDLE)
    if LINUX:
        paths.append(DESKTOP_FILE)
        icons = os.path.join(HERE, "assets", "linux", "icons")
        for d, _, files in os.walk(icons):
            paths += [os.path.join(XDG_DATA, "icons", os.path.relpath(d, icons), f) for f in files]
    return paths, uninstaller, note


UNINSTALL_SH = (
    'while kill -0 "$DICTO_PID" 2>/dev/null; do sleep 0.2; done\n'
    'rm -rf -- "$@"\n'
    'if [ "$(uname)" = Darwin ]; then\n'
    f"  tccutil reset All {BUNDLE_ID} >/dev/null 2>&1\n"
    "  osascript -e 'on run argv' -e 'display dialog (item 1 of argv) with title \"Dicto\" buttons {\"OK\"} default button 1'"
    ' -e \'end run\' "$DICTO_MSG"\n'
    "else\n"
    '  notify-send -a Dicto Dicto "$DICTO_MSG" >/dev/null 2>&1\n'
    "fi\n"
)
UNINSTALL_PS = (
    "Wait-Process -Id $env:DICTO_PID -ErrorAction SilentlyContinue; "
    "if ($env:DICTO_UNINSTALLER) { "
    "Start-Process -Wait $env:DICTO_UNINSTALLER -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' }; "
    "if ($env:DICTO_LINKS) { foreach ($f in 'Programs', 'Desktop') { "
    "Remove-Item (Join-Path ([Environment]::GetFolderPath($f)) 'Dicto.lnk') -Force -ErrorAction SilentlyContinue } }; "
    "foreach ($p in $env:DICTO_PATHS.Split('|')) { if ($p) { "
    "Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue } }; "
    "Add-Type -AssemblyName PresentationFramework; "
    "[System.Windows.MessageBox]::Show($env:DICTO_MSG, 'Dicto') | Out-Null"
)


def input_devices():
    host = sd.default.hostapi
    return [d["name"] for d in sd.query_devices() if d["hostapi"] == host and d["max_input_channels"] > 0]


def find_device(name):
    if not name:
        return None
    for i, d in enumerate(sd.query_devices()):
        if d["name"] == name and d["max_input_channels"] > 0:
            return i
    return None


def hotkey_down(hotkey):
    try:
        return keyboard.is_pressed(hotkey)
    except (ValueError, KeyError):
        return False


def beep(start):
    if MAC:
        subprocess.Popen(["afplay", f"/System/Library/Sounds/{'Tink' if start else 'Pop'}.aiff"])
    elif LINUX:
        t = np.arange(int(RATE * 0.07)) / RATE
        sd.play((0.2 * np.sin(2 * np.pi * (880 if start else 440) * t)).astype(np.float32), RATE)
    else:
        threading.Thread(target=winsound.Beep, args=(880 if start else 440, 70), daemon=True).start()


def paste(text):
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None
    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("cmd+v" if MAC else "ctrl+v")
    if previous is not None:
        # La app activa lee el portapapeles un poco después del ⌘V; se restaura sin bloquear.
        threading.Timer(0.3, pyperclip.copy, [previous]).start()


def warm_up(fn):
    """La primera transcripción tras cargar un modelo tarda varios segundos; se hace aquí con silencio."""
    try:
        fn()
    except Exception as e:
        print(f"No se pudo calentar el modelo: {e}")


def parakeet_downloaded():
    return all(os.path.exists(os.path.join(PARAKEET_DIR, f)) for f in PARAKEET_FILES)


def load_parakeet():
    if not parakeet_downloaded():
        from huggingface_hub import snapshot_download

        # En una carpeta propia: onnxruntime rechaza los pesos externos si van por los enlaces de la caché de Hugging Face.
        snapshot_download(PARAKEET_REPO, local_dir=PARAKEET_DIR, allow_patterns=PARAKEET_FILES)
    return onnx_asr.load_model(
        "nemo-parakeet-tdt-0.6b-v3", PARAKEET_DIR, quantization="int8", providers=["CPUExecutionProvider"]
    )


def normalize(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and unicodedata.category(c) != "Mn")


def apply_vocabulary(text, vocabulary):
    """Sustituye en el texto lo que se parezca a una palabra del diccionario (acentos, mayúsculas, letras cambiadas)."""
    words = text.split()
    for term in (t.strip() for t in re.split(r"[,\n]", vocabulary)):
        key, n = normalize(term), len(term.split())
        if len(key) < 3:
            continue
        i = 0
        while i + n <= len(words):
            span = " ".join(words[i : i + n])
            core = span.strip(PUNCT)
            if core and difflib.SequenceMatcher(None, normalize(core), key).ratio() >= 0.8:
                lead = span[: len(span) - len(span.lstrip(PUNCT))]
                trail = span[len(span.rstrip(PUNCT)) :]
                words[i : i + n] = [lead + term + trail]
            i += 1
    return " ".join(words)


def find_cut(audio):
    frame = RATE // 10
    start, n = CHUNK_MIN * 10, len(audio) // frame
    if n <= start:
        return None
    rms = np.sqrt(np.mean(audio[: n * frame].reshape(n, frame) ** 2, axis=1))
    quiet = rms < max(0.1 * np.percentile(rms, 90), 1e-4)
    run = 0
    for i in range(start, n):
        run = run + 1 if quiet[i] else 0
        if run == 5:
            return (i - 2) * frame
    if n >= CHUNK_MAX * 10:
        return (start + int(np.argmin(rms[start:]))) * frame
    return None


class Engine:
    def __init__(self, app):
        self.app = app
        self.parakeet = None
        self.stream = None
        self.device = None
        self.chunks = []
        self.parts = []
        self.audio = threading.Event()
        self.recording = False
        self.level = 0.0
        self.paused = False
        self.dirty = threading.Event()
        self.last_text = ""

    def configure(self):
        cfg = self.app.cfg
        if self.parakeet is None:
            self.app.set_status("loading")
            if not parakeet_downloaded():
                self.app.notify("Descargando el modelo de voz (~640 MB). Solo pasa la primera vez.")
            self.parakeet = load_parakeet()
            warm_up(lambda: self.parakeet.recognize(np.zeros(RATE, np.float32), sample_rate=RATE))
        if self.stream is None or cfg["device"] != self.device:
            if self.stream:
                self.stream.close()
            try:
                self.stream = sd.InputStream(
                    samplerate=RATE,
                    channels=1,
                    dtype="float32",
                    device=find_device(cfg["device"]),
                    callback=self.callback,
                )
            except Exception:
                self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", callback=self.callback)
            self.stream.start()
            self.device = cfg["device"]
        self.app.set_status("idle")

    def callback(self, indata, frames, t, status):
        if self.recording:
            self.chunks.append(indata[:, 0].copy())
            self.level = float(np.sqrt(np.mean(indata**2)))
            self.audio.set()

    def run(self):
        try:
            self.configure()
        except Exception as e:
            self.app.notify(f"No se pudo iniciar: {e}")
            raise
        self.app.on_ready()
        was_down = False
        while True:
            if self.dirty.is_set():
                self.dirty.clear()
                self.configure()
            cfg = self.app.cfg
            down = not self.paused and hotkey_down(cfg["hotkey"])
            pressed, released = down and not was_down, was_down and not down
            was_down = down
            if cfg["mode"] == "hold":
                if pressed:
                    self.start()
                elif released and self.recording:
                    self.stop()
            elif pressed:
                if self.recording:
                    self.stop()
                else:
                    self.start()
            time.sleep(0.01)

    def start(self):
        self.chunks = []
        self.parts = []
        self.level = 0.0
        self.recording = True
        self.worker = threading.Thread(target=self.transcribe_live, daemon=True)
        self.worker.start()
        self.app.set_status("recording")
        if self.app.cfg["sounds"]:
            beep(True)

    def transcribe(self, audio):
        text = self.parakeet.recognize(audio, sample_rate=RATE).strip()
        return apply_vocabulary(text, self.app.cfg["vocabulary"])

    def transcribe_live(self):
        buf = np.zeros(0, np.float32)
        taken = 0
        cutting = True
        while True:
            recording = self.recording
            new = self.chunks[taken:]
            taken += len(new)
            if new:
                buf = np.concatenate([buf, *new])
            if not recording:
                break
            cut = find_cut(buf) if cutting else None
            if not cut:
                self.audio.wait(0.1)
                self.audio.clear()
                continue
            try:
                text = self.transcribe(buf[:cut])
            except Exception as e:
                print(f"Error al transcribir un trozo: {e}")
                cutting = False
                continue
            if text:
                self.parts.append(text)
            buf = buf[cut:]
        self.tail = buf

    def stop(self):
        cfg = self.app.cfg
        self.recording = False
        self.audio.set()
        if cfg["sounds"]:
            beep(False)
        seconds = sum(map(len, self.chunks)) / RATE
        if seconds < 0.3:
            self.worker.join()
            self.app.set_status("idle")
            return
        self.app.set_status("processing")
        self.worker.join()
        try:
            if len(self.tail) >= RATE * 0.3:
                self.parts.append(self.transcribe(self.tail))
        except Exception as e:
            self.app.notify(f"Error al transcribir: {e}")
        text = " ".join(self.parts).strip()
        if text:
            while hotkey_down(cfg["hotkey"]):
                time.sleep(0.02)
            paste(text + " ")
            self.last_text = text
            self.app.post(self.app.add_history, text, seconds)
            print(text)
        self.app.set_status("idle")


class Overlay:
    KEY = "#010203"
    BG = "#17241E"

    def __init__(self, root):
        self.s = root.winfo_fpixels("1i") / (72 if MAC else 96)
        self.w, self.h = int(128 * self.s), int(36 * self.s)
        win = self.win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)
        if MAC:
            win.attributes("-transparent", True)
            bg = "systemTransparent"
        elif LINUX:
            bg = self.BG
        else:
            win.attributes("-transparentcolor", self.KEY)
            bg = self.KEY
        win.configure(bg=bg)
        self.c = tk.Canvas(win, width=self.w, height=self.h, bg=bg, highlightthickness=0)
        self.c.pack()
        x = (win.winfo_screenwidth() - self.w) // 2
        y = win.winfo_screenheight() - self.h - int(90 * self.s)
        win.geometry(f"{self.w}x{self.h}+{x}+{y}")
        win.update_idletasks()
        if LINUX:
            win.withdraw()
        if WIN:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x80)
        self.levels = [0.0] * 14
        self.visible = False
        self.frame = 0

    def tick(self, enabled, status, level):
        show = enabled and status in ("recording", "processing")
        if show != self.visible:
            if LINUX and show:
                self.win.deiconify()
            elif LINUX:
                self.win.withdraw()
            self.win.attributes("-alpha", 0.94 if show else 0.0)
            self.visible = show
        if not show:
            return
        self.frame += 1
        c, w, h = self.c, self.w, self.h
        c.delete("all")
        c.create_oval(0, 0, h, h, fill=self.BG, outline="")
        c.create_oval(w - h, 0, w, h, fill=self.BG, outline="")
        c.create_rectangle(h / 2, 0, w - h / 2, h, fill=self.BG, outline="")
        if status == "recording":
            self.levels = self.levels[1:] + [min(1.0, level * 14)]
            bw = 3 * self.s
            gap = (w - h - bw * len(self.levels)) / (len(self.levels) - 1)
            for i, v in enumerate(self.levels):
                x = h / 2 + i * (bw + gap)
                bh = max(3 * self.s, v * (h - 14 * self.s))
                c.create_rectangle(x, (h - bh) / 2, x + bw, (h + bh) / 2, fill=COLORS["recording"], outline="")
        else:
            for i in range(3):
                on = (self.frame // 6) % 3 == i
                r = (4 if on else 3) * self.s
                cx = w / 2 + (i - 1) * 14 * self.s
                c.create_oval(cx - r, h / 2 - r, cx + r, h / 2 + r, fill=COLORS["processing"] if on else "#5b6b63", outline="")


class App:
    def __init__(self):
        self.first_run = not os.path.exists(CONFIG_PATH)
        self.cfg = load_config()
        self.history = load_history()
        self.status = self.tray_status = "loading"
        self.ui_status = None
        self.events = queue.Queue()
        self.ui = None
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP)
        if MAC:
            AppKit.NSApplication.sharedApplication().setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        ensure_shortcuts()
        set_window_icon(self.root)
        self.overlay = Overlay(self.root)
        self.engine = Engine(self)
        self.tray = pystray.Icon(
            APP,
            ICONS["loading"],
            f"{APP} · {STATUS_TEXT['loading']}",
            menu=pystray.Menu(
                pystray.MenuItem("Abrir Dicto", lambda: self.post(self.open_window, "home"), default=True),
                pystray.MenuItem("Ajustes…", lambda: self.post(self.open_window, "settings")),
                pystray.MenuItem(
                    "Copiar última transcripción",
                    lambda: pyperclip.copy(self.engine.last_text),
                    enabled=lambda item: bool(self.engine.last_text),
                ),
                pystray.MenuItem("Permisos de macOS…", lambda: self.check_mac_permissions(manual=True), visible=MAC),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", lambda: self.post(self.quit)),
            ),
        )

    def post(self, fn, *args):
        self.events.put((fn, args))

    def pump(self):
        while True:
            try:
                fn, args = self.events.get_nowait()
            except queue.Empty:
                break
            fn(*args)
        status = self.status
        if status != self.tray_status:
            self.tray_status = status
            self.tray.icon = ICONS[status]
            self.tray.title = f"{APP} · {STATUS_TEXT[status]}"
        self.overlay.tick(self.cfg["overlay"], status, self.engine.level)
        info = self.status_info()
        if info != self.ui_status:
            self.ui_status = info
            self.send({"type": "status", "status": info})
        self.root.after(33, self.pump)

    def set_status(self, status):
        self.status = status

    def notify(self, message):
        if MAC:
            subprocess.Popen(
                ["osascript", "-e", "on run argv", "-e", f'display notification (item 1 of argv) with title "{APP}"', "-e", "end run", message]
            )
            return
        if LINUX:
            linux_notify(message)
            return
        try:
            self.tray.notify(message, APP)
        except Exception:
            pass

    def check_mac_permissions(self, manual=False):
        threading.Thread(target=self.mac_permissions, args=(manual,), daemon=True).start()

    def mac_permissions(self, manual=False):
        listen, post = keyboard.listen_allowed(), keyboard.post_allowed()
        print(f"Permisos de macOS: monitorización de entrada={listen}, accesibilidad={post}")
        if listen and post:
            if manual:
                mac_dialog("Dicto tiene todos los permisos que necesita.", ["OK"], icon="note")
            return
        missing = []
        if not listen:
            missing.append("Monitorización de entrada: detectar el atajo de teclado.")
        if not post:
            missing.append("Accesibilidad: pegar el texto con ⌘V.")
        text = (
            "Dicto no puede dictar porque le falta este permiso en Ajustes del Sistema › Privacidad y seguridad:\n\n• "
            + "\n• ".join(missing)
            + "\n\nPuede aparecer como «Dicto» o como «Python». Actívalo y después sal de Dicto y vuelve a abrirlo."
            "\n\nSi ya aparece activado, quítalo de la lista con el botón −, sal de Dicto y vuelve a abrirlo: "
            "reaparecerá apagado. Actívalo y vuelve a abrir Dicto una vez más."
        )
        if mac_dialog(text, ["Ahora no", "Abrir Ajustes"]) == "Abrir Ajustes":
            pane = "Privacy_ListenEvent" if not listen else "Privacy_Accessibility"
            subprocess.Popen(["open", f"x-apple.systempreferences:com.apple.preference.security?{pane}"])

    def on_ready(self):
        if self.first_run:
            self.notify(f"Listo. Mantén pulsado «{self.cfg['hotkey']}» para dictar. Haz clic en el icono para configurarlo.")

    def status_info(self):
        detail = "Parakeet v3 · CPU"
        return {"state": self.status, "label": STATUS_TEXT[self.status], "detail": detail}

    def open_window(self, page="home"):
        if WIN:
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        if self.ui:
            self.send({"type": "focus", "page": page})
            return
        self.ui = subprocess.Popen(
            UI_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=open(LOG_PATH, "a", encoding="utf-8"),
            cwd=HERE,
        )
        self.ui_status = self.status_info()
        self.send(
            {
                "cfg": self.cfg,
                "options": {
                    "modes": [[k, v] for k, v in MODES.items()],
                    "mics": input_devices(),
                    "defaultMic": DEFAULT_MIC,
                },
                "history": self.history,
                "status": self.ui_status,
                "page": page,
                "mac": MAC,
                "windows": WIN,
            }
        )
        threading.Thread(target=self.read_ui, args=(self.ui,), daemon=True).start()

    def read_ui(self, proc):
        for line in proc.stdout:
            self.post(self.on_ui, json.loads(line))
        self.post(self.ui_closed, proc)

    def ui_closed(self, proc):
        if self.ui is proc:
            self.ui = None

    def send(self, msg):
        if not self.ui:
            return
        try:
            self.ui.stdin.write(json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n")
            self.ui.stdin.flush()
        except OSError:
            pass

    def on_ui(self, msg):
        cmd = msg["cmd"]
        if cmd == "apply":
            self.apply({**self.cfg, **msg["cfg"]})
        elif cmd == "capture":
            self.capture_hotkey()
        elif cmd == "delete":
            self.history["items"] = [i for i in self.history["items"] if i["t"] != msg["t"]]
            save_history(self.history)
        elif cmd == "clear":
            self.history["items"] = []
            save_history(self.history)
        elif cmd == "uninstall":
            self.uninstall()

    def capture_hotkey(self):
        self.engine.paused = True

        def worker():
            hk = keyboard.read_hotkey(suppress=False)
            while hotkey_down(hk):
                time.sleep(0.02)
            self.post(self.hotkey_captured, hk)

        threading.Thread(target=worker, daemon=True).start()

    def hotkey_captured(self, hk):
        self.engine.paused = False
        self.apply({**self.cfg, "hotkey": hk})
        self.send({"type": "cfg", "cfg": self.cfg})

    def add_history(self, text, seconds):
        entry = {"t": time.time(), "text": text, "secs": round(seconds, 1)}
        h = self.history
        h["items"] = (h["items"] + [entry])[-HISTORY_LIMIT:]
        h["words"] += len(text.split())
        h["seconds"] += seconds
        save_history(h)
        self.send({"type": "entry", "entry": entry, "words": h["words"], "seconds": h["seconds"]})

    def apply(self, cfg):
        self.cfg = cfg
        save_config(cfg)
        set_autostart(cfg["autostart"])
        self.engine.dirty.set()

    def uninstall(self):
        """Un proceso aparte espera a que Dicto se cierre y borra el programa, el modelo y los datos."""
        set_autostart(False)
        paths, uninstaller, note = uninstall_plan()
        print(f"Desinstalando: {paths} {uninstaller}")
        env = dict(os.environ, DICTO_PID=str(os.getpid()), DICTO_MSG="Dicto se ha desinstalado." + (f"\n\n{note}" if note else ""))
        quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.expanduser("~"))
        if WIN:
            env.update(DICTO_PATHS="|".join(paths), DICTO_UNINSTALLER=uninstaller, DICTO_LINKS="" if FROZEN else "1")
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", UNINSTALL_PS],
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                **quiet,
            )
        else:
            subprocess.Popen(["/bin/sh", "-c", UNINSTALL_SH, "sh", *paths], env=env, start_new_session=True, **quiet)
        self.quit()

    def quit(self):
        if self.ui:
            self.ui.kill()
        self.tray.stop()
        self.root.destroy()
        os._exit(0)

    def run(self):
        if self.first_run:
            save_config(self.cfg)
            self.open_window("settings")
        self.tray.run_detached()
        if MAC:
            keyboard.start()
            self.check_mac_permissions()
        if LINUX and (not keyboard.start() or os.environ.get("XDG_SESSION_TYPE") == "wayland"):
            self.notify(
                "En Wayland, Dicto solo detecta el atajo y pega en aplicaciones XWayland. "
                "Para usarlo en todas, inicia sesión con Xorg (X11)."
            )
        threading.Thread(target=self.engine.run, daemon=True).start()
        self.root.after(33, self.pump)
        self.root.mainloop()


def set_window_icon(win):
    if WIN:
        win.iconbitmap(ICON_PATH)
    elif LINUX and os.path.exists(PNG_PATH):
        win.iconphoto(True, tk.PhotoImage(master=win, file=PNG_PATH))


def mac_dialog(message, buttons, icon="caution"):
    names = ", ".join(json.dumps(b, ensure_ascii=False) for b in buttons)
    r = subprocess.run(
        [
            "osascript",
            "-e", "on run argv",
            "-e", f'display dialog (item 1 of argv) with title "{APP}" with icon {icon} buttons {{{names}}} default button {len(buttons)}',
            "-e", "end run",
            message,
        ],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip().removeprefix("button returned:")


def linux_notify(message):
    try:
        subprocess.Popen(["notify-send", "-a", APP, "-i", "dicto", APP, message])
    except OSError:
        print(message)


def main_posix():
    lock = open(os.path.join(CONFIG_DIR, "dicto.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if LINUX:
            linux_notify("Dicto ya está abierto. Búscalo en la bandeja del sistema.")
            return
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display dialog "Dicto ya está abierto. Búscalo en la barra de menús." with title "{APP}" buttons {{"OK"}} default button 1',
            ]
        )
        return
    App().run()


def main():
    if not WIN:
        main_posix()
        return
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DictoSingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(None, "Dicto ya está abierto. Búscalo en la bandeja del sistema.", APP, 0x40)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().run()
    del mutex


if __name__ == "__main__":
    main()
