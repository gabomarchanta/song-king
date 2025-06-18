from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from app.services.song_processor import process_song_with_tracking
from app.services.job_manager import update_job_status, get_job_status

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    """Página principal con formulario de upload y lista de canciones procesadas"""
    if request.method == 'POST':
        # Verificar si se envió un archivo
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Verificar si se seleccionó un archivo
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        # Verificar si el archivo es válido
        if file and allowed_file(file.filename):
            try:
                # Generar nombre único para el archivo
                filename = secure_filename(file.filename)
                base_name = os.path.splitext(filename)[0]
                unique_id = str(uuid.uuid4())[:8]
                safe_filename = f"{base_name}_{unique_id}{os.path.splitext(filename)[1]}"
                
                # Guardar archivo
                upload_path = os.path.join('uploads', safe_filename)
                file.save(upload_path)
                
                # Crear directorio para stems
                stems_folder = os.path.join('static', 'stems', base_name)
                os.makedirs(stems_folder, exist_ok=True)
                
                # Generar ID único para el trabajo
                job_id = str(uuid.uuid4())
                
                # Iniciar procesamiento en segundo plano
                process_song_with_tracking(upload_path, stems_folder, job_id)
                
                flash(f'Archivo "{filename}" subido y procesamiento iniciado. ID: {job_id}', 'success')
                return redirect(url_for('main.index'))
                
            except Exception as e:
                flash(f'Error procesando archivo: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Tipo de archivo no permitido. Use MP3, WAV, M4A o FLAC.', 'error')
            return redirect(request.url)
    
    # GET: Mostrar lista de canciones procesadas
    processed_songs = []
    
    if os.path.exists('static/stems'):
        for song_folder in os.listdir('static/stems'):
            song_path = os.path.join('static/stems', song_folder)
            if os.path.isdir(song_path):
                # Verificar si tiene archivos MIDI
                htdemucs_path = os.path.join(song_path, 'htdemucs')
                has_midi = os.path.exists(htdemucs_path) and any(
                    f.endswith('.mid') for f in os.listdir(htdemucs_path)
                )
                
                # Obtener stems disponibles
                stems = []
                if has_midi:
                    for file in os.listdir(htdemucs_path):
                        if file.endswith('.mid'):
                            stem_name = file.replace('.mid', '')
                            stems.append(stem_name)
                
                processed_songs.append({
                    'name': song_folder,
                    'has_midi': has_midi,
                    'stems': stems
                })
    
    return render_template('index.html', processed_songs=processed_songs)

@main_bp.route('/api/job-status/<job_id>')
def get_job_status_route(job_id):
    """Obtener estado de un trabajo de procesamiento"""
    return get_job_status(job_id) 