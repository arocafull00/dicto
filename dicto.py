import ctypes
import glob
import json
import os
import plistlib
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import zipfile

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
PACKAGES = getattr(sys, "_MEIPASS", os.path.join(sys.prefix, "Lib", "site-packages"))
CUDA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", CONFIG_DIR), APP, "cuda")
CUDA_PACKAGES = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12", "nvidia-cuda-nvrtc-cu12"]
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

os.makedirs(CONFIG_DIR, exist_ok=True)
if sys.stdout is None or sys.stderr is None:
    sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)


def add_cuda_dirs():
    for d in glob.glob(os.path.join(PACKAGES, "nvidia", "*", "bin")) + glob.glob(os.path.join(CUDA_DIR, "nvidia", "*", "bin")):
        if d not in os.environ["PATH"]:
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


def cuda_ready():
    return any(glob.glob(os.path.join(root, "nvidia", "cudnn", "bin", "cudnn64_*.dll")) for root in (PACKAGES, CUDA_DIR))


def has_nvidia():
    return os.path.exists(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvcuda.dll"))


def download_cuda():
    tmp = CUDA_DIR + ".partial"
    os.makedirs(tmp, exist_ok=True)
    for name in CUDA_PACKAGES:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as r:
            files = json.load(r)["urls"]
        url = next(f["url"] for f in files if f["filename"].endswith("win_amd64.whl"))
        wheel = os.path.join(tmp, name + ".whl")
        urllib.request.urlretrieve(url, wheel)
        with zipfile.ZipFile(wheel) as z:
            z.extractall(tmp, [m for m in z.namelist() if m.startswith("nvidia/") and m.lower().endswith(".dll")])
        os.remove(wheel)
    os.replace(tmp, CUDA_DIR)


if WIN:
    add_cuda_dirs()

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from faster_whisper import WhisperModel
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
    "language": "es",
    "model": "large-v3-turbo",
    "device": "",
    "vocabulary": "",
    "sounds": True,
    "overlay": True,
    "autostart": False,
}

MODES = {"Mantener pulsado": "hold", "Pulsar para empezar y parar": "toggle"}
LANGUAGES = {
    "Español": "es",
    "English": "en",
    "Català": "ca",
    "Português": "pt",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Detectar automáticamente": "auto",
}
MODELS = {
    "Turbo · rápido y preciso (recomendado)": "large-v3-turbo",
    "Large v3 · máxima precisión, más lento": "large-v3",
    "Medium": "medium",
    "Small · ligero": "small",
    "Base · muy ligero": "base",
}
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
            "Comment=Dictado por voz 100 % local con Whisper\n"
            f"Exec={shlex.join(LAUNCH)}\n"
            "Icon=dicto\n"
            "Terminal=false\n"
            "Categories=Utility;Accessibility;AudioVideo;\n"
            "Keywords=dictado;voz;whisper;transcripción;\n"
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
        "$l.Description = 'Dictado local con Whisper'; $l.Save() }"
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
    time.sleep(0.3)
    if previous is not None:
        pyperclip.copy(previous)


def load_model(name):
    if (WIN and cuda_ready()) or (LINUX and shutil.which("nvidia-smi")):
        try:
            return WhisperModel(name, device="cuda", compute_type="float16")
        except Exception as e:
            print(f"GPU no disponible ({e}); usando CPU.")
    return WhisperModel(name, device="cpu", compute_type="int8")


class Engine:
    def __init__(self, app):
        self.app = app
        self.model = None
        self.model_name = None
        self.stream = None
        self.device = None
        self.chunks = []
        self.recording = False
        self.level = 0.0
        self.paused = False
        self.dirty = threading.Event()
        self.last_text = ""

    def get_cuda(self):
        self.app.notify("Tienes una GPU NVIDIA. Descargando el soporte de GPU (~1,3 GB) en segundo plano; mientras tanto Dicto usa la CPU.")
        try:
            download_cuda()
        except Exception as e:
            print(f"No se pudo descargar el soporte de GPU: {e}")
            return
        add_cuda_dirs()
        self.model_name = None
        self.dirty.set()
        self.app.notify("Soporte de GPU listo. Dicto ya usa tu NVIDIA.")

    def configure(self):
        cfg = self.app.cfg
        if cfg["model"] != self.model_name:
            self.app.set_status("loading")
            self.model = None
            self.model = load_model(cfg["model"])
            self.model_name = cfg["model"]
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

    def run(self):
        try:
            self.configure()
        except Exception as e:
            self.app.notify(f"No se pudo iniciar: {e}")
            raise
        self.app.on_ready()
        if WIN and not cuda_ready() and has_nvidia():
            threading.Thread(target=self.get_cuda, daemon=True).start()
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
            time.sleep(0.02)

    def start(self):
        self.chunks = []
        self.level = 0.0
        self.recording = True
        self.app.set_status("recording")
        if self.app.cfg["sounds"]:
            beep(True)

    def stop(self):
        cfg = self.app.cfg
        self.recording = False
        if cfg["sounds"]:
            beep(False)
        audio = np.concatenate(self.chunks) if self.chunks else np.zeros(0, np.float32)
        if len(audio) < RATE * 0.3:
            self.app.set_status("idle")
            return
        self.app.set_status("processing")
        text = ""
        try:
            segments, _ = self.model.transcribe(
                audio,
                language=None if cfg["language"] == "auto" else cfg["language"],
                beam_size=5,
                vad_filter=True,
                initial_prompt=cfg["vocabulary"].strip() or None,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:
            self.app.notify(f"Error al transcribir: {e}")
        if text:
            while hotkey_down(cfg["hotkey"]):
                time.sleep(0.02)
            paste(text + " ")
            self.last_text = text
            self.app.post(self.app.add_history, text, len(audio) / RATE)
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

    def on_ready(self):
        if self.first_run:
            self.notify(f"Listo. Mantén pulsado «{self.cfg['hotkey']}» para dictar. Haz clic en el icono para configurarlo.")

    def status_info(self):
        model = self.engine.model
        if self.status == "loading" or model is None:
            detail = self.cfg["model"]
        else:
            detail = f"{self.engine.model_name} · {'GPU' if model.model.device == 'cuda' else 'CPU'}"
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
                    "languages": [[k, v] for k, v in LANGUAGES.items()],
                    "models": [[k, v] for k, v in MODELS.items()],
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
        if MAC and not keyboard.start():
            self.notify(
                "Dicto necesita permiso de Monitorización de entrada y Accesibilidad. "
                "Actívalo en Ajustes del Sistema › Privacidad y seguridad y vuelve a abrir Dicto."
            )
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
