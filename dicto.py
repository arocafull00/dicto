import ctypes
import glob
import json
import os
import plistlib
import queue
import shlex
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

MAC = sys.platform == "darwin"
if MAC:
    import fcntl
else:
    import winreg
    import winsound

APP = "Dicto"
HERE = os.path.dirname(os.path.abspath(__file__))
if MAC:
    CONFIG_DIR = os.path.expanduser(f"~/Library/Application Support/{APP}")
else:
    CONFIG_DIR = os.path.join(os.environ["APPDATA"], APP)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "dicto.log")
ICON_PATH = os.path.join(HERE, "dicto.ico")
PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
BUNDLE_ID = "io.github.arocafull00.dicto"
APP_BUNDLE = os.path.expanduser(f"~/Applications/{APP}.app")
LAUNCH_AGENT = os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")
RATE = 16000

os.makedirs(CONFIG_DIR, exist_ok=True)
if sys.stdout is None or sys.stderr is None:
    sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
    os.add_dll_directory(d)
    os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw

if MAC:
    import AppKit
    import mackeys as keyboard
else:
    import keyboard

TITLE_FONT = ("Helvetica Neue", 18, "bold") if MAC else ("Segoe UI Semibold", 16)
HOTKEY_FONT = ("Helvetica Neue", 13, "bold") if MAC else ("Segoe UI Semibold", 10)

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

COLORS = {"loading": "#8a8f98", "idle": "#2f6fed", "recording": "#e5484d", "processing": "#f5a524"}
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


def make_icon(color, size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64
    w = max(2, round(4 * s))
    d.ellipse((1 * s, 1 * s, 63 * s, 63 * s), fill=color)
    d.rounded_rectangle((25 * s, 12 * s, 39 * s, 36 * s), radius=7 * s, fill="white")
    d.arc((18 * s, 20 * s, 46 * s, 44 * s), 0, 180, fill="white", width=w)
    d.line((32 * s, 44 * s, 32 * s, 51 * s), fill="white", width=w)
    d.line((24 * s, 51 * s, 40 * s, 51 * s), fill="white", width=w)
    return img


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
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, f'"{PYTHONW}" "{os.path.join(HERE, "dicto.py")}"')
        else:
            try:
                winreg.DeleteValue(k, APP)
            except FileNotFoundError:
                pass


def ensure_mac_app():
    contents = os.path.join(APP_BUNDLE, "Contents")
    if os.path.exists(contents):
        return
    os.makedirs(os.path.join(contents, "MacOS"))
    os.makedirs(os.path.join(contents, "Resources"))
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
            f"exec {shlex.quote(sys.executable)} {shlex.quote(os.path.join(HERE, 'dicto.py'))}"
            f" >> {shlex.quote(LOG_PATH)} 2>&1\n"
        )
    os.chmod(launcher, 0o755)
    try:
        make_icon(COLORS["idle"], 1024).save(os.path.join(contents, "Resources", "dicto.icns"))
    except Exception as e:
        print(f"No se pudo crear el icono de la app: {e}")


def ensure_shortcuts():
    if MAC:
        ensure_mac_app()
        return
    if not os.path.exists(ICON_PATH):
        make_icon(COLORS["idle"], 256).save(ICON_PATH, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
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
    if not MAC:
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
            print(text)
        self.app.set_status("idle")


class Overlay:
    KEY = "#010203"
    BG = "#1c1c1f"

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
        if not MAC:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x80)
        self.levels = [0.0] * 14
        self.visible = False
        self.frame = 0

    def tick(self, enabled, status, level):
        show = enabled and status in ("recording", "processing")
        if show != self.visible:
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
                c.create_oval(cx - r, h / 2 - r, cx + r, h / 2 + r, fill=COLORS["processing"] if on else "#6b6b70", outline="")


class Settings:
    def __init__(self, app):
        self.app = app
        cfg = app.cfg
        win = self.win = tk.Toplevel(app.root)
        win.title("Dicto · Configuración")
        set_window_icon(win)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.close)

        self.hotkey = tk.StringVar(value=cfg["hotkey"])
        self.mode = tk.StringVar(value=key_for(MODES, cfg["mode"]))
        self.language = tk.StringVar(value=key_for(LANGUAGES, cfg["language"]))
        self.model = tk.StringVar(value=key_for(MODELS, cfg["model"]))
        self.device = tk.StringVar(value=cfg["device"] or DEFAULT_MIC)
        self.vocabulary = tk.StringVar(value=cfg["vocabulary"])
        self.sounds = tk.BooleanVar(value=cfg["sounds"])
        self.overlay = tk.BooleanVar(value=cfg["overlay"])
        self.autostart = tk.BooleanVar(value=cfg["autostart"])

        f = ttk.Frame(win, padding=(22, 18, 22, 18))
        f.grid(sticky="nsew")
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Dicto", font=TITLE_FONT).grid(row=0, column=0, columnspan=3, sticky="w")
        self.status = ttk.Label(f, foreground="#6b6b70")
        self.status.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        r = 2
        ttk.Label(f, text="Atajo").grid(row=r, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Label(f, textvariable=self.hotkey, font=HOTKEY_FONT).grid(row=r, column=1, sticky="w")
        self.capture_btn = ttk.Button(f, text="Cambiar…", command=self.capture)
        self.capture_btn.grid(row=r, column=2, sticky="e")

        for label, var, values in (
            ("Modo", self.mode, list(MODES)),
            ("Idioma", self.language, list(LANGUAGES)),
            ("Modelo", self.model, list(MODELS)),
            ("Micrófono", self.device, [DEFAULT_MIC] + input_devices()),
        ):
            r += 1
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 14))
            ttk.Combobox(f, textvariable=var, values=values, state="readonly", width=40).grid(
                row=r, column=1, columnspan=2, sticky="ew"
            )

        r += 1
        ttk.Label(f, text="Vocabulario").grid(row=r, column=0, sticky="w", pady=(5, 0), padx=(0, 14))
        ttk.Entry(f, textvariable=self.vocabulary, width=42).grid(row=r, column=1, columnspan=2, sticky="ew", pady=(5, 0))
        r += 1
        ttk.Label(f, text="Nombres o términos que suele escribir mal, separados por comas", foreground="#6b6b70").grid(
            row=r, column=1, columnspan=2, sticky="w", pady=(2, 10)
        )

        for text, var in (
            ("Sonidos al empezar y terminar", self.sounds),
            ("Mostrar indicador mientras grabo", self.overlay),
            ("Iniciar al iniciar sesión" if MAC else "Iniciar con Windows", self.autostart),
        ):
            r += 1
            ttk.Checkbutton(f, text=text, variable=var).grid(row=r, column=0, columnspan=3, sticky="w", pady=2)

        r += 1
        buttons = ttk.Frame(f)
        buttons.grid(row=r, column=0, columnspan=3, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Cancelar", command=self.close).pack(side="right")
        ttk.Button(buttons, text="Guardar", command=self.save, default="active").pack(side="right", padx=(0, 8))

        self.refresh_status()
        win.update_idletasks()
        x = (win.winfo_screenwidth() - win.winfo_width()) // 2
        y = (win.winfo_screenheight() - win.winfo_height()) // 3
        win.geometry(f"+{x}+{y}")
        win.lift()
        win.focus_force()

    def refresh_status(self):
        if not self.win.winfo_exists():
            return
        device = "GPU" if self.app.engine.model is not None and self.app.engine.model.model.device == "cuda" else "CPU"
        text = STATUS_TEXT[self.app.status]
        if self.app.status != "loading":
            text += f" · {self.app.engine.model_name} en {device}"
        self.status.configure(text=text)
        self.win.after(500, self.refresh_status)

    def capture(self):
        self.app.engine.paused = True
        self.capture_btn.state(["disabled"])
        self.hotkey.set("Pulsa la combinación…")

        def worker():
            hk = keyboard.read_hotkey(suppress=False)
            while hotkey_down(hk):
                time.sleep(0.02)
            self.app.post(self.captured, hk)

        threading.Thread(target=worker, daemon=True).start()

    def captured(self, hk):
        self.hotkey.set(hk)
        self.capture_btn.state(["!disabled"])
        self.app.engine.paused = False

    def save(self):
        hk = self.hotkey.get()
        if hk.startswith("Pulsa"):
            return
        mic = self.device.get()
        self.app.apply(
            {
                "hotkey": hk,
                "mode": MODES[self.mode.get()],
                "language": LANGUAGES[self.language.get()],
                "model": MODELS[self.model.get()],
                "device": "" if mic == DEFAULT_MIC else mic,
                "vocabulary": self.vocabulary.get(),
                "sounds": self.sounds.get(),
                "overlay": self.overlay.get(),
                "autostart": self.autostart.get(),
            }
        )
        self.close()

    def close(self):
        self.app.engine.paused = False
        self.win.destroy()
        self.app.settings = None


def key_for(mapping, value):
    return next((k for k, v in mapping.items() if v == value), next(iter(mapping)))


class App:
    def __init__(self):
        self.first_run = not os.path.exists(CONFIG_PATH)
        self.cfg = load_config()
        self.status = self.tray_status = "loading"
        self.events = queue.Queue()
        self.settings = None
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
                pystray.MenuItem("Configuración…", lambda: self.post(self.open_settings), default=True),
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
        self.root.after(33, self.pump)

    def set_status(self, status):
        self.status = status

    def notify(self, message):
        if MAC:
            subprocess.Popen(
                ["osascript", "-e", "on run argv", "-e", f'display notification (item 1 of argv) with title "{APP}"', "-e", "end run", message]
            )
            return
        try:
            self.tray.notify(message, APP)
        except Exception:
            pass

    def on_ready(self):
        if self.first_run:
            self.notify(f"Listo. Mantén pulsado «{self.cfg['hotkey']}» para dictar. Haz clic en el icono para configurarlo.")

    def open_settings(self):
        if MAC:
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        if self.settings:
            self.settings.win.lift()
            self.settings.win.focus_force()
        else:
            self.settings = Settings(self)

    def apply(self, cfg):
        self.cfg = cfg
        save_config(cfg)
        set_autostart(cfg["autostart"])
        self.engine.dirty.set()

    def quit(self):
        self.tray.stop()
        self.root.destroy()
        os._exit(0)

    def run(self):
        if self.first_run:
            save_config(self.cfg)
            self.open_settings()
        self.tray.run_detached()
        if MAC and not keyboard.start():
            self.notify(
                "Dicto necesita permiso de Monitorización de entrada y Accesibilidad. "
                "Actívalo en Ajustes del Sistema › Privacidad y seguridad y vuelve a abrir Dicto."
            )
        threading.Thread(target=self.engine.run, daemon=True).start()
        self.root.after(33, self.pump)
        self.root.mainloop()


def set_window_icon(win):
    if not MAC:
        win.iconbitmap(ICON_PATH)


def main_mac():
    lock = open(os.path.join(CONFIG_DIR, "dicto.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
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
    if MAC:
        main_mac()
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
