"""
Configuración de Gunicorn para Song King
"""
import multiprocessing
import os

# Configuración del servidor
bind = "127.0.0.1:5000"
workers = min(4, multiprocessing.cpu_count())
worker_class = "gevent"
worker_connections = 1000

# Configuración de timeout (importante para procesamiento de audio)
timeout = 1800  # 30 minutos para procesos largos
keepalive = 5

# Configuración de memoria
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Configuración de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Configuración de proceso
daemon = False
pidfile = None
tmp_upload_dir = None

# Configuraciones específicas para Song King
def when_ready(server):
    """Ejecutar cuando el servidor esté listo"""
    print("🎵 Song King con Gunicorn está listo!")
    print(f"🚀 Servidor disponible en: http://{bind}")
    print(f"👥 Workers: {workers}")
    print(f"⚡ Worker class: {worker_class}")

def worker_int(worker):
    """Manejo de interrupción de workers"""
    print(f"🔄 Worker {worker.pid} interrumpido")

def post_fork(server, worker):
    """Configuración post-fork para cada worker"""
    print(f"👤 Worker {worker.pid} iniciado") 