# Song Processor

This is a simple Flask application that uploads a song and separates vocals and accompaniment using **Spleeter**.

**Note:** Spleeter currently supports Python versions up to **3.10**. Using Python 3.11 or newer will fail because no compatible Spleeter wheels are available. The dependencies in this repository are tested with Python 3.8–3.10.

## Setup

1. Create and activate a Python 3.8–3.10 virtual environment:
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Alternatively, you can install from `pyproject.toml` using
   ```bash
   pip install .
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open the browser at `http://localhost:5000` and upload a track.

Separated stems will be stored inside `static/stems` and can be played or downloaded from the page.
