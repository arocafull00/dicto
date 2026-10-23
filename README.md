<div align="center">

<img src="assets/dicto.png" width="112" alt="Dicto">

# Dicto

**Dictado por voz para Windows, macOS y Linux, 100 % local.**
Mantén pulsada una tecla, habla y suelta: el texto aparece donde esté el cursor.

<p>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/macOS-12%2B-000000?logo=apple&logoColor=white" alt="macOS">
  <img src="https://img.shields.io/badge/Linux-X11-FCC624?logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/Homebrew-tap-FBB040?logo=homebrew&logoColor=white" alt="Homebrew">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Whisper-faster--whisper-111111" alt="faster-whisper">
  <img src="https://img.shields.io/badge/GPU-CUDA%20opcional-76B900?logo=nvidia&logoColor=white" alt="CUDA">
  <img src="https://img.shields.io/badge/privacidad-sin%20nube-2f6fed" alt="Sin nube">
</p>

</div>

---

## ✨ Qué hace

Dicto vive en la bandeja del sistema (Windows y Linux) o en la barra de menús (macOS) y convierte tu voz en texto en **cualquier aplicación**: el navegador, Word, Slack, tu editor de código, la terminal… Usa [Whisper](https://github.com/openai/whisper) a través de [faster-whisper](https://github.com/SYSTRAN/faster-whisper), así que la transcripción se hace en tu propio ordenador: **ningún audio sale de tu equipo**.

- 💻 **Windows, Mac y Linux.** Mismo funcionamiento en Windows 10/11, macOS (Intel y Apple Silicon) y Linux con X11.
- 🎙️ **Pulsar y hablar.** Mantén `Ctrl derecho` en Windows y Linux u `Opción derecha` en Mac (o el atajo que elijas), habla y suelta. El texto se pega solo.
- 🔁 **Dos modos.** *Mantener pulsado* o *pulsar para empezar y parar*, para dictados largos.
- ⚡ **Rápido con GPU.** En Windows usa CUDA si tienes una NVIDIA, y en Linux si además tienes CUDA 12 y cuDNN 9 instalados; si no (y siempre en Mac), funciona en CPU sin tocar nada.
- 🌍 **Multilingüe.** Español, inglés, catalán, portugués, francés, alemán, italiano o detección automática.
- 📚 **Diccionario propio.** Enséñale nombres, marcas o términos técnicos que suele escribir mal.
- 🗂️ **Historial.** Tus últimas 500 transcripciones, agrupadas por día y listas para copiar, con estadísticas de palabras, velocidad y racha.
- 🟢 **Indicador flotante.** Una pequeña píldora muestra el nivel del micrófono mientras grabas y avisa cuando transcribe.
- 🔔 **Sonidos sutiles** al empezar y terminar de grabar.
- 📋 **Respeta tu portapapeles.** Pega el texto y después restaura lo que tenías copiado.
- 🚀 **Inicio automático** opcional, con accesos directos en el menú Inicio y el escritorio (Windows), `Dicto.app` en Spotlight y Launchpad (Mac) o una entrada en el menú de aplicaciones (Linux).

## 🧭 Cómo funciona

```text
  tecla pulsada ──► micrófono (16 kHz) ──► tecla suelta
                                              │
                                              ▼
                         Whisper local (GPU / CPU) + filtro de silencios
                                              │
                                              ▼
                          texto ──► portapapeles ──► Ctrl+V / ⌘V en la app activa
```

El icono de la bandeja (o de la barra de menús) cambia de color según el estado:

| Color | Estado |
| :---: | --- |
| ⚪ Gris | Cargando el modelo |
| 🟢 Verde | Listo para dictar |
| 🔴 Rojo | Escuchando |
| 🟠 Naranja | Transcribiendo |

## 📦 Instalación

Elige tu sistema:

- [🪟 Windows](#-windows)
- [🍎 macOS](#-macos) *(Apple Silicon)*
- [🍎 macOS con Homebrew](#-macos-con-homebrew) *(Intel o Apple Silicon)*
- [🍎 macOS sin Homebrew](#-macos-sin-homebrew)
- [🐧 Linux](#-linux)

### 🪟 Windows

Descarga **[Dicto-Windows-Setup.exe](https://github.com/arocafull00/dicto/releases/latest/download/Dicto-Windows-Setup.exe)**, ábrelo y pulsa *Siguiente*. No hace falta instalar Python ni tener permisos de administrador. Si Windows muestra «Windows protegió su PC», pulsa *Más información* → *Ejecutar de todas formas*.

<details>
<summary><b>Instalar desde el código fuente</b></summary>

**Requisitos:** Windows 10/11, [Python 3.10 o superior](https://www.python.org/downloads/) (marca *Add python.exe to PATH* al instalarlo) y un micrófono. Una GPU NVIDIA es opcional pero muy recomendable.

1. Descarga el proyecto: botón verde **Code → Download ZIP** y descomprímelo, o con Git:

   ```bash
   git clone https://github.com/arocafull00/dicto.git
   ```

2. Abre **`instalar.bat`** con doble clic. Crea el entorno de Python, instala las dependencias (con soporte CUDA solo si detecta una GPU NVIDIA) y abre Dicto.

¡Y ya está! A partir de ahí, abre Dicto desde el acceso directo del menú Inicio o del escritorio.

**Instalación manual:**

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements.txt
```

Sin GPU NVIDIA puedes quitar antes `nvidia-cublas-cu12` y `nvidia-cudnn-cu12` de `requirements.txt`. Después, abre `dicto.bat`.

Para generar el instalador: `pyinstaller --noconfirm packaging/dicto.spec` y después `iscc packaging\dicto.iss` ([Inno Setup](https://jrsoftware.org/isinfo.php)). El flujo `.github/workflows/build.yml` lo hace solo al subir una etiqueta `v*` y crea un borrador de *release* con `Dicto-Windows-Setup.exe` y `Dicto-macOS.dmg`. El instalador no incluye CUDA: si Dicto detecta una GPU NVIDIA, descarga cuBLAS y cuDNN (~1,3 GB) la primera vez que se abre, en `%LOCALAPPDATA%\Dicto\cuda`, y mientras tanto funciona en CPU.

</details>

### 🍎 macOS

**Requisitos:** macOS 12 o superior en un Mac con Apple Silicon (M1 o posterior) y un micrófono. En un Mac Intel, usa [Homebrew](#-macos-con-homebrew).

1. Descarga **[Dicto-macOS.dmg](https://github.com/arocafull00/dicto/releases/latest/download/Dicto-macOS.dmg)**, ábrelo y arrastra **Dicto** a la carpeta **Aplicaciones**.
2. Abre Dicto. Como la app no está firmada por Apple, macOS no la dejará abrir la primera vez: ve a **Ajustes del Sistema › Privacidad y seguridad**, baja hasta el aviso sobre Dicto y pulsa **Abrir igualmente**.
3. Concede los [permisos](#-permisos-en-macos) que pida. No hace falta instalar Python ni usar la Terminal.

### 🍎 macOS con Homebrew

**Requisitos:** macOS 12 o superior (Intel o Apple Silicon), [Homebrew](https://brew.sh) y un micrófono.

```bash
brew tap arocafull00/dicto https://github.com/arocafull00/dicto
```

```bash
brew install --HEAD dicto
```

```bash
dicto
```

El primer `dicto` prepara el entorno de Python (unos minutos), crea **`Dicto.app`** en `~/Applications` y la abre. A partir de ahí, ábrela desde Spotlight o Launchpad como cualquier otra app.

Para actualizar, `brew upgrade --fetch-HEAD dicto` y vuelve a ejecutar `dicto`.

### 🍎 macOS sin Homebrew

**Requisitos:** macOS 12 o superior, [Python 3.10 o superior de python.org](https://www.python.org/downloads/macos/) (incluye Tkinter) y un micrófono.

1. Descarga el proyecto (**Code → Download ZIP**) o clónalo con Git.
2. Abre **`instalar.command`** con doble clic. Si macOS dice que no puede abrirlo porque es de un desarrollador no identificado, haz clic derecho → **Abrir**, o ejecútalo desde la Terminal:

   ```bash
   bash instalar.command
   ```

3. El instalador crea el entorno de Python, instala las dependencias y abre **`Dicto.app`** desde `~/Applications`.

### 🔐 Permisos en macOS

La primera vez, macOS pedirá tres permisos para **Dicto** (en algunos sistemas aparece como **Python**). Actívalos en **Ajustes del Sistema › Privacidad y seguridad** y vuelve a abrir Dicto:

| Permiso | Para qué |
| --- | --- |
| **Micrófono** | Grabar tu voz. |
| **Monitorización de entrada** | Detectar el atajo de teclado en cualquier app. |
| **Accesibilidad** | Pegar el texto (⌘V) en la app activa. |

> [!NOTE]
> En Mac no hay CUDA, así que Whisper se ejecuta en la CPU. En Apple Silicon el modelo Turbo va bien; en Macs Intel elige *Small* o *Base* para que vaya fluido.

### 🐧 Linux

**Requisitos:** una distribución con `apt` (Ubuntu, Debian, Mint…), `dnf` (Fedora), `pacman` (Arch) o `zypper` (openSUSE), sesión **X11** y un micrófono.

```bash
git clone https://github.com/arocafull00/dicto.git
```

```bash
bash dicto/instalar.sh
```

El instalador pide tu contraseña para instalar las dependencias del sistema (Tkinter, PyGObject, WebKit2GTK, AppIndicator, PortAudio, `xclip` y `notify-send`), crea el entorno de Python, añade Dicto al menú de aplicaciones y lo abre. No hay paquete precompilado: Dicto se ejecuta desde la carpeta que has clonado, así que no la borres. Para actualizar, `git pull` dentro de ella.

> [!WARNING]
> Dicto necesita X11 para detectar el atajo y pegar el texto. En una sesión **Wayland** (la predeterminada en Ubuntu y Fedora con GNOME) solo funciona en aplicaciones XWayland. Para usarlo en todas, cierra sesión y, en la pantalla de inicio, elige **Ubuntu en Xorg** (o la opción *X11* de tu escritorio).

En GNOME, el icono de la bandeja necesita la extensión *AppIndicator*, que Ubuntu ya trae activada.

### La primera vez que se abre

1. **Se descarga el modelo de voz** desde Hugging Face, una sola vez. Con el modelo Turbo son unos **1,6 GB**, así que puede tardar varios minutos: mientras tanto el icono se ve ⚪ gris. Cuando se pone 🟢 verde, ya puedes dictar.
2. Se crean los accesos directos: menú Inicio y escritorio en Windows, `~/Applications/Dicto.app` en Mac y el menú de aplicaciones en Linux.
3. Se abre la ventana de Dicto en *Ajustes* para que elijas el atajo, el idioma y el micrófono.

> [!NOTE]
> Los modelos se guardan en `~/.cache/huggingface` (`%USERPROFILE%\.cache\huggingface` en Windows). Si cambias de modelo en la configuración, el nuevo se descarga la primera vez que lo uses. Después, Dicto funciona sin internet.

> [!TIP]
> Sin GPU, Dicto funciona en CPU automáticamente. Elige un modelo más ligero (*Small* o *Base*) para que vaya fluido.

## 🎛️ Configuración

Haz clic en el icono de la bandeja (Windows y Linux) o de la barra de menús (Mac) para abrir Dicto. La ventana tiene tres secciones y sigue el tema claro u oscuro del sistema:

- **Inicio:** tus estadísticas (palabras dictadas, palabras por minuto y días seguidos) y el historial de transcripciones agrupado por día. Pasa el ratón por una para copiarla o borrarla.
- **Diccionario:** nombres, marcas o términos que Whisper debe reconocer mejor.
- **Ajustes:** todo lo demás. Los cambios se guardan al momento.

| Opción | Descripción |
| --- | --- |
| **Atajo** | Cualquier tecla o combinación. Pulsa *Cambiar* y presiónala. |
| **Modo** | *Mantener pulsado* o *Pulsar para empezar y parar*. |
| **Idioma** | Idioma del dictado o detección automática. |
| **Modelo** | Turbo (recomendado), Large v3, Medium, Small o Base. |
| **Micrófono** | El predeterminado del sistema o uno concreto. |
| **Opciones** | Sonidos, indicador flotante e inicio automático al encender. |

Desde el menú del icono también puedes **copiar la última transcripción** o salir.

Los ajustes se guardan en `config.json`, el historial en `history.json` y el registro de actividad en `dicto.log`, dentro de:

- **Windows:** `%APPDATA%\Dicto\`
- **macOS:** `~/Library/Application Support/Dicto/`
- **Linux:** `~/.config/Dicto/`

## 🧠 Modelos

| Modelo | Descarga | Velocidad | Precisión | Ideal para |
| --- | :---: | :---: | :---: | --- |
| `large-v3-turbo` | ~1,6 GB | ⚡⚡⚡ | ★★★★ | Uso diario con GPU o Apple Silicon *(por defecto)* |
| `large-v3` | ~3 GB | ⚡ | ★★★★★ | Máxima precisión |
| `medium` | ~1,5 GB | ⚡⚡ | ★★★ | GPUs modestas |
| `small` | ~500 MB | ⚡⚡⚡ | ★★ | CPU |
| `base` | ~150 MB | ⚡⚡⚡⚡ | ★ | Equipos muy ligeros |

## 🔒 Privacidad

La transcripción ocurre en tu máquina, sin cuentas, telemetría ni envío de audio al mantenedor. Dicto descarga los modelos desde Hugging Face y, en Windows con GPU NVIDIA, puede descargar bibliotecas CUDA desde PyPI. Una vez disponibles el modelo y las dependencias, el dictado funciona sin conexión.

El historial, los ajustes y los contadores se guardan localmente. El archivo `dicto.log` también puede contener texto transcrito. Borrar el historial no borra ese registro. Consulta la [política de privacidad](https://adrianrocafulldev.es/dicto/privacidad) para conocer las ubicaciones de los archivos, los servicios externos y cómo eliminar todos los datos.

## Code signing policy

La solicitud a SignPath Foundation está en preparación. **La firma de SignPath todavía no está activa** y las publicaciones actuales pueden estar sin firmar. Consulta la [Code signing policy](https://adrianrocafulldev.es/dicto/code-signing-policy) para comprobar el estado y las responsabilidades.

Si se aprueba la solicitud y se activa la integración: Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

- Autor y committer: [Adrián Rocafull (arocafull00)](https://github.com/arocafull00).
- Revisor de contribuciones externas: Adrián Rocafull.
- Aprobador de solicitudes de firma: Adrián Rocafull. Cada solicitud requerirá aprobación manual; antes de activar la integración se deberá verificar MFA en GitHub y SignPath.
- Instaladores compilados desde el repositorio público con GitHub Actions. Los binarios de terceros no se presentarán como código propio para su firma. La compatibilidad de las bibliotecas CUDA opcionales con el programa queda pendiente de revisión por SignPath.

## Desinstalación

En Windows, usa **Ajustes → Aplicaciones → Dicto → Desinstalar**. En macOS, desactiva primero el inicio automático en Dicto y elimina `~/Applications/Dicto.app`; si usaste Homebrew, ejecuta `brew uninstall dicto`. En Linux, desactiva el inicio automático, borra la carpeta que clonaste y elimina `~/.local/share/applications/dicto.desktop`.

La desinstalación puede conservar los datos personales. Para borrarlos, cierra Dicto y elimina `%APPDATA%\Dicto\` (Windows), `~/Library/Application Support/Dicto/` (macOS) o `~/.config/Dicto/` (Linux). Los modelos descargados están aparte, normalmente en `~/.cache/huggingface/`; elimina solo los correspondientes a Dicto si otras aplicaciones usan esa caché.

## Licencia

Dicto se distribuye bajo la [licencia MIT](LICENSE). Los modelos y componentes de terceros conservan sus propias licencias.

## 🛠️ Hecho con

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [sounddevice](https://github.com/spatialaudio/python-sounddevice) · [keyboard](https://github.com/boppreh/keyboard) · [PyObjC](https://pyobjc.readthedocs.io) · [pynput](https://github.com/moses-palmer/pynput) · [pystray](https://github.com/moses-palmer/pystray) · [pyperclip](https://github.com/asweigart/pyperclip) · [Pillow](https://python-pillow.org) · Tkinter
