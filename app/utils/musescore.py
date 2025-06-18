import os
import subprocess
import music21

def setup_musescore():
    """Configurar MuseScore para music21"""
    print("🎵 Configurando MuseScore sin parches...")
    
    # Buscar MuseScore en diferentes ubicaciones
    musescore_paths = [
        # WSL paths
        "/mnt/c/Program Files/MuseScore 4/bin/MuseScore4.exe",
        "/mnt/c/Program Files/MuseScore 3/bin/MuseScore3.exe",
        "/mnt/c/Program Files/MuseScore 2/bin/MuseScore2.exe",
        # Linux paths
        "/usr/bin/musescore",
        "/usr/bin/musescore3",
        "/usr/bin/musescore4",
        # Windows paths (si se ejecuta directamente en Windows)
        "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe",
        "C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe",
    ]
    
    musescore_path = None
    
    for path in musescore_paths:
        if os.path.exists(path):
            musescore_path = path
            print(f"MuseScore encontrado (WSL): {path}")
            break
    
    if not musescore_path:
        print("⚠️ MuseScore no encontrado. Intentando detectar automáticamente...")
        try:
            # Intentar detectar automáticamente
            result = subprocess.run(['which', 'musescore'], capture_output=True, text=True)
            if result.returncode == 0:
                musescore_path = result.stdout.strip()
                print(f"MuseScore encontrado (auto): {musescore_path}")
        except:
            pass
    
    if musescore_path:
        # Configurar music21 para usar MuseScore
        try:
            us = music21.environment.UserSettings()
            us['musescoreDirectPNGPath'] = musescore_path
            us['musicxmlPath'] = musescore_path
            print(f"✅ music21 configurado con UserSettings: {musescore_path}")
        except Exception as e:
            print(f"⚠️ Error configurando music21: {e}")
        
        print(f"MuseScore configurado en: {musescore_path}")
        return musescore_path
    else:
        print("❌ MuseScore no encontrado. Algunas funcionalidades pueden no estar disponibles.")
        return None 