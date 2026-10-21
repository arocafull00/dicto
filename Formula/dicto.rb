class Dicto < Formula
  desc "Dictado por voz 100 % local con Whisper"
  homepage "https://github.com/arocafull00/dicto"
  head "https://github.com/arocafull00/dicto.git", branch: "main"

  depends_on :macos
  depends_on "python-tk@3.12"
  depends_on "python@3.12"

  def install
    libexec.install "dicto.py", "ui.py", "ui.html", "mackeys.py", "dicto.ico", "assets", "requirements.txt"
    (bin/"dicto").write <<~EOS
      #!/bin/bash
      set -e
      VENV="$HOME/Library/Application Support/Dicto/venv"
      if [ ! -x "$VENV/bin/python" ]; then
        echo "Preparando Dicto por primera vez. Puede tardar unos minutos..."
        "#{Formula["python@3.12"].opt_bin}/python3.12" -m venv "$VENV"
      fi
      if ! cmp -s "#{opt_libexec}/requirements.txt" "$VENV/requirements.txt"; then
        "$VENV/bin/python" -m pip install --upgrade pip --quiet --disable-pip-version-check
        "$VENV/bin/python" -m pip install -r "#{opt_libexec}/requirements.txt" --disable-pip-version-check
        cp "#{opt_libexec}/requirements.txt" "$VENV/requirements.txt"
      fi
      cd "#{opt_libexec}"
      "$VENV/bin/python" -c "import dicto; dicto.ensure_shortcuts()"
      open "$HOME/Applications/Dicto.app"
    EOS
  end

  def caveats
    <<~EOS
      Ejecuta `dicto` una vez para terminar la instalación: crea el entorno de Python,
      instala las dependencias y añade Dicto.app a ~/Applications.

      macOS pedirá permisos de Micrófono, Monitorización de entrada y Accesibilidad.
      Concédelos en Ajustes del Sistema › Privacidad y seguridad y vuelve a abrir Dicto.
    EOS
  end

  test do
    assert_path_exists libexec/"dicto.py"
  end
end
