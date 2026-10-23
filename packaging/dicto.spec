import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

MAC = sys.platform == "darwin"
ROOT = os.path.dirname(SPECPATH)
ICON = os.path.join(ROOT, "dicto.ico")
ICNS = os.path.join(ROOT, "assets", "dicto.icns")

binaries = collect_dynamic_libs("ctranslate2")
datas = collect_data_files("faster_whisper") + [(os.path.join(ROOT, "ui.html"), "."), (ICON, ".")]
hiddenimports = ["ui"]
if MAC:
    datas.append((ICNS, "assets"))
    hiddenimports += ["pystray._darwin", "webview.platforms.cocoa"]

a = Analysis(
    [os.path.join(ROOT, "dicto.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["matplotlib", "pandas", "scipy", "torch", "IPython", "pytest"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [("X utf8", None, "OPTION")],
    exclude_binaries=True,
    name="Dicto",
    console=False,
    icon=ICNS if MAC else ICON,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Dicto", upx=False)

if MAC:
    app = BUNDLE(
        coll,
        name="Dicto.app",
        icon=ICNS,
        bundle_identifier="io.github.arocafull00.dicto",
        version=os.environ.get("DICTO_VERSION", "0.0.0"),
        info_plist={
            "CFBundleDisplayName": "Dicto",
            "LSUIElement": True,
            "LSMinimumSystemVersion": "12.0",
            "NSMicrophoneUsageDescription": "Dicto usa el micrófono para transcribir lo que dictas.",
        },
    )
