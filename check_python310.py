#!/usr/bin/env python3
"""
Script para verificar compatibilidad con Python 3.10
"""
import sys
import platform
import subprocess
import importlib

def check_python_version():
    """Verificar versión de Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3:
        print("❌ Necesitas Python 3.x")
        return False
    
    if version.minor < 10:
        print("❌ Necesitas Python 3.10 o superior")
        return False
    
    print("✅ Versión de Python compatible")
    return True

def check_dependencies():
    """Verificar dependencias principales"""
    dependencies = [
        ('flask', 'Flask'),
        ('numpy', 'NumPy'),
        ('music21', 'Music21'),
        ('librosa', 'Librosa'),
        ('sklearn', 'Scikit-learn'),
        ('pretty_midi', 'Pretty MIDI'),
        ('basic_pitch', 'Basic Pitch'),
    ]
    
    print("\n📦 Verificando dependencias:")
    all_ok = True
    
    for module_name, display_name in dependencies:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {display_name}: {version}")
        except ImportError as e:
            print(f"❌ {display_name}: No instalado - {e}")
            all_ok = False
        except Exception as e:
            print(f"⚠️ {display_name}: Error - {e}")
    
    return all_ok

def check_system_requirements():
    """Verificar requisitos del sistema"""
    print(f"\n🖥️ Sistema: {platform.system()} {platform.release()}")
    print(f"📟 Arquitectura: {platform.machine()}")
    
    # Verificar memoria disponible
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"💾 Memoria: {memory.total // (1024**3)} GB total, {memory.available // (1024**3)} GB disponible")
        
        if memory.available < 2 * (1024**3):  # 2GB
            print("⚠️ Memoria baja - Se recomiendan al menos 2GB disponibles")
    except ImportError:
        print("ℹ️ psutil no instalado - no se puede verificar memoria")

def check_audio_processing():
    """Verificar capacidades de procesamiento de audio"""
    print("\n🎵 Verificando capacidades de audio:")
    
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"🔥 CUDA: {'✅ Disponible' if cuda_available else '❌ No disponible'}")
        if cuda_available:
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("⚠️ PyTorch no instalado - CUDA no verificado")

def test_basic_functionality():
    """Probar funcionalidad básica"""
    print("\n🧪 Probando funcionalidad básica:")
    
    try:
        # Test Flask
        from flask import Flask
        app = Flask(__name__)
        print("✅ Flask: OK")
        
        # Test NumPy
        import numpy as np
        arr = np.array([1, 2, 3])
        print("✅ NumPy: OK")
        
        # Test music21 básico
        import music21
        note = music21.note.Note("C4")
        print("✅ Music21: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas básicas: {e}")
        return False

def main():
    print("🔍 Verificación de compatibilidad Song King con Python 3.10")
    print("=" * 60)
    
    checks = [
        ("Versión de Python", check_python_version),
        ("Dependencias", check_dependencies),
        ("Requisitos del sistema", lambda: (check_system_requirements(), True)[1]),
        ("Procesamiento de audio", lambda: (check_audio_processing(), True)[1]),
        ("Funcionalidad básica", test_basic_functionality),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            if result is False:
                all_passed = False
        except Exception as e:
            print(f"❌ Error en {check_name}: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ¡Todo listo! Tu sistema es compatible con Song King en Python 3.10")
        print("\n🚀 Para ejecutar la aplicación:")
        print("   python app.py")
        print("   # o con Gunicorn (recomendado):")
        print("   python start_server.py --mode prod")
    else:
        print("⚠️ Se encontraron algunos problemas. Revisa los errores arriba.")
        print("\n📝 Para instalar dependencias faltantes:")
        print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main() 