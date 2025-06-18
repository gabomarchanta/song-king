from flask import Blueprint, jsonify, send_from_directory
import os
import music21
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/score/<song_name>/<instrument>/render')
def render_score_interactive(song_name, instrument):
    """Generar partitura interactiva HTML que se puede reproducir"""
    try:
        print(f"🎼 Generando partitura interactiva para {song_name}/{instrument}")
        
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
        
        # Verificar que existe el archivo MIDI
        midi_path = os.path.join('static', 'stems', song_name, 'htdemucs', instrument_files[instrument])
        if not os.path.exists(midi_path):
            return jsonify({'error': 'Archivo MIDI no encontrado'}), 404

        # Cargar MIDI con music21
        print(f"📄 Cargando MIDI: {midi_path}")
        score = music21.converter.parse(midi_path)
        
        # Extraer información de notas para reproducción
        notes_data = []
        current_time = 0.0
        
        # Obtener todas las notas del score
        all_notes = score.flatten().notes
        
        for element in all_notes:
            if hasattr(element, 'pitch'):  # Nota individual
                pitch = element.pitch
                note_name = pitch.name.lower()
                octave = pitch.octave
                midi_note = pitch.midi
                
                # Calcular duración
                duration = float(getattr(element, 'quarterLength', 1.0))
                start_time = current_time
                end_time = start_time + duration
                
                notes_data.append({
                    'note': note_name,
                    'octave': octave,
                    'midi_note': midi_note,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'type': 'note'
                })
                
                current_time = end_time
                
            elif hasattr(element, 'notes'):  # Acorde
                if element.notes:
                    # Tomar la nota más aguda del acorde
                    highest_note = max(element.notes, key=lambda n: n.pitch.ps)
                    pitch = highest_note.pitch
                    note_name = pitch.name.lower()
                    octave = pitch.octave
                    midi_note = pitch.midi
                    
                    duration = float(getattr(element, 'quarterLength', 1.0))
                    start_time = current_time
                    end_time = start_time + duration
                    
                    notes_data.append({
                        'note': note_name,
                        'octave': octave,
                        'midi_note': midi_note,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'type': 'chord'
                    })
                    
                    current_time = end_time
        
        # Construir rutas de archivos
        audio_files = {
            'vocals': 'vocals.wav',
            'bass': 'bass.wav', 
            'guitar': 'other.wav',  # Guitar viene del archivo 'other'
            'piano': 'other.wav',   # Piano viene del archivo 'other'
            'synth': 'other.wav'    # Synth viene del archivo 'other'
        }
        
        audio_file_path = f'/static/stems/{song_name}/htdemucs/{audio_files[instrument]}'
        midi_file_path = f'/static/stems/{song_name}/htdemucs/{instrument_files[instrument]}'
        
        # Verificar que el archivo de audio existe
        audio_full_path = os.path.join('static', 'stems', song_name, 'htdemucs', audio_files[instrument])
        if not os.path.exists(audio_full_path):
            return jsonify({'error': f'Archivo de audio no encontrado: {audio_file_path}'}), 404
        
        # Crear respuesta con datos de reproducción
        response_data = {
            'notes': notes_data,
            'total_duration': current_time,
            'instrument': instrument,
            'song_name': song_name,
            'midi_file': midi_file_path,
            'audio_file': audio_file_path
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error generando partitura interactiva: {str(e)}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@api_bp.route('/api/score/<song_name>/<instrument>')
def get_score(song_name, instrument):
    """Obtener información de partitura para un instrumento específico con notas reales del MIDI"""
    try:
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
                        
                        notes.append({
                            'note': note_full,
                            'duration': duration,
                            'quarterLength': float(getattr(element, 'quarterLength', 1.0)),
                            'octave': octave,
                            'type': 'chord'
                        })
            
            return jsonify({
                'notes': notes,
                'instrument': instrument,
                'song_name': song_name,
                'total_notes': len(notes)
            })
            
        except Exception as e:
            print(f"Error parseando MIDI con music21: {e}")
            return jsonify({'error': f'Error parseando MIDI: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Error obteniendo partitura: {e}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@api_bp.route('/api/musicxml/<string:song_name>')
def get_musicxml_data(song_name):
    """Obtener datos MusicXML para una canción específica (archivo other_basic_pitch.mid)"""
    print(f"🎵 API: Solicitud recibida para song_name: {song_name}")
    
    midi_filename = 'other_basic_pitch.mid'
    # La ruta base donde están los archivos de esta canción
    base_path = os.path.join('static', 'stems', song_name, 'htdemucs')
    midi_full_path = os.path.join(base_path, midi_filename)
    
    print(f"📁 API: Buscando MIDI en: {midi_full_path}")
    print(f"📁 API: ¿Archivo existe? {os.path.exists(midi_full_path)}")

    if not os.path.exists(midi_full_path):
        print(f"❌ API: MIDI no encontrado. Listando archivos en {base_path}:")
        if os.path.exists(base_path):
            files = os.listdir(base_path)
            for file in files:
                if file.endswith('.mid'):
                    print(f"   📄 Archivo MIDI encontrado: {file}")
        else:
            print(f"❌ API: Directorio base no existe: {base_path}")
        return "MIDI file not found", 404

    try:
        # Forzamos la carga de la configuración para máxima robustez
        print("🔧 API: Configurando music21...")
        from music21 import environment
        us = environment.UserSettings()
        us['musicxmlPath'] = '/usr/local/bin/mscore-launcher'
        us['musescoreDirectPNGPath'] = '/usr/local/bin/mscore-launcher'
        print(f"✅ API: music21 configurado - musicxmlPath: {us['musicxmlPath']}")

        # 1. Cargar el MIDI
        print(f"🎼 API: Cargando MIDI desde {midi_full_path}")
        import music21
        score = music21.converter.parse(midi_full_path)
        print(f"✅ API: MIDI cargado exitosamente - {len(score.parts)} partes encontradas")
        
        # 2. Escribir a un archivo temporal .musicxml en el disco
        xml_temp_path = os.path.join(base_path, 'temp_score.musicxml')
        print(f"📝 API: Escribiendo MusicXML temporal en {xml_temp_path}")
        score.write('musicxml', fp=xml_temp_path)
        print(f"✅ API: MusicXML escrito. ¿Archivo existe? {os.path.exists(xml_temp_path)}")
        
        if os.path.exists(xml_temp_path):
            file_size = os.path.getsize(xml_temp_path)
            print(f"📊 API: Tamaño del archivo MusicXML: {file_size} bytes")

        # 3. Leer el contenido del archivo generado
        print(f"📖 API: Leyendo contenido desde {xml_temp_path}")
        with open(xml_temp_path, 'r', encoding='utf-8') as f:
            musicxml_data = f.read()
        
        print(f"📏 API: Contenido leído - {len(musicxml_data)} caracteres")
        print(f"🔍 API: Primeros 100 caracteres: {musicxml_data[:100]}")
        
        # 4. (Opcional pero recomendado) Limpiar el archivo temporal
        os.remove(xml_temp_path)
        print("🗑️ API: Archivo temporal eliminado.")
        
        # 5. Comprobar que los datos leídos son un XML válido
        if not musicxml_data.strip().startswith('<?xml'):
            raise ValueError(f"La conversión de music21 no generó un archivo XML válido. Inicio: {musicxml_data[:50]}")

        # 6. Enviar los datos
        print("📤 API: Enviando respuesta MusicXML")
        from flask import Response
        return Response(musicxml_data, mimetype='application/vnd.recordare.musicxml+xml')
        
    except Exception as e:
        print(f"❌ API: Error en get_musicxml_data: {e}")
        import traceback
        traceback.print_exc() # Esto nos mostrará el error exacto en la terminal de Flask
        return str(e), 500

@api_bp.route('/api/musicxml/<string:song_name>/<string:instrument>')
def get_musicxml_instrument(song_name, instrument):
    """Obtener datos MusicXML para un instrumento específico"""
    print(f"🎵 API: Solicitud recibida para {song_name}/{instrument}")
    
    # Mapeo de instrumentos a archivos MIDI
    instrument_files = {
        'vocals': 'vocals_basic_pitch.mid',
        'bass': 'bass_basic_pitch.mid',
        'guitar': 'other_cluster_0_guitar.mid',
        'piano': 'other_cluster_1_piano.mid',
        'synth': 'other_cluster_2_synth.mid',
        'other': 'other_basic_pitch.mid'
    }
    
    if instrument not in instrument_files:
        print(f"❌ API: Instrumento no válido: {instrument}")
        return f"Instrumento no válido: {instrument}", 400
    
    midi_filename = instrument_files[instrument]
    base_path = os.path.join('static', 'stems', song_name, 'htdemucs')
    midi_full_path = os.path.join(base_path, midi_filename)
    
    print(f"📁 API: Buscando MIDI en: {midi_full_path}")
    print(f"📁 API: ¿Archivo existe? {os.path.exists(midi_full_path)}")

    if not os.path.exists(midi_full_path):
        print(f"❌ API: MIDI no encontrado. Listando archivos en {base_path}:")
        if os.path.exists(base_path):
            files = os.listdir(base_path)
            for file in files:
                if file.endswith('.mid'):
                    print(f"   📄 Archivo MIDI encontrado: {file}")
        else:
            print(f"❌ API: Directorio base no existe: {base_path}")
        return "MIDI file not found", 404

    try:
        # Forzamos la carga de la configuración para máxima robustez
        print(f"🔧 API: Configurando music21 para {instrument}...")
        from music21 import environment
        us = environment.UserSettings()
        us['musicxmlPath'] = '/usr/local/bin/mscore-launcher'
        us['musescoreDirectPNGPath'] = '/usr/local/bin/mscore-launcher'
        print(f"✅ API: music21 configurado - musicxmlPath: {us['musicxmlPath']}")

        # 1. Cargar el MIDI
        print(f"🎼 API: Cargando MIDI desde {midi_full_path}")
        import music21
        score = music21.converter.parse(midi_full_path)
        print(f"✅ API: MIDI cargado exitosamente - {len(score.parts)} partes encontradas")
        
        # 2. Escribir a un archivo temporal .musicxml en el disco
        xml_temp_path = os.path.join(base_path, f'temp_score_{instrument}.musicxml')
        print(f"📝 API: Escribiendo MusicXML temporal en {xml_temp_path}")
        score.write('musicxml', fp=xml_temp_path)
        print(f"✅ API: MusicXML escrito. ¿Archivo existe? {os.path.exists(xml_temp_path)}")
        
        if os.path.exists(xml_temp_path):
            file_size = os.path.getsize(xml_temp_path)
            print(f"📊 API: Tamaño del archivo MusicXML: {file_size} bytes")

        # 3. Leer el contenido del archivo generado
        print(f"📖 API: Leyendo contenido desde {xml_temp_path}")
        with open(xml_temp_path, 'r', encoding='utf-8') as f:
            musicxml_data = f.read()
        
        print(f"📏 API: Contenido leído - {len(musicxml_data)} caracteres")
        print(f"🔍 API: Primeros 100 caracteres: {musicxml_data[:100]}")
        
        # 4. (Opcional pero recomendado) Limpiar el archivo temporal
        os.remove(xml_temp_path)
        print("🗑️ API: Archivo temporal eliminado.")
        
        # 5. Comprobar que los datos leídos son un XML válido
        if not musicxml_data.strip().startswith('<?xml'):
            raise ValueError(f"La conversión de music21 no generó un archivo XML válido. Inicio: {musicxml_data[:50]}")

        # 6. Enviar los datos
        print(f"📤 API: Enviando respuesta MusicXML para {instrument}")
        from flask import Response
        return Response(musicxml_data, mimetype='application/vnd.recordare.musicxml+xml')
        
    except Exception as e:
        print(f"❌ API: Error en get_musicxml_instrument para {instrument}: {e}")
        import traceback
        traceback.print_exc()
        return str(e), 500

@api_bp.route('/api/health')
def health_check():
    """Verificar estado de la aplicación"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0',
        'service': 'Song King'
    })

@api_bp.route('/api/stats')
def get_stats():
    """Obtener estadísticas de la aplicación"""
    try:
        stats = {
            'total_songs': 0,
            'total_midi_files': 0,
            'total_size_mb': 0
        }
        
        if os.path.exists('static/stems'):
            for song_folder in os.listdir('static/stems'):
                song_path = os.path.join('static/stems', song_folder)
                if os.path.isdir(song_path):
                    stats['total_songs'] += 1
                    
                    # Contar archivos MIDI
                    htdemucs_path = os.path.join(song_path, 'htdemucs')
                    if os.path.exists(htdemucs_path):
                        midi_files = [f for f in os.listdir(htdemucs_path) if f.endswith('.mid')]
                        stats['total_midi_files'] += len(midi_files)
                        
                        # Calcular tamaño total
                        for midi_file in midi_files:
                            file_path = os.path.join(htdemucs_path, midi_file)
                            stats['total_size_mb'] += os.path.getsize(file_path) / (1024 * 1024)
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@api_bp.route('/favicon.ico')
def favicon():
    """Servir favicon"""
    from flask import current_app
    return send_from_directory(current_app.static_folder, 'favicon.ico')

@api_bp.route('/api/debug/jobs')
def debug_jobs():
    """Debug: mostrar todos los trabajos activos"""
    from app.services.job_manager import job_status
    return jsonify({
        'active_jobs': len(job_status),
        'jobs': job_status
    }) 