from flask import Flask, render_template, request, url_for
import os
from werkzeug.utils import secure_filename
from spleeter.separator import Separator

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STEMS_FOLDER'] = 'static/stems'

# Inicializamos el separador (esto puede tardar la primera vez)
print("Cargando modelo de Spleeter...")
separator = Separator('spleeter:2stems')
print("Modelo cargado.")

# Creamos las carpetas necesarias si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STEMS_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'audio' not in request.files:
            return render_template('index.html', error="No se seleccionó ningún archivo.")
        
        file = request.files['audio']
        if file.filename == '':
            return render_template('index.html', error="No se seleccionó ningún archivo.")
        
        # 1. Guardar el archivo subido de forma segura
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # 2. Preparar la ruta de salida para Spleeter
        song_name_without_ext = os.path.splitext(filename)[0]
        # Esta es la carpeta base que le pasamos a Spleeter
        output_destination_folder = os.path.join(app.config['STEMS_FOLDER'], song_name_without_ext)
        
        print(f"Procesando {filename}...")
        separator.separate_to_file(upload_path, output_destination_folder)
        print("Procesamiento completado.")

        # 3. CONSTRUIR LA RUTA CORRECTA A LOS ARCHIVOS DE SALIDA
        # Spleeter crea una subcarpeta con el mismo nombre, aquí es donde están los .wav
        actual_stems_path = os.path.join(output_destination_folder, song_name_without_ext)

        stems_urls = []
        # Verificamos si la carpeta de resultados existe
        if os.path.isdir(actual_stems_path):
            # Recorremos los archivos .wav dentro de la carpeta anidada
            for stem_filename in sorted(os.listdir(actual_stems_path)):
                if stem_filename.endswith('.wav'):
                    # Creamos la ruta relativa a la carpeta 'static' para usarla con url_for
                    # Ej: "stems/NOMBRE_CANCION/NOMBRE_CANCION/vocals.wav"
                    url_path = os.path.join('stems', song_name_without_ext, song_name_without_ext, stem_filename).replace('\\', '/')
                    stems_urls.append({
                        'name': os.path.splitext(stem_filename)[0].capitalize(),
                        'url': url_for('static', filename=url_path)
                    })
        
        return render_template('index.html', stems=stems_urls)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)