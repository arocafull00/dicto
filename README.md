<div align="center">

<img src="assets/dicto.png" width="112" alt="Dicto">

# Dicto

**Dictado por voz para Windows, 100 % local.**
Mantén pulsada una tecla, habla y suelta: el texto aparece donde esté el cursor.

<p>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Whisper-faster--whisper-111111" alt="faster-whisper">
  <img src="https://img.shields.io/badge/GPU-CUDA%20opcional-76B900?logo=nvidia&logoColor=white" alt="CUDA">
  <img src="https://img.shields.io/badge/privacidad-sin%20nube-2f6fed" alt="Sin nube">
</p>

</div>

---

## ✨ Qué hace

Dicto vive en la bandeja del sistema y convierte tu voz en texto en **cualquier aplicación**: el navegador, Word, Slack, tu editor de código, la terminal… Usa [Whisper](https://github.com/openai/whisper) a través de [faster-whisper](https://github.com/SYSTRAN/faster-whisper), así que la transcripción se hace en tu propio ordenador: **ningún audio sale de tu equipo**.

- 🎙️ **Pulsar y hablar.** Mantén `Ctrl derecho` (o el atajo que elijas), habla y suelta. El texto se pega solo.
- 🔁 **Dos modos.** *Mantener pulsado* o *pulsar para empezar y parar*, para dictados largos.
- ⚡ **Rápido con GPU.** Usa CUDA si tienes una NVIDIA; si no, funciona en CPU sin tocar nada.
- 🌍 **Multilingüe.** Español, inglés, catalán, portugués, francés, alemán, italiano o detección automática.
- 📚 **Vocabulario propio.** Enséñale nombres, marcas o términos técnicos que suele escribir mal.
- 🟢 **Indicador flotante.** Una pequeña píldora muestra el nivel del micrófono mientras grabas y avisa cuando transcribe.
- 🔔 **Sonidos sutiles** al empezar y terminar de grabar.
- 📋 **Respeta tu portapapeles.** Pega el texto y después restaura lo que tenías copiado.
- 🚀 **Inicio con Windows** opcional, con accesos directos en el menú Inicio y el escritorio.

## 🧭 Cómo funciona

```text
  tecla pulsada ──► micrófono (16 kHz) ──► tecla suelta
                                              │
                                              ▼
                         Whisper local (GPU / CPU) + filtro de silencios
                                              │
                                              ▼
                          texto ──► portapapeles ──► Ctrl+V en la app activa
```

El icono de la bandeja cambia de color según el estado:

| Color | Estado |
| :---: | --- |
| ⚪ Gris | Cargando el modelo |
| 🔵 Azul | Listo para dictar |
| 🔴 Rojo | Escuchando |
| 🟠 Naranja | Transcribiendo |

## 📦 Instalación

**Requisitos:** Windows 10/11, [Python 3.10 o superior](https://www.python.org/downloads/) (marca *Add python.exe to PATH* al instalarlo; con Scoop no hace falta) y un micrófono. Una GPU NVIDIA es opcional pero muy recomendable.

### Instalación rápida

1. Descarga el proyecto: botón verde **Code → Download ZIP** y descomprímelo, o con Git:

   ```bash
   git clone https://github.com/arocafull00/dicto.git
   ```

2. Abre **`instalar.bat`** con doble clic. Crea el entorno de Python, instala las dependencias (con soporte CUDA solo si detecta una GPU NVIDIA) y abre Dicto.

¡Y ya está! A partir de ahí, abre Dicto desde el acceso directo del menú Inicio o del escritorio.

### Con Scoop

Si usas [Scoop](https://scoop.sh), no necesitas instalar Python a mano: Scoop lo instala como dependencia.

```bash
scoop bucket add dicto https://github.com/arocafull00/dicto
```

```bash
scoop install dicto
```

Después, ejecuta `dicto` para abrirlo. Para actualizar, `scoop update dicto`.

### La primera vez que se abre

1. **Se descarga el modelo de voz** desde Hugging Face, una sola vez. Con el modelo Turbo son unos **1,6 GB**, así que puede tardar varios minutos: mientras tanto el icono de la bandeja se ve ⚪ gris. Cuando se pone 🔵 azul, ya puedes dictar.
2. Se crean accesos directos a **Dicto** en el menú Inicio y en el escritorio.
3. Se abre la ventana de configuración para que ajustes el atajo, el idioma y el micrófono.

> [!NOTE]
> Los modelos se guardan en `%USERPROFILE%\.cache\huggingface`. Si cambias de modelo en la configuración, el nuevo se descarga la primera vez que lo uses. Después, Dicto funciona sin internet.

<details>
<summary><b>Instalación manual</b></summary>

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements.txt
```

Sin GPU NVIDIA puedes quitar antes `nvidia-cublas-cu12` y `nvidia-cudnn-cu12` de `requirements.txt`. Después, abre `dicto.bat`.

</details>

> [!TIP]
> Sin GPU, Dicto funciona en CPU automáticamente. Elige un modelo más ligero (*Small* o *Base*) para que vaya fluido.

## 🎛️ Configuración

Haz clic en el icono de la bandeja para abrir la configuración:

| Opción | Descripción |
| --- | --- |
| **Atajo** | Cualquier tecla o combinación. Pulsa *Cambiar…* y presiónala. |
| **Modo** | *Mantener pulsado* o *Pulsar para empezar y parar*. |
| **Idioma** | Idioma del dictado o detección automática. |
| **Modelo** | Turbo (recomendado), Large v3, Medium, Small o Base. |
| **Micrófono** | El predeterminado del sistema o uno concreto. |
| **Vocabulario** | Términos separados por comas que Whisper debe reconocer mejor. |
| **Opciones** | Sonidos, indicador flotante e inicio con Windows. |

Desde el menú de la bandeja también puedes **copiar la última transcripción** o salir.

Los ajustes se guardan en `%APPDATA%\Dicto\config.json` y el registro de actividad en `%APPDATA%\Dicto\dicto.log`.

## 🧠 Modelos

| Modelo | Descarga | Velocidad | Precisión | Ideal para |
| --- | :---: | :---: | :---: | --- |
| `large-v3-turbo` | ~1,6 GB | ⚡⚡⚡ | ★★★★ | Uso diario con GPU *(por defecto)* |
| `large-v3` | ~3 GB | ⚡ | ★★★★★ | Máxima precisión |
| `medium` | ~1,5 GB | ⚡⚡ | ★★★ | GPUs modestas |
| `small` | ~500 MB | ⚡⚡⚡ | ★★ | CPU |
| `base` | ~150 MB | ⚡⚡⚡⚡ | ★ | Equipos muy ligeros |

## 🔒 Privacidad

Todo ocurre en tu máquina. Dicto no tiene cuentas, ni telemetría, ni servidores: la única conexión a internet es la descarga inicial del modelo desde Hugging Face.

## 🛠️ Hecho con

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [sounddevice](https://github.com/spatialaudio/python-sounddevice) · [keyboard](https://github.com/boppreh/keyboard) · [pystray](https://github.com/moses-palmer/pystray) · [pyperclip](https://github.com/asweigart/pyperclip) · [Pillow](https://python-pillow.org) · Tkinter
