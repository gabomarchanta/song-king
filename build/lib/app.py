from flask import Flask, render_template, request, url_for, redirect
import os
from werkzeug.utils import secure_filename
import threading # <-- ¡NUEVA IMPORTACIÓN CLAVE!
from tasks import process_song # <-- Seguimos usando nuestra función de tarea

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STEMS_FOLDER'] = 'static/stems'
app.config['DEMUCS_MODEL'] = 'htdemucs_ft'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STEMS_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    if request.method == 'POST':
        if 'audio' not in request.files or not request.files['audio'].filename:
            return render_template('index.html', error="No se seleccionó ningún archivo.")
        
        file = request.files['audio']
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # --- ¡AQUÍ ESTÁ LA NUEVA MAGIA! ---
        # Creamos un hilo separado que ejecutará la función process_song.
        # Esto no bloquea al servidor web.
        print(f"APP: Iniciando tarea en un hilo separado para {filename}...")
        thread = threading.Thread(target=process_song, args=(upload_path, app.config['STEMS_FOLDER']))
        thread.start() # <-- El hilo empieza a trabajar en segundo plano

        message = f"¡Recibido! Tu canción '{filename}' se está procesando. Refresca la página en unos minutos para ver los resultados."

    # La lógica para mostrar resultados se queda exactamente igual.
    processed_songs = []
    for song_dir in os.listdir(app.config['STEMS_FOLDER']):
        model_output_path = os.path.join(app.config['STEMS_FOLDER'], song_dir, app.config['DEMUCS_MODEL'], song_dir)
        
        if os.path.isdir(model_output_path):
            song_data = {'name': song_dir, 'stems': [], 'midi_url': None}
            for file in sorted(os.listdir(model_output_path)):
                url_path = os.path.join('stems', song_dir, app.config['DEMUCS_MODEL'], song_dir, file).replace('\\', '/')
                if file.endswith('.wav'):
                    song_data['stems'].append({
                        'name': os.path.splitext(file)[0].replace('_', ' ').capitalize(),
                        'url': url_for('static', filename=url_path)
                    })
                if file.endswith('.mid'):
                    song_data['midi_url'] = url_for('static', filename=url_path)
            processed_songs.append(song_data)
            
    return render_template('index.html', message=message, processed_songs=processed_songs)

if __name__ == '__main__':
    # El use_reloader=False es importante cuando se usan hilos
    app.run(debug=True, use_reloader=False)