from flask import Blueprint, render_template, jsonify
import os
import music21

score_bp = Blueprint('score', __name__)

@score_bp.route('/score/<song_name>/<instrument>')
def show_interactive_score(song_name, instrument):
    """Mostrar partitura interactiva en HTML con controles de reproducción"""
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
            return "Instrumento no válido", 400
        
        # Verificar que existe el archivo MIDI
        midi_path = os.path.join('static', 'stems', song_name, 'htdemucs', instrument_files[instrument])
        if not os.path.exists(midi_path):
            return "Archivo MIDI no encontrado", 404
        
        # Renderizar plantilla con datos
        return render_template('interactive_score.html', 
                             song_name=song_name, 
                             instrument=instrument)
        
    except Exception as e:
        print(f"❌ Error mostrando partitura interactiva: {str(e)}")
        return f"Error interno: {str(e)}", 500 