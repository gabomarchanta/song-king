"""
Configuración centralizada para Song King
"""
import os
import secrets
from pathlib import Path

class Config:
    """Configuración base"""
    
    # Configuración Flask básica
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Directorios de la aplicación
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    STEMS_FOLDER = os.environ.get('STEMS_FOLDER', 'static/stems')
    
    # Configuración de archivos
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg'}
    
    # Configuración de procesamiento
    DEMUCS_MODEL = os.environ.get('DEMUCS_MODEL', 'htdemucs')
    DEMUCS_TIMEOUT = int(os.environ.get('DEMUCS_TIMEOUT', 1800))  # 30 minutos
    
    # Configuración de seguridad
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # MuseScore
    MUSESCORE_PATH = os.environ.get('MUSESCORE_PATH')
    
    @classmethod
    def init_app(cls, app):
        """Inicializar configuración de la aplicación"""
        # Crear directorios necesarios
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.STEMS_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    USE_RELOADER = False
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    PORT = int(os.environ.get('FLASK_PORT', 5000))

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    USE_RELOADER = False
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Configuraciones adicionales de seguridad para producción
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        
        # Configurar logging para producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/song_king.log', maxBytes=10240000, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Song King startup')

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True
    
    # Usar directorios temporales para testing
    UPLOAD_FOLDER = 'test_uploads'
    STEMS_FOLDER = 'test_stems'

# Mapeo de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 