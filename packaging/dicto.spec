import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = os.path.dirname(SPECPATH)
ICON = os.path.join(ROOT, "dicto.ico")

binaries = collect_dynamic_libs("ctranslate2")
for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc"):
    binaries += collect_dynamic_libs(pkg)

a = Analysis(
    [os.path.join(ROOT, "dicto.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=collect_data_files("faster_whisper") + [(os.path.join(ROOT, "ui.html"), "."), (ICON, ".")],
    hiddenimports=["ui"],
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
    icon=ICON,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Dicto", upx=False)
