import os
import sys
from demucs import separate
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile

# Re-añadimos la importación y la función
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
        
        print(f"WORKER: [INICIO DEMUCS] Cargando modelo y procesando {filename}...")

        model = get_model(name='htdemucs')
        model.to('cuda')

        wav = AudioFile(upload_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)

        print("WORKER: Aplicando el modelo al audio...")
        sources = apply_model(model, wav[None], split=True, overlap=0.02)[0]
        print("WORKER: Modelo aplicado.")

        output_dir = os.path.join(stems_folder, song_name_without_ext, 'htdemucs')
        os.makedirs(output_dir, exist_ok=True)
        
        stems = ['drums', 'bass', 'other', 'vocals']
        for i, name in enumerate(stems):
            stem_path = os.path.join(output_dir, f'{name}.wav')
            separate.save_audio(sources[i].cpu(), stem_path, model.samplerate)
            print(f"WORKER: [OK] Pista '{name}' guardada.")

        print("WORKER: [OK DEMUCS] Separación de pistas completada.")

        # --- TRANSCRIPCIÓN CON BASIC-PITCH (CORREGIDO) ---
        path_to_transcribe = os.path.join(output_dir, 'other.wav')

        if os.path.exists(path_to_transcribe):
            print(f"WORKER: [INICIO BASIC-PITCH] Transcribiendo {path_to_transcribe}...")
            
            # --- ¡LÍNEA DE LA VICTORIA! ---
            # Comprobamos si el archivo MIDI de salida ya existe y lo borramos.
            midi_output_path = os.path.join(output_dir, f"{os.path.splitext('other.wav')[0]}_basic_pitch.mid")
            try:
                if os.path.exists(midi_output_path):
                    print(f"WORKER: Eliminando archivo MIDI antiguo: {midi_output_path}")
                    os.remove(midi_output_path)
            except OSError as e:
                print(f"WORKER: Error al eliminar el archivo MIDI antiguo: {e}")
            # --- Fin de la corrección ---

            predict_and_save(
                audio_path_list=[path_to_transcribe],
                output_directory=output_dir,
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                model_or_model_path=ICASSP_2022_MODEL_PATH
            )
            print("WORKER: [OK BASIC-PITCH] Transcripción a MIDI completada.")
        
        return "Proceso completado exitosamente."
    except Exception as e:
        print(f"WORKER: [ERROR GENERAL] Ocurrió un error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error en el procesamiento: {e}"