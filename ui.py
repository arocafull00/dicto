import json
import os
import subprocess
import sys
import threading

import pyperclip
import webview

APP = "Dicto"
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = sys.platform == "darwin"
OUT = sys.stdout.buffer
sys.stdout = sys.stderr
lock = threading.Lock()


def send(msg):
    with lock:
        OUT.write(json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n")
        OUT.flush()


def dark_mode():
    try:
        if MAC:
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True)
            return "Dark" in r.stdout
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


class Api:
    def __init__(self, state):
        self._state = state
        self._window = None
        self._listening = False

    def init(self):
        if not self._listening:
            self._listening = True
            threading.Thread(target=self._listen, daemon=True).start()
        return self._state

    def apply(self, cfg):
        send({"cmd": "apply", "cfg": cfg})

    def capture(self):
        send({"cmd": "capture"})

    def copy(self, text):
        pyperclip.copy(text)

    def delete(self, t):
        send({"cmd": "delete", "t": t})

    def clear(self):
        send({"cmd": "clear"})

    def _listen(self):
        for line in sys.stdin.buffer:
            msg = json.loads(line)
            if msg["type"] == "focus":
                self._window.restore()
                self._window.show()
            self._window.evaluate_js(f"dicto.receive({json.dumps(msg, ensure_ascii=False)})")
        self._window.destroy()


def main():
    state = json.loads(sys.stdin.buffer.readline())
    api = Api(state)
    with open(os.path.join(HERE, "ui.html"), encoding="utf-8") as f:
        html = f.read()
    api._window = webview.create_window(
        APP,
        html=html,
        js_api=api,
        text_select=True,
        width=1040,
        height=720,
        min_size=(760, 520),
        background_color="#121b17" if dark_mode() else "#F5F7F2",
    )
    webview.start(icon=os.path.join(HERE, "dicto.ico"))
    os._exit(0)


if __name__ == "__main__":
    main()
