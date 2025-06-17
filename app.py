from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, Response
import os
from werkzeug.utils import secure_filename
import threading
import music21
from tasks import process_song

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
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
        
        # Limpiar resultados antiguos para la misma canción
        song_name_without_ext = os.path.splitext(filename)[0]
        # ¡LA RUTA CORRECTA A BORRAR!
        song_output_folder = os.path.join(app.config['STEMS_FOLDER'], app.config['DEMUCS_MODEL'], song_name_without_ext)
        if os.path.exists(song_output_folder):
            import shutil
            shutil.rmtree(song_output_folder)
            print(f"Limpiando carpeta de resultados antiguos para {song_name_without_ext}")

        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        thread = threading.Thread(target=process_song, args=(upload_path, app.config['STEMS_FOLDER']))
        thread.start()

        flash(f"¡Recibido! Tu canción '{filename}' se está procesando. Refresca la página en unos minutos.", "info")
        return redirect(url_for('index'))

    # --- LÓGICA DE VISUALIZACIÓN CORREGIDA ---
    processed_songs = []
    if os.path.exists(app.config['STEMS_FOLDER']):
        # Recorremos las carpetas de cada canción en la raíz de 'stems'
        for song_dir_name in sorted(os.listdir(app.config['STEMS_FOLDER'])):
            # La carpeta de resultados ahora está en 'stems/cancion/modelo'
            model_output_path = os.path.join(app.config['STEMS_FOLDER'], song_dir_name, app.config['DEMUCS_MODEL'])
            
            if os.path.isdir(model_output_path):
                song_data = {'name': song_dir_name, 'stems': [], 'has_midi': False}
                for file in sorted(os.listdir(model_output_path)):
                    # Construimos la URL correcta
                    url_path = os.path.join('stems', song_dir_name, app.config['DEMUCS_MODEL'], file).replace('\\', '/')
                    if file.endswith('.wav'):
                        song_data['stems'].append({'name': os.path.splitext(file)[0].title(), 'url': url_for('static', filename=url_path)})
                    if file.endswith('.mid'):
                        song_data['has_midi'] = True
                processed_songs.append(song_data)
            
    return render_template('index.html', processed_songs=processed_songs)


@app.route('/api/musicxml/<string:song_name>')
def get_musicxml_data(song_name):
    # La ruta base a los resultados de la canción
    base_path = os.path.join(app.config['STEMS_FOLDER'], song_name, app.config['DEMUCS_MODEL'])
    if not os.path.isdir(base_path):
        return "Carpeta de resultados no encontrada", 404

    try:
        # Configurar el entorno de music21 para usar MuseScore
        us = music21.environment.UserSettings()
        us['musicxmlPath'] = '/usr/local/bin/mscore-launcher'
        us['musescoreDirectPNGPath'] = '/usr/local/bin/mscore-launcher'

        score = music21.stream.Score()
        
        # Mapa para asignar un instrumento y clave a cada tipo de MIDI
        instrument_map = {
            'vocals_basic_pitch': {'name': 'Vocal Melody', 'instrument': music21.instrument.Vocalist(), 'clef': music21.clef.TrebleClef()},
            'bass_basic_pitch': {'name': 'Bass Line', 'instrument': music21.instrument.ElectricBass(), 'clef': music21.clef.BassClef()},
            'other_cluster_0_guitar': {'name': 'Guitar 1 (Cluster)', 'instrument': music21.instrument.AcousticGuitar(), 'clef': music21.clef.TrebleClef()},
            'other_cluster_1_piano': {'name': 'Piano (Cluster)', 'instrument': music21.instrument.Piano(), 'clef': music21.clef.TrebleClef()},
            'other_cluster_2_synth': {'name': 'Synth (Cluster)', 'instrument': music21.instrument.SynthLead(), 'clef': music21.clef.TrebleClef()}
        }

        # Iterar sobre todos los archivos .mid en la carpeta de resultados
        for midi_file in sorted(os.listdir(base_path)):
            if not midi_file.endswith('.mid'): 
                continue

            file_key = os.path.splitext(midi_file)[0]
            # Encontrar la configuración correcta para esta parte
            part_info = next((v for k, v in instrument_map.items() if k in file_key), None)
            
            if not part_info:
                print(f"API: Saltando archivo MIDI no mapeado: {midi_file}")
                continue

            print(f"API: Procesando {midi_file} para la parte '{part_info['name']}'...")
            
            midi_full_path = os.path.join(base_path, midi_file)
            part_score = music21.converter.parse(midi_full_path)
            
            part = music21.stream.Part()
            part.id = part_info['name']
            part.insert(0, part_info['instrument'])
            part.insert(0, part_info['clef'])
            
            # Usar chordify para agrupar notas en acordes de forma robusta
            chordified_part = part_score.chordify()
            
            # Insertar los elementos del stream chordificado en nuestra nueva parte
            for element in chordified_part.flatten().notesAndRests:
                 part.append(element)
            
            score.insert(0, part)
        
        # Organizar toda la partitura en compases al final
        final_score = score.makeMeasures()

        # Escribir el MusicXML final y enviarlo
        fp = final_score.write('musicxml')
        with open(fp, 'r', encoding='utf-8') as f:
            musicxml_data = f.read()
        os.remove(fp)

        return Response(musicxml_data, mimetype='application/vnd.recordare.musicxml+xml')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return str(e), 500

# El punto de partida de la aplicación
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)