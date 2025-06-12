# Song Processor (Song King)

**Song Processor** es una aplicación web construida con Flask y Python que utiliza modelos de Inteligencia Artificial de última generación para analizar y transformar archivos de audio. Permite a los usuarios subir una canción para separarla en sus componentes instrumentales y generar una transcripción musical en formato de partitura.

![Captura de pantalla de la aplicación](URL_A_UNA_IMAGEN_DE_TU_APP_FUNCIONANDO)
*(Sube una captura de pantalla a tu repositorio y enlaza aquí)*

---

## Características Principales

-   **Separación de Pistas:** Utiliza **Demucs** de Meta AI para separar una canción en cuatro pistas: voz, batería, bajo y otros instrumentos (guitarras, pianos, etc.).
-   **Aceleración por GPU:** El procesamiento se realiza en la GPU a través de CUDA y WSL2 para una velocidad y eficiencia máximas.
-   **Transcripción Automática:** Emplea **Basic Pitch** de Spotify para analizar la pista instrumental y transcribir las notas musicales a un archivo MIDI.
-   **Visualización de Partituras:** Renderiza la transcripción MIDI como una partitura musical interactiva directamente en el navegador usando **VexFlow**.
-   **Arquitectura Robusta:** Construido con una arquitectura de tareas en segundo plano para manejar procesos largos sin bloquear la interfaz de usuario.

---

## Stack Tecnológico

-   **Backend:** Python 3.10, Flask
-   **IA / Machine Learning:**
    -   Demucs (PyTorch)
    -   Basic Pitch (TensorFlow Lite)
    -   PrettyMIDI
-   **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript (VexFlow, Tone.js)
-   **Entorno de Desarrollo:** WSL2 (Ubuntu) con aceleración por GPU NVIDIA (CUDA)

---

## Instalación y Puesta en Marcha (Local)

Este proyecto requiere un entorno específico con aceleración por GPU para funcionar correctamente.

### Prerrequisitos

1.  **Windows 11** con una **tarjeta gráfica NVIDIA**.
2.  **WSL2** instalado y configurado. (Guía: `wsl --install`)
3.  **Drivers de NVIDIA para WSL** instalados en Windows.
4.  **CUDA Toolkit** instalado DENTRO de la distribución de Ubuntu en WSL.

### Pasos de Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/gabomarchanta/song-king.git
    cd song-king
    ```

2.  **Crear y activar un entorno virtual de Python:**
    ```bash
    python3.10 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instalar las dependencias (incluyendo PyTorch para CUDA):**
    *Primero, desinstala cualquier versión de PyTorch que pueda existir:*
    ```bash
    pip uninstall -y torch torchvision torchaudio
    ```
    *Luego, instala la versión correcta para tu versión de CUDA (ej. CUDA 12.1):*
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```
    *Finalmente, instala el resto de las dependencias del proyecto:*
    ```bash
    pip install -e .
    ```

4.  **Ejecutar la aplicación:**
    *Necesitarás dos terminales.*
    *En la Terminal 1, inicia el servidor de Flask:*
    ```bash
    python app.py
    ```
    *En una Terminal 2 (opcional, si vuelves a usar `rq` en el futuro):*
    ```bash
    rq worker
    ```

5.  Abre tu navegador y ve a `http://127.0.0.1:5000`.

---

## Hoja de Ruta Futura

-   [ ] Implementar sincronización visual del playback con la partitura.
-   [ ] Añadir la opción de generar y mostrar tablaturas de guitarra.
-   [ ] Mejorar la lógica de cuantización rítmica para partituras más legibles.
-   [ ] Permitir al usuario elegir entre diferentes modelos de separación (2 pistas, 4 pistas, 6 pistas).

---

## Autor

-   **Gabriel Gil** - [gabomarchanta](https://github.com/gabomarchanta)
