# Song Processor

This is a simple Flask application that uploads a song and separates vocals and accompaniment using **Spleeter**.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open the browser at `http://localhost:5000` and upload a track.

Separated stems will be stored inside `static/stems` and can be played or downloaded from the page.
