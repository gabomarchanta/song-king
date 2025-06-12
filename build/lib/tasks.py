import os
import sys
# ¡NUEVAS IMPORTACIONES!
from demucs import separate
from demucs.apply import BagOfModels
from demucs.pretrained import get_model
from demucs.audio import AudioFile

from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

def process_song(upload_path, stems_folder):
    """
    Función que hace todo el trabajo pesado usando las LIBRERÍAS
    de Demucs y Basic Pitch directamente en Python.
    """
    try:
        filename = os.path.basename(upload_path)
        song_name_without_ext = os.path.splitext(filename)[0]
        
        # --- SEPARACIÓN CON DEMUCS (COMO LIBRERÍA) ---
        print(f"WORKER: [INICIO DEMUCS] Cargando modelo y procesando {filename}...")

        # 1. Cargar el modelo pre-entrenado y moverlo a la GPU
        model = get_model(name='htdemucs_ft')
        model.to('cuda') # <-- Le decimos explícitamente que use la GPU

        # 2. Cargar el archivo de audio
        wav = AudioFile(upload_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        wav = wav.to('cuda')

        # 3. Separar las pistas
        # Esto devuelve un diccionario de tensores de audio en la GPU
        origin, res = separate.predict_mag_tas(model, wav[None], split=True, overlap=0.02)
        
        # 4. Guardar los archivos de salida
        output_dir = os.path.join(stems_folder, song_name_without_ext, 'htdemucs_ft')
        os.makedirs(output_dir, exist_ok=True)
        
        for name, source in res.items():
            stem_path = os.path.join(output_dir, f'{name}.wav')
            separate.save_audio(source, stem_path, model.samplerate)

        print("WORKER: [OK DEMUCS] Separación de pistas completada.")

        # --- TRANSCRIPCIÓN CON BASIC-PITCH ---
        path_to_accompaniment = os.path.join(output_dir, 'no_vocals.wav')
        
        if os.path.exists(path_to_accompaniment):
            print(f"WORKER: [INICIO BASIC-PITCH] Transcribiendo {path_to_accompaniment}...")
            predict_and_save(
                audio_path_list=[path_to_accompaniment],
                output_directory=output_dir,
                save_midi=True, sonify_midi=False, save_model_outputs=False, save_notes=False,
                model_path=ICASSP_2022_MODEL_PATH
            )
            print("WORKER: [OK BASIC-PITCH] Transcripción a MIDI completada.")
        
        return "Proceso completado exitosamente."
    except Exception as e:
        print(f"WORKER: [ERROR GENERAL] Ocurrió un error: {e}")
        # Importante para depurar
        import traceback
        traceback.print_exc()
        return f"Error en el procesamiento: {e}"