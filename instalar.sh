#!/bin/bash
cd "$(dirname "$0")" || exit 1

echo
echo "  Dicto · instalación"
echo "  ───────────────────"
echo

fail() {
    echo
    echo "  Algo ha fallado durante la instalación. Revisa los mensajes de arriba."
    exit 1
}

echo "  [1/4] Instalando dependencias del sistema (puede pedir tu contraseña)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq
    WEBKIT=gir1.2-webkit2-4.1
    apt-cache show "$WEBKIT" >/dev/null 2>&1 || WEBKIT=gir1.2-webkit2-4.0
    sudo apt-get install -y python3-venv python3-tk python3-gi python3-evdev gir1.2-gtk-3.0 "$WEBKIT" \
        gir1.2-ayatanaappindicator3-0.1 libportaudio2 xclip libnotify-bin || fail
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3-tkinter python3-gobject python3-evdev gtk3 webkit2gtk4.1 \
        libayatana-appindicator-gtk3 portaudio xclip libnotify || fail
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python tk python-gobject python-evdev gtk3 webkit2gtk-4.1 \
        libayatana-appindicator portaudio xclip libnotify || fail
elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3-tk python3-gobject-Gdk python3-evdev typelib-1_0-WebKit2-4_1 \
        typelib-1_0-AyatanaAppIndicator3-0_1 portaudio xclip libnotify-tools || fail
else
    echo "  No reconozco tu gestor de paquetes. Instala a mano: Python 3.10+ con Tkinter,"
    echo "  PyGObject, WebKit2GTK, AppIndicator, PortAudio, xclip y notify-send."
fi

if ! python3 -c 'import sys, tkinter, gi; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    echo "  Hace falta Python 3.10 o superior con Tkinter y PyGObject."
    fail
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "  [2/4] Creando el entorno de Python..."
    python3 -m venv --system-site-packages .venv || fail
else
    echo "  [2/4] Entorno de Python ya creado."
fi

echo "  [3/4] Instalando dependencias. Puede tardar unos minutos..."
.venv/bin/python -m pip install --upgrade pip --quiet --disable-pip-version-check
.venv/bin/python -m pip install -r requirements.txt --disable-pip-version-check || fail

echo "  [4/4] Abriendo Dicto..."
.venv/bin/python -c "import dicto; dicto.ensure_shortcuts()" || fail
nohup .venv/bin/python dicto.py >/dev/null 2>&1 &

echo
echo "  La primera vez se descarga el modelo de voz (~1,6 GB con el modelo Turbo)."
echo "  Mientras tanto el icono de la bandeja se verá gris. Cuando se ponga verde, ya puedes dictar."
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    echo
    echo "  Estás en una sesión Wayland: el atajo y el pegado solo funcionan en aplicaciones XWayland."
    echo "  Para usar Dicto en todas, cierra sesión y entra con «Xorg» (o «X11»)."
fi
echo
echo "  Listo. A partir de ahora abre Dicto desde el menú de aplicaciones."
