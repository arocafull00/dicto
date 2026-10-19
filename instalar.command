#!/bin/bash
cd "$(dirname "$0")" || exit 1

echo
echo "  Dicto · instalación"
echo "  ───────────────────"
echo

finish() {
    echo
    read -n 1 -s -r -p "  Pulsa una tecla para cerrar."
    echo
    exit "$1"
}

fail() {
    echo
    echo "  Algo ha fallado durante la instalación. Revisa los mensajes de arriba."
    finish 1
}

PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys, tkinter; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        PY="$c"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "  No se ha encontrado Python 3.10 o superior con Tkinter."
    echo "  Instálalo desde https://www.python.org/downloads/macos/"
    echo "  (o con Homebrew: brew install python@3.12 python-tk@3.12)"
    echo "  y vuelve a ejecutar este instalador."
    finish 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "  [1/3] Creando el entorno de Python..."
    "$PY" -m venv .venv || fail
else
    echo "  [1/3] Entorno de Python ya creado."
fi

echo "  [2/3] Instalando dependencias. Puede tardar unos minutos..."
.venv/bin/python -m pip install --upgrade pip --quiet --disable-pip-version-check
.venv/bin/python -m pip install -r requirements.txt --disable-pip-version-check || fail

echo "  [3/3] Abriendo Dicto..."
.venv/bin/python -c "import dicto; dicto.ensure_shortcuts()" || fail
open "$HOME/Applications/Dicto.app"

echo
echo "  La primera vez se descarga el modelo de voz (~1,6 GB con el modelo Turbo)."
echo "  Mientras tanto el icono de la barra de menús se verá gris. Cuando se ponga azul, ya puedes dictar."
echo
echo "  macOS te pedirá permisos de Micrófono, Monitorización de entrada y Accesibilidad."
echo "  Concédelos en Ajustes del Sistema › Privacidad y seguridad y vuelve a abrir Dicto."
echo
echo "  Listo. A partir de ahora abre Dicto desde Spotlight, Launchpad o ~/Applications."
finish 0
