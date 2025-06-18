from flask import Flask
from config import Config
import os

def create_app(config_name=None):
    """Factory function para crear la aplicación Flask"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Configuración
    if config_name:
        app.config.from_object(f'config.{config_name}')
    else:
        app.config.from_object(Config)
    
    # Configurar directorio de uploads
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    
    # Configurar directorio de stems
    if not os.path.exists('static/stems'):
        os.makedirs('static/stems', exist_ok=True)
    
    # Registrar blueprints
    from app.routes.main import main_bp
    from app.routes.score import score_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(score_bp)
    app.register_blueprint(api_bp)
    
    # Configurar MuseScore
    from app.utils.musescore import setup_musescore
    setup_musescore()
    
    return app 