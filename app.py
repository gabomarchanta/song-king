from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, Response
import os
import sys
import shutil
import secrets
from werkzeug.utils import secure_filename
import threading
import subprocess
import music21
from tasks import process_song
from config import config
import time
import json

def create_app(config_name=None):
    """Factory function para crear la aplicación Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    return app

app = create_app()

# Extensiones de archivo permitidas (ahora desde config)
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']

# Crear directorios necesarios
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STEMS_FOLDER'], exist_ok=True)

# Diccionario global para rastrear el estado de los trabajos
processing_jobs = {}

# Variable global para MuseScore path
MUSESCORE_PATH = None

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def setup_musescore():
    """Configura MuseScore para music21 - optimizado para WSL/Windows con manejo robusto de errores"""
    try:
        import platform
        import subprocess
        
        # Configuración de variables de entorno para MuseScore headless
        env_vars = {
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_LOGGING_RULES': '*.debug=false;qt.qpa.*=false',
            'MUSESCORE_NO_SYNTHESIZER': '1',
            'DISPLAY': ':99'  # Display virtual para headless
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Rutas a probar en orden de preferencia (MuseScore 4 primero)
        musescore_paths = [
            # MuseScore 4 (prioritario)
            'C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe',
            # WSL launcher (si existe)
            '/usr/local/bin/mscore-launcher',
            # MuseScore 3 como fallback
            'C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe',
            'C:\\Program Files (x86)\\MuseScore 3\\bin\\MuseScore3.exe',
            # Linux nativo
            '/usr/bin/musescore',
            '/usr/bin/mscore'
        ]
        
        musescore_found = None
        
        # Probar cada ruta con verificación mejorada
        for path in musescore_paths:
            try:
                if path.startswith('C:\\'):
                    # Path de Windows - verificar existencia directa
                    if os.path.exists(path):
                        # Verificar que es ejecutable probando versión
                        try:
                            result = subprocess.run([path, '--version'], 
                                                  capture_output=True, 
                                                  timeout=10,
                                                  env=os.environ)
                            if result.returncode == 0 or result.returncode == 3221225620:
                                # 3221225620 es común en MuseScore 4 pero aún funciona
                                musescore_found = path
                                print(f"MuseScore encontrado (Windows): {path}")
                                break
                        except:
                            # Si falla la verificación de versión pero el archivo existe, usar igualmente
                            musescore_found = path
                            print(f"MuseScore encontrado (Windows, sin verificación): {path}")
                            break
                else:
                    # Path de Linux - probar ejecución
                    if os.path.exists(path):
                        result = subprocess.run([path, '--version'], 
                                              capture_output=True, 
                                              timeout=5)
                        if result.returncode == 0:
                            musescore_found = path
                            print(f"MuseScore encontrado (Linux): {path}")
                            break
            except Exception as path_error:
                print(f"⚠️ Error probando {path}: {path_error}")
                continue
        
        if musescore_found:
            # Configurar music21 con manejo robusto de errores
            music21_configured = False
            
            try:
                us = music21.environment.UserSettings()
                
                # Limpiar configuraciones problemáticas primero
                problem_keys = ['musicxmlPath', 'musescoreDirectPNGPath', 'graphicsPath']
                for key in problem_keys:
                    try:
                        if key in us:
                            del us[key]
                    except:
                        pass
                
                # Configurar MuseScore
                us['musicxmlPath'] = musescore_found
                us['musescoreDirectPNGPath'] = musescore_found
                
                print(f"✅ music21 configurado con UserSettings: {musescore_found}")
                music21_configured = True
                
            except Exception as us_error:
                print(f"⚠️ Error con music21 UserSettings: {us_error}")
                
                # Fallback: configuración manual por archivo
                try:
                    config_dir = os.path.expanduser("~/.local/share/music21")
                    os.makedirs(config_dir, exist_ok=True)
                    
                    config_content = f'''<?xml version="1.0" encoding="utf-8"?>
<settings>
    <preference name="musicxmlPath" value="{musescore_found}"/>
    <preference name="musescoreDirectPNGPath" value="{musescore_found}"/>
    <preference name="qtPath" value="offscreen"/>
</settings>'''
                    
                    config_file = os.path.join(config_dir, "settings.xml")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(config_content)
                    
                    print(f"✅ music21 configurado manualmente: {config_file}")
                    music21_configured = True
                    
                except Exception as manual_error:
                    print(f"⚠️ Error en configuración manual: {manual_error}")
            
            # Guardar path global para uso directo
            global MUSESCORE_PATH
            MUSESCORE_PATH = musescore_found
            print(f"MuseScore configurado en: {musescore_found}")
            
            return True
        
        print("⚠️ MuseScore no encontrado - Las partituras se generarán como MusicXML")
        print("💡 Instala MuseScore 4 desde: https://musescore.org/en/download")
        return False
        
    except Exception as e:
        print(f"⚠️ Error configurando MuseScore: {e}")
        print("   La aplicación funcionará pero sin generación de PNG")
        return False

def update_job_status(job_id, status, message="", progress=0):
    """Actualiza el estado de un trabajo de procesamiento"""
    processing_jobs[job_id] = {
        'status': status,
        'message': message,
        'progress': progress,
        'timestamp': time.time()
    }

def process_song_with_tracking(upload_path, stems_folder, job_id):
    """Wrapper para process_song que incluye seguimiento de estado"""
    try:
        update_job_status(job_id, 'starting', 'Iniciando procesamiento...', 0)
        
        # Llamar a la función original de procesamiento
        result = process_song(upload_path, stems_folder, 
                            progress_callback=lambda msg, progress: update_job_status(job_id, 'processing', msg, progress))
        
        update_job_status(job_id, 'completed', 'Procesamiento completado', 100)
        return result
        
    except Exception as e:
        update_job_status(job_id, 'error', f'Error: {str(e)}', 0)
        print(f"Error en procesamiento: {str(e)}")
        raise

@app.route('/api/job-status/<job_id>')
def get_job_status(job_id):
    """Endpoint para obtener el estado de un trabajo"""
    print(f"DEBUG: Buscando job_id: '{job_id}' en processing_jobs")
    print(f"DEBUG: Jobs activos: {list(processing_jobs.keys())}")
    
    if job_id in processing_jobs:
        status = processing_jobs[job_id]
        print(f"DEBUG: Job encontrado - Status: {status['status']}, Progress: {status['progress']}%")
        return jsonify(status)
    else:
        print(f"DEBUG: Job '{job_id}' no encontrado")
        return jsonify({'status': 'not_found', 'message': 'Trabajo no encontrado'}), 404

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Validar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        file = request.files['file']
        
        # Validar que el archivo tiene nombre
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        # Validar extensión del archivo
        if not allowed_file(file.filename):
            return jsonify({'error': f'Tipo de archivo no permitido. Formatos válidos: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        try:
            filename = secure_filename(file.filename)
            song_name_without_ext = os.path.splitext(filename)[0]
            
            # Limpiar resultados antiguos para la misma canción
            song_output_folder = os.path.join(app.config['STEMS_FOLDER'], song_name_without_ext, app.config['DEMUCS_MODEL'])
            if os.path.exists(song_output_folder):
                shutil.rmtree(song_output_folder)
                print(f"Limpiando carpeta de resultados antiguos para {song_name_without_ext}")

            # Guardar archivo subido
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

            # Procesar en hilo separado
            job_id = f"process-{song_name_without_ext}"
            print(f"DEBUG: Creando job con ID: '{job_id}' para archivo: '{filename}'")
            thread = threading.Thread(
                target=process_song_with_tracking, 
                args=(upload_path, app.config['STEMS_FOLDER'], job_id),
                name=job_id
            )
            thread.start()

            # Retornar respuesta JSON con el job_id correcto
            return jsonify({
                'success': True,
                'message': f'¡Recibido! Tu canción "{filename}" se está procesando.',
                'job_id': job_id
            })
            
        except Exception as e:
            return jsonify({'error': f'Error procesando el archivo: {str(e)}'}), 500

    # Mostrar canciones procesadas
    processed_songs = []
    try:
        if os.path.exists(app.config['STEMS_FOLDER']):
            for song_dir_name in sorted(os.listdir(app.config['STEMS_FOLDER'])):
                model_output_path = os.path.join(app.config['STEMS_FOLDER'], song_dir_name, app.config['DEMUCS_MODEL'])
                
                if os.path.isdir(model_output_path):
                    song_data = {'name': song_dir_name, 'stems': [], 'has_midi': False, 'midi_url': None}
                    
                    for file in sorted(os.listdir(model_output_path)):
                        url_path = os.path.join('stems', song_dir_name, app.config['DEMUCS_MODEL'], file).replace('\\', '/')
                        
                        if file.endswith('.wav'):
                            stem_name = os.path.splitext(file)[0].replace('_', ' ').title()
                            song_data['stems'].append({
                                'name': stem_name, 
                                'url': url_for('static', filename=url_path)
                            })
                        elif file.endswith('.mid'):
                            song_data['has_midi'] = True
                            # Agregar URL de cualquier archivo MIDI para el botón de descarga
                            if not song_data['midi_url']:
                                song_data['midi_url'] = url_for('static', filename=url_path)
                    
                    if song_data['stems'] or song_data['has_midi']:
                        processed_songs.append(song_data)
    except Exception as e:
        print(f"Error cargando canciones procesadas: {str(e)}")
            
    return render_template('index.html', processed_songs=processed_songs)

@app.route('/api/score/<song_name>/<instrument>/render')
def render_score_image(song_name, instrument):
    """Generar partitura completa profesional usando el sistema integrado"""
    import music21
    import tempfile
    import os
    import subprocess
    
    try:
        print(f"🎼 Generando partitura completa para {song_name}")
        
        # Usar el generador de partituras completas existente
        base_path = os.path.join('static', 'stems', song_name, 'htdemucs')
        if not os.path.isdir(base_path):
            return jsonify({'error': 'Carpeta de resultados no encontrada'}), 404

        # Crear score completo con todos los instrumentos como en get_musicxml_data
        score = music21.stream.Score()
        score.append(music21.metadata.Metadata())
        score.metadata.title = f'{song_name} - Partitura Completa'
        score.metadata.composer = 'Song King AI'
        
        # Mapa de instrumentos profesional
        instrument_map = {
            'vocals_basic_pitch': {
                'name': 'Voz', 
                'instrument': music21.instrument.Vocalist(), 
                'clef': music21.clef.TrebleClef(),
                'color': '#E74C3C'
            },
            'bass_basic_pitch': {
                'name': 'Bajo', 
                'instrument': music21.instrument.ElectricBass(), 
                'clef': music21.clef.BassClef(),
                'color': '#3498DB'
            },
            'other_cluster_0_guitar': {
                'name': 'Guitarra', 
                'instrument': music21.instrument.AcousticGuitar(), 
                'clef': music21.clef.TrebleClef(),
                'color': '#F39C12'
            },
            'other_cluster_1_piano': {
                'name': 'Piano', 
                'instrument': music21.instrument.Piano(), 
                'clef': music21.clef.TrebleClef(),
                'color': '#9B59B6'
            },
            'other_cluster_2_synth': {
                'name': 'Sintetizador', 
                'instrument': music21.instrument.ElectricPiano(), 
                'clef': music21.clef.TrebleClef(),
                'color': '#1ABC9C'
            }
        }

        midi_files_processed = 0
        try:
            midi_files = [f for f in os.listdir(base_path) if f.endswith('.mid')]
            
            for midi_file in sorted(midi_files):
                file_key = os.path.splitext(midi_file)[0]
                part_info = next((v for k, v in instrument_map.items() if k in file_key), None)
                
                if not part_info:
                    continue

                print(f"🎵 Procesando {part_info['name']} ({midi_file})")
                
                try:
                    midi_full_path = os.path.join(base_path, midi_file)
                    part_score = music21.converter.parse(midi_full_path)
                    
                    if not part_score:
                        continue
                    
                    # Crear parte profesional
                    part = music21.stream.Part()
                    part.id = part_info['name']
                    part.partName = part_info['name']
                    part.insert(0, part_info['instrument'])
                    part.insert(0, part_info['clef'])
                    
                    # Añadir tiempo y tonalidad si es la primera parte
                    if midi_files_processed == 0:
                        try:
                            # Detectar tiempo y tonalidad
                            key = part_score.analyze('key')
                            time_sig = part_score.getTimeSignatures()
                            
                            if key:
                                part.insert(0, key)
                            if time_sig:
                                part.insert(0, time_sig[0])
                        except:
                            # Valores por defecto
                            part.insert(0, music21.key.KeySignature(0))  # C major
                            part.insert(0, music21.meter.TimeSignature('4/4'))
                    
                    # Procesar notas con limitación para evitar partituras muy largas
                    try:
                        chordified_part = part_score.chordify()
                        notes_and_rests = chordified_part.flatten().notesAndRests
                    except:
                        notes_and_rests = part_score.flatten().notesAndRests
                    
                    # Limitar a los primeros 32 compases para una partitura legible
                    measure_count = 0
                    for element in notes_and_rests:
                        if hasattr(element, 'offset') and element.offset > 128:  # 32 compases de 4/4
                            break
                        if element:
                            part.append(element)
                    
                    if len(part.notesAndRests) > 0:
                        score.insert(0, part)
                        midi_files_processed += 1
                        
                except Exception as e:
                    print(f"🚫 Error procesando {midi_file}: {str(e)}")
                    continue
                    
        except OSError:
            return jsonify({'error': 'Error accediendo a archivos MIDI'}), 500
        
        if midi_files_processed == 0:
            return jsonify({'error': 'No se encontraron archivos MIDI válidos'}), 404

        print(f"✅ Partitura creada con {midi_files_processed} instrumentos")
        
        # Crear directorio temporal en Windows accesible desde WSL
        import platform
        system = platform.system().lower()
        
        if system == 'windows' or 'microsoft' in platform.release().lower():
            # Usar directorio temporal de Windows para compatibilidad
            import tempfile
            temp_dir = tempfile.gettempdir()  # C:\Users\...\AppData\Local\Temp
        else:
            # Crear directorio temporal local para otros sistemas
            temp_dir = os.path.join(os.getcwd(), 'temp_musescore')
            os.makedirs(temp_dir, exist_ok=True)
        
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        xml_path = os.path.join(temp_dir, f'score_{unique_id}.musicxml')
        png_path = os.path.join(temp_dir, f'score_{unique_id}.png')
        
        print(f"📁 Directorio temporal: {temp_dir}")
        print(f"📄 Archivo XML: {xml_path}")
        print(f"🖼️ Archivo PNG: {png_path}")
        
        try:
            # Generar la partitura final
            try:
                final_score = score.makeMeasures()
            except:
                final_score = score
            
            # Exportar a MusicXML
            final_score.write('musicxml', fp=xml_path)
            print(f"🎼 MusicXML generado: {xml_path}")
            
            # Intentar usar MuseScore para generar PNG profesional
            musescore_path = None
            try:
                us = music21.environment.UserSettings()
                # Usar diferentes métodos para acceder a la configuración
                if hasattr(us, 'get'):
                    musescore_path = us.get('musicxmlPath', None)
                elif 'musicxmlPath' in us:
                    musescore_path = us['musicxmlPath']
                else:
                    # Configuración manual si no existe
                    launcher_path = '/usr/local/bin/mscore-launcher'
                    if os.path.exists(launcher_path):
                        us['musicxmlPath'] = launcher_path
                        us['musescoreDirectPNGPath'] = launcher_path
                        musescore_path = launcher_path
                        print(f"🔧 Configuración automática aplicada: {launcher_path}")
            except Exception as settings_error:
                print(f"⚠️ Error con music21 UserSettings: {settings_error}")
                # Fallback directo al launcher
                launcher_path = '/usr/local/bin/mscore-launcher'
                if os.path.exists(launcher_path):
                    musescore_path = launcher_path
                    print(f"🔧 Usando launcher directo: {launcher_path}")
                else:
                    print("⚠️ No se encontró configuración de MuseScore")
            
            # Intentar directamente con MuseScore (como funcionaba antes)
            print("🖼️ Intentando MuseScore directo...")
            
            # Detectar sistema y usar la ruta apropiada
            import platform
            system = platform.system().lower()
            
            # Lista de rutas de MuseScore para probar
            musescore_paths = []
            
            # Primero intentar el path configurado globalmente
            global MUSESCORE_PATH
            if MUSESCORE_PATH:
                musescore_paths.append(MUSESCORE_PATH)
            
            # Luego rutas específicas del sistema
            if system == 'windows' or 'microsoft' in platform.release().lower():
                # En WSL o Windows
                musescore_paths.extend([
                    '/usr/local/bin/mscore-launcher',  # Launcher WSL (prioritario)
                    'C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe',
                    'C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe',
                    'C:\\Program Files (x86)\\MuseScore 3\\bin\\MuseScore3.exe'
                ])
            else:
                # Linux nativo
                musescore_paths.extend([
                    '/usr/bin/musescore',
                    '/usr/bin/mscore',
                    '/usr/local/bin/mscore-launcher'
                ])
            
            # Filtrar duplicados
            musescore_paths = list(dict.fromkeys(musescore_paths))
            
            png_generated = False
            
            for musescore_path in musescore_paths:
                if png_generated:
                    break
                    
                if not os.path.exists(musescore_path):
                    continue
                    
                try:
                    print(f"🎼 Probando: {musescore_path}")
                    
                    # Variables de entorno para MuseScore headless en Windows
                    env = os.environ.copy()
                    env['QT_QPA_PLATFORM'] = 'offscreen'
                    env['QT_LOGGING_RULES'] = '*.debug=false'
                    env['MUSESCORE_NO_SYNTHESIZER'] = '1'
                    env['DISPLAY'] = ':0'  # Display virtual
                    
                    # Solo forzar directorio temporal si no es Windows nativo
                    if not (system == 'windows'):
                        env['TEMP'] = temp_dir
                        env['TMP'] = temp_dir
                        env['TMPDIR'] = temp_dir
                    
                    # MuseScore4 conversión directa simplificada
                    cmd = [musescore_path, xml_path, '-o', png_path]
                    print(f"🔧 Ejecutando: {' '.join(cmd)}")
                    
                    # Ejecutar desde directorio temporal solo si no es Windows nativo
                    if system == 'windows':
                        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=45)
                    else:
                        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=45, cwd=temp_dir)
                    
                    print(f"MuseScore código: {result.returncode}")
                    if result.stdout:
                        print(f"MuseScore stdout: {result.stdout}")
                    if result.stderr:
                        print(f"MuseScore stderr: {result.stderr}")
                    
                    # Verificar si se generó la imagen
                    if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                        print(f"✅ Partitura PNG generada: {os.path.getsize(png_path)} bytes")
                        with open(png_path, 'rb') as img_file:
                            img_data = img_file.read()
                        png_generated = True
                        return Response(img_data, mimetype='image/png')
                    else:
                        print("⚠️ No se generó PNG válido")
                        
                except subprocess.TimeoutExpired:
                    print(f"⚠️ Timeout con {musescore_path}")
                    continue
                except Exception as musescore_error:
                    print(f"⚠️ Error con {musescore_path}: {musescore_error}")
                    continue
            
            if not png_generated:
                print("⚠️ No se pudo generar PNG con MuseScore")
                
                # Fallback: usar generador alternativo de PNG MEJORADO
                print("🔄 Generando PNG profesional con PIL...")
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    import music21
                    
                    # Parsear el score para obtener información real
                    score = music21.converter.parse(xml_path)
                    
                    # Configuración mejorada de imagen
                    width = 1200
                    height = 800
                    bg_color = '#FEFEFE'
                    img = Image.new('RGB', (width, height), bg_color)
                    draw = ImageDraw.Draw(img)
                    
                    # Cargar fuentes mejoradas
                    try:
                        title_font = ImageFont.truetype("arial.ttf", 28)
                        subtitle_font = ImageFont.truetype("arial.ttf", 18)
                        text_font = ImageFont.truetype("arial.ttf", 14)
                        note_font = ImageFont.truetype("arial.ttf", 12)
                    except:
                        title_font = ImageFont.load_default()
                        subtitle_font = ImageFont.load_default()
                        text_font = ImageFont.load_default()
                        note_font = ImageFont.load_default()
                    
                    # Colores profesionales
                    title_color = '#2C3E50'
                    staff_color = '#34495E'
                    note_color = '#E74C3C'
                    text_color = '#7F8C8D'
                    
                    # Header profesional
                    draw.text((width//2 - 200, 30), f"Song King - {song_name}", 
                             fill=title_color, font=title_font)
                    draw.text((width//2 - 150, 70), f"Instrumento: {instrument.title()}", 
                             fill=text_color, font=subtitle_font)
                    
                    # Línea decorativa
                    draw.line([(50, 110), (width-50, 110)], fill='#BDC3C7', width=2)
                    
                    # Dibujar múltiples pentagramas profesionales
                    staff_start_y = 150
                    staff_height = 80
                    num_staffs = 5
                    
                    for staff_num in range(num_staffs):
                        staff_y = staff_start_y + (staff_num * staff_height)
                        
                        # Dibujar pentagrama
                        for i in range(5):
                            line_y = staff_y + (i * 12)
                            draw.line([(80, line_y), (width-80, line_y)], 
                                     fill=staff_color, width=1)
                        
                        # Clave de Sol al inicio
                        draw.text((90, staff_y - 5), "𝄞", fill=staff_color, font=title_font)
                        
                        # Dibujar notas representativas del score real
                        try:
                            notes = list(score.flatten().notes)[:16]  # Máximo 16 notas por pentagrama
                            note_x = 140
                            
                            for i, note in enumerate(notes):
                                if i >= 16:  # Máximo notas por línea
                                    break
                                
                                # Posición vertical basada en el pitch si está disponible
                                if hasattr(note, 'pitch'):
                                    pitch_offset = (note.pitch.midi % 12) * 2
                                    note_y = staff_y + 24 - pitch_offset
                                else:
                                    note_y = staff_y + 24
                                
                                # Dibujar nota como círculo relleno
                                draw.ellipse([(note_x-6, note_y-4), (note_x+6, note_y+4)], 
                                           fill=note_color)
                                
                                # Plica de la nota
                                draw.line([(note_x+6, note_y), (note_x+6, note_y-30)], 
                                         fill=note_color, width=2)
                                
                                note_x += 60
                                
                        except Exception as note_error:
                            # Fallback: notas genéricas
                            for i in range(8):
                                note_x = 140 + (i * 80)
                                note_y = staff_y + 24 + ((i % 4) * 6)
                                draw.ellipse([(note_x-6, note_y-4), (note_x+6, note_y+4)], 
                                           fill=note_color)
                                draw.line([(note_x+6, note_y), (note_x+6, note_y-30)], 
                                         fill=note_color, width=2)
                    
                    # Información adicional en el footer
                    footer_y = height - 120
                    draw.line([(50, footer_y), (width-50, footer_y)], fill='#BDC3C7', width=1)
                    
                    # Información del archivo
                    try:
                        # Analizar score para información real
                        total_notes = len(list(score.flatten().notes))
                        duration = score.duration.quarterLength if hasattr(score.duration, 'quarterLength') else 'N/A'
                        
                        info_text = [
                            f"📊 Notas totales: {total_notes}",
                            f"⏱️ Duración: {duration} beats",
                            f"🎼 Generado por Song King v2.0",
                            f"📅 {song_name} - {instrument}"
                        ]
                        
                        for i, text in enumerate(info_text):
                            draw.text((80, footer_y + 20 + (i * 25)), text, 
                                     fill=text_color, font=text_font)
                            
                    except:
                        # Información básica si falla el análisis
                        draw.text((80, footer_y + 20), "🎼 Partitura generada por Song King v2.0", 
                                 fill=text_color, font=text_font)
                        draw.text((80, footer_y + 45), f"🎵 {song_name} - {instrument}", 
                                 fill=text_color, font=text_font)
                    
                    # Logo/marca de agua sutil
                    draw.text((width - 200, footer_y + 60), "Song King AI", 
                             fill='#ECF0F1', font=subtitle_font)
                    
                    # Guardar imagen con calidad optimizada
                    img.save(png_path, 'PNG', quality=95, optimize=True)
                    
                    if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                        print(f"✅ PNG profesional generado: {os.path.getsize(png_path)} bytes")
                        with open(png_path, 'rb') as img_file:
                            img_data = img_file.read()
                        return Response(img_data, mimetype='image/png')
                    
                except Exception as alt_error:
                    print(f"⚠️ Error en generador profesional: {alt_error}")
                    
                    # Fallback simple si falla el profesional
                    try:
                        from PIL import Image, ImageDraw, ImageFont
                        
                        img = Image.new('RGB', (800, 600), 'white')
                        draw = ImageDraw.Draw(img)
                        
                        try:
                            font = ImageFont.truetype("arial.ttf", 16)
                        except:
                            font = ImageFont.load_default()
                        
                        draw.text((50, 50), f"Song King - {song_name}", fill='black', font=font)
                        draw.text((50, 100), f"Instrumento: {instrument}", fill='black', font=font)
                        draw.text((50, 150), "Partitura disponible en formato MusicXML", fill='black', font=font)
                        
                        img.save(png_path, 'PNG')
                        
                        if os.path.exists(png_path):
                            with open(png_path, 'rb') as img_file:
                                img_data = img_file.read()
                            return Response(img_data, mimetype='image/png')
                            
                    except Exception as simple_error:
                        print(f"⚠️ Error en fallback simple: {simple_error}")
            
            # Último fallback: retornar el MusicXML para visualización web
            print("📄 Enviando MusicXML como fallback final")
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_data = f.read()
            return Response(xml_data, mimetype='application/vnd.recordare.musicxml+xml')
                
        finally:
            # Limpiar archivos temporales
            for temp_file in [xml_path, png_path]:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
    except Exception as e:
        print(f"🚫 Error generando partitura completa: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/score/<song_name>/<instrument>')
def get_score(song_name, instrument):
    """Obtener información de partitura para un instrumento específico con notas reales del MIDI"""
    try:
        import mido
        
        # Mapeo de instrumentos a archivos MIDI
        instrument_files = {
            'vocals': 'vocals_basic_pitch.mid',
            'bass': 'bass_basic_pitch.mid',
            'guitar': 'other_cluster_0_guitar.mid',
            'piano': 'other_cluster_1_piano.mid',
            'synth': 'other_cluster_2_synth.mid'
        }
        
        if instrument not in instrument_files:
            return jsonify({'error': 'Instrumento no válido'}), 400
            
        midi_file = os.path.join('static', 'stems', song_name, 'htdemucs', instrument_files[instrument])
        
        if not os.path.exists(midi_file):
            return jsonify({'error': 'Archivo MIDI no encontrado'}), 404
            
        # Parsear el archivo MIDI real usando music21 (más robusto para nuestros archivos)
        try:
            import music21
            
            # Usar music21 para parser mejor los archivos MIDI generados
            score = music21.converter.parse(midi_file)
            notes = []
            
            # Mapeo de números MIDI a nombres de notas
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            
            print(f"Analizando MIDI de {instrument} con music21...")
            
            # Obtener todas las notas del score
            all_notes = score.flatten().notes
            
            for i, element in enumerate(all_notes):
                if i >= 24:  # Limitar a 24 notas para mejor visualización
                    break
                    
                if hasattr(element, 'pitch'):  # Es una nota individual
                    # Convertir pitch de music21 a formato VexFlow
                    pitch = element.pitch
                    note_name = pitch.name.lower()
                    octave = pitch.octave
                    
                    # Asegurar octava válida para VexFlow
                    if octave < 2:
                        octave = 3
                    elif octave > 6:
                        octave = 5
                    
                    note_full = f"{note_name}/{octave}"
                    
                    # Determinar duración basada en quarterLength
                    duration = 'q'  # por defecto quarter note
                    if hasattr(element, 'quarterLength'):
                        ql = element.quarterLength
                        if ql >= 2.0:
                            duration = 'h'  # half note
                        elif ql >= 1.0:
                            duration = 'q'  # quarter note
                        elif ql >= 0.5:
                            duration = '8'  # eighth note
                        else:
                            duration = '16' # sixteenth note
                    
                    notes.append({
                        'note': note_full,
                        'duration': duration,
                        'quarterLength': float(getattr(element, 'quarterLength', 1.0)),
                        'octave': octave,
                        'type': 'note'
                    })
                    
                elif hasattr(element, 'notes'):  # Es un acorde
                    # Tomar solo la nota más aguda del acorde
                    if element.notes:
                        highest_note = max(element.notes, key=lambda n: n.pitch.ps)
                        pitch = highest_note.pitch
                        note_name = pitch.name.lower()
                        octave = pitch.octave
                        
                        if octave < 2:
                            octave = 3
                        elif octave > 6:
                            octave = 5
                            
                        note_full = f"{note_name}/{octave}"
                        
                        duration = 'q'
                        if hasattr(element, 'quarterLength'):
                            ql = element.quarterLength
                            if ql >= 2.0:
                                duration = 'h'
                            elif ql >= 1.0:
                                duration = 'q'
                            elif ql >= 0.5:
                                duration = '8'
                            else:
                                duration = '16'
                        
                        # Para acordes, agregar tanto la nota principal como las notas del acorde
                        chord_notes = []
                        for chord_note in element.notes[:4]:  # Máximo 4 notas por acorde
                            chord_pitch = chord_note.pitch
                            chord_note_name = chord_pitch.name.lower()
                            chord_octave = chord_pitch.octave
                            
                            if chord_octave < 2:
                                chord_octave = 3
                            elif chord_octave > 6:
                                chord_octave = 5
                                
                            chord_notes.append(f"{chord_note_name}/{chord_octave}")
                        
                        notes.append({
                            'note': note_full,  # Nota principal (más aguda)
                            'chord_notes': chord_notes,  # Todas las notas del acorde
                            'duration': duration,
                            'quarterLength': float(getattr(element, 'quarterLength', 1.0)),
                            'octave': octave,
                            'type': 'chord'
                        })
            
            print(f"Extraídas {len(notes)} notas de {instrument} usando music21: {[n['note'] for n in notes[:8]]}...")
            
            return jsonify({
                'instrument': instrument,
                'file': instrument_files[instrument],
                'song': song_name,
                'available': True,
                'notes': notes,
                'total_notes_in_file': len(score.flatten().notes),
                'total_parts': len(score.parts),
                'key_signature': str(score.analyze('key')) if hasattr(score, 'analyze') else 'Unknown',
                'time_signature': str(score.getTimeSignatures()[0]) if score.getTimeSignatures() else '4/4'
            })
            
        except Exception as midi_error:
            print(f"Error parseando MIDI {midi_file}: {midi_error}")
            return jsonify({
                'instrument': instrument,
                'file': instrument_files[instrument],
                'song': song_name,
                'available': False,
                'error': f'Error parseando MIDI: {str(midi_error)}'
            })
        
    except Exception as e:
        print(f"Error obteniendo partitura: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/musicxml/<string:song_name>')
def get_musicxml_data(song_name):
    """Genera y retorna MusicXML para visualización de partituras"""
    try:
        # Validar nombre de canción de manera más estricta
        if not song_name or '..' in song_name or '/' in song_name or '\\' in song_name:
            return "Nombre de canción inválido", 400
            
        # Sanitizar el nombre de la canción
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', song_name):
            return "Nombre de canción contiene caracteres no válidos", 400
            
        base_path = os.path.join(app.config['STEMS_FOLDER'], song_name, app.config['DEMUCS_MODEL'])
        if not os.path.isdir(base_path):
            return "Carpeta de resultados no encontrada", 404

        # Configurar MuseScore con manejo de errores
        try:
            setup_musescore()
        except Exception as e:
            print(f"API: Advertencia al configurar MuseScore: {str(e)}")

        score = music21.stream.Score()
        
        # Mapa de instrumentos mejorado
        instrument_map = {
            'vocals_basic_pitch': {
                'name': 'Vocal Melody', 
                'instrument': music21.instrument.Vocalist(), 
                'clef': music21.clef.TrebleClef()
            },
            'bass_basic_pitch': {
                'name': 'Bass Line', 
                'instrument': music21.instrument.ElectricBass(), 
                'clef': music21.clef.BassClef()
            },
            'other_cluster_0_guitar': {
                'name': 'Guitar (Cluster)', 
                'instrument': music21.instrument.AcousticGuitar(), 
                'clef': music21.clef.TrebleClef()
            },
            'other_cluster_1_piano': {
                'name': 'Piano (Cluster)', 
                'instrument': music21.instrument.Piano(), 
                'clef': music21.clef.TrebleClef()
            },
            'other_cluster_2_synth': {
                'name': 'Synth (Cluster)', 
                'instrument': music21.instrument.ElectricPiano(), 
                'clef': music21.clef.TrebleClef()
            }
        }

        # Procesar archivos MIDI de manera más robusta
        midi_files_processed = 0
        try:
            midi_files = [f for f in os.listdir(base_path) if f.endswith('.mid')]
            if not midi_files:
                return "No se encontraron archivos MIDI", 404
                
            for midi_file in sorted(midi_files):
                file_key = os.path.splitext(midi_file)[0]
                part_info = next((v for k, v in instrument_map.items() if k in file_key), None)
                
                if not part_info:
                    print(f"API: Saltando archivo MIDI no mapeado: {midi_file}")
                    continue

                print(f"API: Procesando {midi_file} para la parte '{part_info['name']}'...")
                
                try:
                    midi_full_path = os.path.join(base_path, midi_file)
                    if not os.path.exists(midi_full_path):
                        print(f"API: Archivo MIDI no encontrado: {midi_full_path}")
                        continue
                        
                    part_score = music21.converter.parse(midi_full_path)
                    
                    if not part_score:
                        print(f"API: No se pudo parsear el archivo MIDI: {midi_file}")
                        continue
                    
                    part = music21.stream.Part()
                    part.id = part_info['name']
                    part.insert(0, part_info['instrument'])
                    part.insert(0, part_info['clef'])
                    
                    # Procesar con chordify de manera robusta
                    try:
                        chordified_part = part_score.chordify()
                        notes_and_rests = chordified_part.flatten().notesAndRests
                    except Exception as chord_error:
                        print(f"API: Error en chordify para {midi_file}: {str(chord_error)}")
                        # Fallback: usar directamente las notas del score original
                        notes_and_rests = part_score.flatten().notesAndRests
                    
                    for element in notes_and_rests:
                        if element:  # Verificar que el elemento no sea None
                            part.append(element)
                    
                    if len(part.notesAndRests) > 0:
                        score.insert(0, part)
                        midi_files_processed += 1
                        
                except Exception as e:
                    print(f"API: Error procesando {midi_file}: {str(e)}")
                    continue
                    
        except OSError as e:
            return f"Error accediendo a los archivos: {str(e)}", 500
        
        if midi_files_processed == 0:
            return "No se pudieron procesar archivos MIDI válidos", 404
            
        # Generar MusicXML de manera más robusta
        try:
            final_score = score.makeMeasures()
        except Exception as e:
            print(f"API: Error creando medidas: {str(e)}")
            final_score = score  # Usar score original si falla makeMeasures
        
        # Crear archivo temporal y leerlo con mejor manejo de errores
        temp_file = None
        try:
            temp_file = final_score.write('musicxml')
            if not temp_file or not os.path.exists(temp_file):
                return "Error generando archivo MusicXML temporal", 500
                
            with open(temp_file, 'r', encoding='utf-8') as f:
                musicxml_data = f.read()
            
            if not musicxml_data.strip():
                return "Archivo MusicXML generado está vacío", 500
            
            return Response(musicxml_data, mimetype='application/vnd.recordare.musicxml+xml')
            
        except UnicodeDecodeError:
            # Intentar con diferentes codificaciones
            try:
                with open(temp_file, 'r', encoding='latin-1') as f:
                    musicxml_data = f.read()
                return Response(musicxml_data, mimetype='application/vnd.recordare.musicxml+xml')
            except Exception as e:
                return f"Error de codificación al leer MusicXML: {str(e)}", 500
                
        except Exception as e:
            return f"Error escribiendo MusicXML: {str(e)}", 500
            
        finally:
            # Limpiar archivo temporal de manera segura
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError as e:
                    print(f"API: No se pudo eliminar archivo temporal: {temp_file} - {str(e)}")

    except Exception as e:
        print(f"API: Error inesperado generando MusicXML para {song_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error interno del servidor: {str(e)}", 500

@app.route('/api/health')
def health_check():
    """Endpoint de salud para verificar el estado de la aplicación"""
    try:
        # Verificar directorios
        upload_ok = os.path.exists(app.config['UPLOAD_FOLDER'])
        stems_ok = os.path.exists(app.config['STEMS_FOLDER'])
        
        # Verificar MuseScore
        us = music21.environment.UserSettings()
        musescore_ok = 'musicxmlPath' in us and os.path.exists(us['musicxmlPath'])
        
        return jsonify({
            'status': 'healthy',
            'version': '2.0.0',
            'components': {
                'upload_folder': upload_ok,
                'stems_folder': stems_ok,
                'musescore': musescore_ok,
                'active_jobs': len(processing_jobs)
            },
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/api/stats')
def get_stats():
    """Endpoint para obtener estadísticas de la aplicación"""
    try:
        total_songs = 0
        total_midi_files = 0
        
        if os.path.exists(app.config['STEMS_FOLDER']):
            for song_dir in os.listdir(app.config['STEMS_FOLDER']):
                song_path = os.path.join(app.config['STEMS_FOLDER'], song_dir, app.config['DEMUCS_MODEL'])
                if os.path.isdir(song_path):
                    total_songs += 1
                    midi_files = [f for f in os.listdir(song_path) if f.endswith('.mid')]
                    total_midi_files += len(midi_files)
        
        return jsonify({
            'total_songs_processed': total_songs,
            'total_midi_files': total_midi_files,
            'active_jobs': len(processing_jobs),
            'supported_formats': list(ALLOWED_EXTENSIONS),
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    """Manejador para archivos demasiado grandes"""
    return jsonify({'error': 'El archivo es demasiado grande. Tamaño máximo permitido: 100MB'}), 413

@app.errorhandler(404)
def not_found(e):
    """Manejador para recursos no encontrados"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Recurso no encontrado'}), 404
    return render_template('index.html', processed_songs=[]), 404

@app.errorhandler(500)
def internal_error(e):
    """Manejador para errores internos del servidor"""
    return jsonify({'error': 'Error interno del servidor'}), 500

if __name__ == '__main__':
    print("🎵 Iniciando Song King v2.0...")
    print("✨ Aplicación mejorada con diseño moderno")
    
    # Configurar MuseScore antes de iniciar
    setup_musescore()
    
    print("🚀 Servidor disponible en: http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)