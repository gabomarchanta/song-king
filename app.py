from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from spleeter.separator import Separator

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STEMS_FOLDER'] = 'static/stems'

separator = Separator('spleeter:2stems')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STEMS_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'audio' not in request.files:
            return redirect(request.url)
        file = request.files['audio']
        if file.filename == '':
            return redirect(request.url)
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        stems_dir = os.path.join(app.config['STEMS_FOLDER'], os.path.splitext(filename)[0])
        os.makedirs(stems_dir, exist_ok=True)
        separator.separate_to_file(upload_path, stems_dir)

        stems = []
        for stem_file in os.listdir(stems_dir):
            stems.append(url_for('static', filename=f"stems/{os.path.splitext(filename)[0]}/{stem_file}"))
        return render_template('index.html', stems=stems)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
