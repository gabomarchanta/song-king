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
        
        # Crear respuesta con datos de reproducción
        response_data = {
            'notes': notes_data,
            'total_duration': current_time,
            'instrument': instrument,
            'song_name': song_name,
            'midi_file': f'/static/stems/{song_name}/htdemucs/{instrument_files[instrument]}'
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
    """Obtener datos MusicXML para una canción específica"""
    try:
        # Buscar archivos MusicXML en el directorio de la canción
        song_dir = os.path.join('static', 'stems', song_name)
        if not os.path.exists(song_dir):
            return jsonify({'error': 'Canción no encontrada'}), 404
        
        musicxml_files = []
        for root, dirs, files in os.walk(song_dir):
            for file in files:
                if file.endswith('.musicxml') or file.endswith('.xml'):
                    musicxml_files.append({
                        'filename': file,
                        'path': os.path.join(root, file),
                        'relative_path': os.path.relpath(os.path.join(root, file), song_dir)
                    })
        
        return jsonify({
            'song_name': song_name,
            'musicxml_files': musicxml_files,
            'total_files': len(musicxml_files)
        })
        
    except Exception as e:
        print(f"Error obteniendo datos MusicXML: {e}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

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
    return send_from_directory('static', 'favicon.ico') 