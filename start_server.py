#!/usr/bin/env python
"""
Script de arranque para Song King
Permite ejecutar con Flask dev server o Gunicorn
"""
import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Ejecutar Song King')
    parser.add_argument('--mode', choices=['dev', 'prod'], default='dev',
                       help='Modo de ejecución: dev (Flask) o prod (Gunicorn)')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host para ejecutar el servidor')
    parser.add_argument('--port', type=int, default=5000,
                       help='Puerto para ejecutar el servidor')
    parser.add_argument('--workers', type=int, default=4,
                       help='Número de workers para Gunicorn')
    
    args = parser.parse_args()
    
    if args.mode == 'dev':
        print("🔧 Ejecutando en modo desarrollo con Flask dev server...")
        print("⚠️  Solo para desarrollo - No usar en producción")
        print(f"🚀 Servidor disponible en: http://{args.host}:{args.port}")
        
        # Importar y ejecutar Flask app
        from app import app
        app.run(host=args.host, port=args.port, debug=True)
        
    elif args.mode == 'prod':
        print("🏭 Ejecutando en modo producción con Gunicorn...")
        print(f"👥 Workers: {args.workers}")
        print(f"🚀 Servidor disponible en: http://{args.host}:{args.port}")
        
        # Ejecutar con Gunicorn
        cmd = [
            'gunicorn',
            '--config', 'gunicorn_config.py',
            '--bind', f'{args.host}:{args.port}',
            '--workers', str(args.workers),
            'app:app'
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error ejecutando Gunicorn: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n🛑 Servidor detenido por el usuario")
            sys.exit(0)

if __name__ == '__main__':
    main() 