from flask import jsonify
import threading
import time

# Almacenamiento en memoria para estados de trabajos
job_status = {}
job_lock = threading.Lock()

def update_job_status(job_id, status, message="", progress=0):
    """Actualizar estado de un trabajo"""
    with job_lock:
        job_status[job_id] = {
            'status': status,
            'message': message,
            'progress': progress,
            'timestamp': time.time()
        }
        print(f"📊 Job {job_id}: {status} - {message} ({progress}%)")

def get_job_status(job_id):
    """Obtener estado de un trabajo"""
    with job_lock:
        if job_id in job_status:
            return jsonify(job_status[job_id])
        else:
            return jsonify({'error': 'Trabajo no encontrado'}), 404 