from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
import os
from werkzeug.utils import secure_filename
import threading
import pretty_midi
import numpy as np
from tasks import process_song

app = Flask(__name__)
app.secret_key = 'Gaboindi86'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STEMS_FOLDER'] = 'static/stems'
app.config['DEMUCS_MODEL'] = 'htdemucs'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STEMS_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'audio' not in request.files or not request.files['audio'].filename:
            flash("Error: No se seleccionó ningún archivo.", "danger")
            return redirect(url_for('index'))
        
        file = request.files['audio']
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        thread = threading.Thread(target=process_song, args=(upload_path, app.config['STEMS_FOLDER']))
        thread.start()

        flash(f"¡Recibido! Tu canción '{filename}' se está procesando. Refresca en unos minutos para ver los resultados.", "info")
        return redirect(url_for('index'))

    processed_songs = []
    for song_dir in os.listdir(app.config['STEMS_FOLDER']):
        model_output_path = os.path.join(app.config['STEMS_FOLDER'], song_dir, app.config['DEMUCS_MODEL'])
        
        if os.path.isdir(model_output_path):
            song_data = {'name': song_dir, 'stems': [], 'midi_url': None}
            for file in sorted(os.listdir(model_output_path)):
                url_path = os.path.join('stems', song_dir, app.config['DEMUCS_MODEL'], file).replace('\\', '/')
                if file.endswith('.wav'):
                    song_data['stems'].append({
                        'name': os.path.splitext(file)[0].replace('_', ' ').title(),
                        'url': url_for('static', filename=url_path)
                    })
                if file.endswith('.mid'):
                    song_data['midi_url'] = url_for('static', filename=url_path)
            processed_songs.append(song_data)
            
    return render_template('index.html', processed_songs=processed_songs)

# --- ENDPOINT DE API (POSICIÓN CORRECTA) ---
# Al estar aquí, ANTES de app.run(), Flask sí registra esta ruta.
@app.route('/api/midi-data/<string:song_name>')
def get_midi_data(song_name):
    midi_filename = 'other_basic_pitch.mid'
    full_path = os.path.join(app.config['STEMS_FOLDER'], song_name, app.config['DEMUCS_MODEL'], midi_filename)

    if not os.path.exists(full_path):
        return jsonify({"error": f"MIDI file not found at {full_path}"}), 404

    try:
        pm = pretty_midi.PrettyMIDI(full_path)
        if not pm.instruments:
            return jsonify({"notes": [], "tempo": 120}), 200

        # Combinamos notas de todos los instrumentos y las ordenamos por tiempo de inicio
        all_notes = []
        for instrument in pm.instruments:
            all_notes.extend(instrument.notes)
        all_notes.sort(key=lambda x: x.start)
        
        # Filtramos y procesamos las notas para enviar al frontend
        GUITAR_LOWEST_NOTE = 40
        GUITAR_HIGHEST_NOTE = 88
        MIN_NOTE_VELOCITY = 20
        
        processed_events = []
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        last_event_end = 0.0

        for note in all_notes:
            # Filtros de calidad
            if not (GUITAR_LOWEST_NOTE <= note.pitch <= GUITAR_HIGHEST_NOTE): continue
            if note.velocity < MIN_NOTE_VELOCITY: continue
            
            # --- LÓGICA PARA SILENCIOS Y NOTAS ---
            rest_duration = note.start - last_event_end
            # Añadir un silencio si la pausa es significativa
            if rest_duration > 0.05:
                processed_events.append({"type": "rest", "start_sec": last_event_end, "duration_sec": rest_duration})

            # Añadir la nota actual
            processed_events.append({
                "type": "note",
                "pitch": note.pitch,
                "keys": [f"{note_names[note.pitch % 12]}/{note.pitch // 12 - 1}"],
                "start_sec": note.start,
                "duration_sec": note.end - note.start
            })
            last_event_end = note.end
        
        print(f"Se procesaron {len(processed_events)} eventos musicales (notas y silencios).")
        return jsonify({"events": processed_events, "tempo": pm.estimate_tempo()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Punto de partida de la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)