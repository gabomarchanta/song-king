#!/usr/bin/env python3
"""
Song King v2.0 - Aplicación principal refactorizada
"""

from app import create_app

if __name__ == '__main__':
    print("♪ Iniciando Song King v2.0...")
    print("✨ Aplicación mejorada con diseño moderno")
    print("🔍 Buscando MuseScore...")
    
    app = create_app()
    
    print("🚀 Servidor disponible en: http://127.0.0.1:5000")
    app.run(debug=False, host='127.0.0.1', port=5000) 