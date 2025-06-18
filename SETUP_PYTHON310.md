# 🐍 Configuración de Python 3.10 para Song King

Esta guía te ayudará a configurar Python 3.10 específicamente para Song King, incluso si ya tienes otra versión de Python instalada.

## 🎯 ¿Por qué Python 3.10?

- **Compatibilidad garantizada** con todas las dependencias de audio/IA
- **Rendimiento optimizado** para NumPy y TensorFlow
- **Estabilidad** probada con las versiones específicas de las librerías
- **Compatibilidad con CUDA** para aceleración GPU

## 📦 Instalación de Python 3.10

### Windows

#### Opción 1: Installer oficial
1. Ve a [python.org/downloads](https://www.python.org/downloads/release/python-31013/)
2. Descarga "Windows installer (64-bit)" para Python 3.10.13
3. **IMPORTANTE**: Durante la instalación:
   - ✅ Marcar "Add Python to PATH"
   - ✅ Marcar "Install for all users"
   - ⚠️ **NO marcar** "py launcher"

#### Opción 2: pyenv-win (recomendado para múltiples versiones)
```cmd
# Instalar pyenv-win
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv

# Agregar al PATH (reiniciar terminal después)
setx PATH "%USERPROFILE%\.pyenv\pyenv-win\bin;%USERPROFILE%\.pyenv\pyenv-win\shims;%PATH%"

# Instalar Python 3.10
pyenv install 3.10.13
pyenv global 3.10.13
```

### WSL/Ubuntu

```bash
# Agregar PPA de Python
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Instalar Python 3.10
sudo apt install python3.10 python3.10-venv python3.10-pip python3.10-dev

# Hacer Python 3.10 predeterminado (opcional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

### macOS

```bash
# Con Homebrew
brew install python@3.10

# O con pyenv
brew install pyenv
pyenv install 3.10.13
pyenv global 3.10.13
```

## 🔧 Configuración del entorno

### 1. Verificar instalación
```bash
python3.10 --version
# Debería mostrar: Python 3.10.13
```

### 2. Crear entorno virtual
```bash
cd song-king

# Crear entorno con Python 3.10 específicamente
python3.10 -m venv venv310

# Activar entorno
# Windows:
venv310\Scripts\activate
# Linux/Mac:
source venv310/bin/activate
```

### 3. Verificar versión en el entorno
```bash
python --version
# Debe mostrar: Python 3.10.x
```

### 4. Instalar dependencias
```bash
# Actualizar pip primero
python -m pip install --upgrade pip

# Instalar dependencias con versiones específicas para Python 3.10
pip install -r requirements.txt
```

## 🧪 Verificación final

```bash
# Ejecutar verificador de compatibilidad
python check_python310.py
```

Deberías ver:
```
🐍 Python 3.10.x
✅ Versión de Python compatible
📦 Verificando dependencias:
✅ Flask: x.x.x
✅ NumPy: x.x.x
...
🎉 ¡Todo listo! Tu sistema es compatible con Song King en Python 3.10
```

## 🔄 Script automático

Si prefieres automatizar todo el proceso:

```bash
#!/bin/bash
# setup_python310.sh

echo "🐍 Configurando Python 3.10 para Song King..."

# Detectar sistema
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Ubuntu/WSL
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install python3.10 python3.10-venv python3.10-pip python3.10-dev -y
    PYTHON_CMD="python3.10"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install python@3.10
    PYTHON_CMD="python3.10"
else
    # Windows (requiere instalación manual)
    echo "En Windows, instala Python 3.10 desde python.org"
    PYTHON_CMD="python"
fi

# Crear entorno virtual
$PYTHON_CMD -m venv venv310
source venv310/bin/activate

# Instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

# Verificar
python check_python310.py

echo "✅ ¡Configuración completada!"
```

## 🚨 Resolución de problemas

### Error: "python3.10: command not found"
```bash
# Ubuntu/WSL
sudo apt install python3.10-distutils
sudo ln -s /usr/bin/python3.10 /usr/local/bin/python3.10

# Windows
# Verificar que Python 3.10 esté en PATH
```

### Error: "No module named 'pip'"
```bash
python3.10 -m ensurepip --upgrade
python3.10 -m pip install --upgrade pip
```

### Error: compilación de dependencias
```bash
# Ubuntu/WSL - instalar herramientas de desarrollo
sudo apt install build-essential python3.10-dev

# Windows - instalar Visual Studio Build Tools
# Descargar desde: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### Conflictos con otras versiones de Python
```bash
# Usar entorno virtual siempre
python3.10 -m venv venv310 --clear
source venv310/bin/activate
which python  # Debe apuntar al entorno virtual
```

## 📋 Checklist final

- [ ] Python 3.10.x instalado
- [ ] Entorno virtual creado con Python 3.10
- [ ] Dependencias instaladas sin errores
- [ ] Script de verificación pasa todas las pruebas
- [ ] MuseScore 4 instalado y detectado
- [ ] CUDA funcionando (si tienes GPU NVIDIA)

## 🚀 Ejecutar Song King

```bash
# Activar entorno Python 3.10
source venv310/bin/activate  # Linux/Mac
# o
venv310\Scripts\activate     # Windows

# Ejecutar aplicación
python app.py

# O con Gunicorn para producción
python start_server.py --mode prod
```

¡Listo! Ahora tienes Song King funcionando con Python 3.10 de forma óptima. 