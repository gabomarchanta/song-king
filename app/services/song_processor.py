import os
import threading
from app.services.job_manager import update_job_status
from tasks import process_song

def process_song_with_tracking(upload_path, stems_folder, job_id):
    """Procesar canción con seguimiento de progreso"""
    def process_with_progress():
        try:
            update_job_status(job_id, 'processing', 'Iniciando separación de instrumentos...', 10)
            
            # Procesar la canción
            process_song(upload_path, stems_folder, progress_callback=lambda message, progress: 
                update_job_status(job_id, 'processing', message, progress))
            
            update_job_status(job_id, 'completed', 'Procesamiento completado exitosamente', 100)
            
        except Exception as e:
            error_msg = f"Error en procesamiento: {str(e)}"
            print(f"❌ {error_msg}")
            update_job_status(job_id, 'failed', error_msg, 0)
    
    # Ejecutar en hilo separado
    thread = threading.Thread(target=process_with_progress)
    thread.daemon = True
    thread.start() 