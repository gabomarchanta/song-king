from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from app.services.song_processor import process_song_with_tracking
from app.services.job_manager import update_job_status, get_job_status
from datetime import datetime

main_bp = Blueprint('main', __name__)

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac'}

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
def index():
    """Página principal con formulario de upload y lista de canciones procesadas"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    stems_folder = current_app.config['STEMS_FOLDER']
    
    processed_songs = []
    if os.path.exists(stems_folder):
        for song_dir in os.listdir(stems_folder):
            song_path = os.path.join(stems_folder, song_dir)
            if os.path.isdir(song_path):
                # Verificar si hay stems procesados
                htdemucs_path = os.path.join(song_path, 'htdemucs')
                has_stems = os.path.exists(htdemucs_path) and len(os.listdir(htdemucs_path)) > 0
                
                # Verificar si hay archivos MIDI
                has_midi = False
                if has_stems:
                    for file in os.listdir(htdemucs_path):
                        if file.endswith('.mid'):
                            has_midi = True
                            break
                
                if has_stems:
                    stems = []
                    if os.path.exists(htdemucs_path):
                        stems = [f for f in os.listdir(htdemucs_path) if f.endswith('.wav')]
                    
                    processed_songs.append({
                        'name': song_dir,
                        'stems': stems,
                        'has_midi': has_midi
                    })
    
    return render_template('index.html', processed_songs=processed_songs)

@main_bp.route('/', methods=['POST'])
def upload_file():
    """Maneja la subida de archivos"""
    print("🟡 POST recibido en /")
    print(f"🟡 Content-Type: {request.content_type}")
    print(f"🟡 Headers: {dict(request.headers)}")
    print(f"🟡 Method: {request.method}")
    print(f"🟡 Form data keys: {list(request.form.keys())}")
    print(f"🟡 Files en request: {list(request.files.keys())}")
    print(f"🟡 Request.files dict: {dict(request.files)}")
    
    # Debug más profundo de la request
    if hasattr(request, 'data'):
        print(f"🟡 Request.data length: {len(request.data) if request.data else 0}")
    
    # Verificar si hay archivos en la request
    if 'file' not in request.files:
        print("❌ No hay campo 'file' en request.files")
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    print(f"🟡 Archivo obtenido: {file}")
    print(f"🟡 Filename: {file.filename}")
    print(f"🟡 Content type: {file.content_type}")
    
    # Verificar que se seleccionó un archivo
    if file.filename == '':
        print("❌ Filename vacío")
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    # Verificar extensión
    if not allowed_file(file.filename):
        print(f"❌ Extensión no permitida: {file.filename}")
        flash(f'Formato no soportado. Use: {", ".join(ALLOWED_EXTENSIONS)}', 'error')
        return redirect(request.url)
    
    print(f"✅ Archivo válido: {file.filename}")
    
    try:
        # Usar nombre original del archivo (sin timestamp para evitar duplicados)
        original_name = secure_filename(file.filename)
        name_without_ext = os.path.splitext(original_name)[0]
        ext = os.path.splitext(original_name)[1]
        
        # Crear directorio de uploads si no existe
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # Usar el nombre original directamente
        filepath = os.path.join(upload_folder, original_name)
        print(f"🟡 Guardando en: {filepath}")
        
        # Si el archivo ya existe, verificar si es el mismo (por tamaño)
        if os.path.exists(filepath):
            existing_size = os.path.getsize(filepath)
            new_size = len(file.read())
            file.seek(0)  # Reset file pointer
            
            if existing_size == new_size:
                print(f"🔄 Archivo idéntico ya existe, reutilizando: {filepath}")
            else:
                # Si es diferente, crear nombre con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{name_without_ext}_{timestamp}{ext}"
                filepath = os.path.join(upload_folder, unique_filename)
                print(f"🟡 Archivo diferente, usando nombre único: {filepath}")
        
        file.save(filepath)
        print(f"✅ Archivo guardado exitosamente")
        
        # Verificar que el archivo se guardó correctamente
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✅ Verificación: archivo existe, tamaño: {file_size} bytes")
        else:
            print("❌ Error: el archivo no se guardó correctamente")
            flash('Error al guardar el archivo', 'error')
            return redirect(request.url)
        
        # Crear directorio para stems usando el nombre base sin extensión
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        stems_output_folder = os.path.join(current_app.config['STEMS_FOLDER'], base_name)
        
        # Si ya existe el directorio de stems, verificar si ya está procesado
        if os.path.exists(stems_output_folder):
            htdemucs_path = os.path.join(stems_output_folder, 'htdemucs')
            if os.path.exists(htdemucs_path) and len(os.listdir(htdemucs_path)) > 0:
                print(f"🔄 Canción ya procesada, mostrando resultados existentes")
                flash(f'La canción "{original_name}" ya fue procesada anteriormente', 'info')
                return redirect(url_for('main.index'))
        
        os.makedirs(stems_output_folder, exist_ok=True)
        
        # Generar ID único para el trabajo  
        job_id = str(uuid.uuid4())
        
        print(f"✅ Job creado: {job_id}")
        print(f"📁 Stems folder: {stems_output_folder}")
        
        # Iniciar procesamiento en background
        process_song_with_tracking(filepath, stems_output_folder, job_id)
        
        # Flash message con job_id para monitoreo
        flash(f'Archivo "{original_name}" procesamiento iniciado|{job_id}', 'info')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        print(f"❌ Error durante procesamiento: {str(e)}")
        flash(f'Error durante el procesamiento: {str(e)}', 'error')
        return redirect(request.url)

@main_bp.route('/api/job-status/<job_id>')
def get_job_status_route(job_id):
    """Obtener estado de un trabajo de procesamiento"""
    return get_job_status(job_id) 