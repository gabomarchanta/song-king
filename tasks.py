import os
import subprocess
import shlex
import pretty_midi
import librosa
import numpy as np
from sklearn.mixture import GaussianMixture

# basic-pitch se importa dentro de las funciones para evitar problemas de inicialización
# en el hilo principal cuando se usa Flask en modo debug.

def separate_instruments_in_other(audio_path, midi_path, output_dir):
    from basic_pitch import ICASSP_2022_MODEL_PATH
    try:
        print("TASK [Other-Clustering]: Iniciando clustering...")
        y, sr = librosa.load(audio_path, sr=None)
        pm = pretty_midi.PrettyMIDI(midi_path)
        
        all_notes = []
        for instrument in pm.instruments:
            all_notes.extend(instrument.notes)
        if not all_notes: return

        notes_with_features = []
        for note in all_notes:
            start_sample, end_sample = librosa.time_to_samples([note.start, note.end], sr=sr)
            note_audio = y[start_sample:end_sample]
            if len(note_audio) == 0: continue
            mfccs = librosa.feature.mfcc(y=note_audio, sr=sr, n_mfcc=13)
            notes_with_features.append({'note': note, 'features': np.mean(mfccs, axis=1)})

        if not notes_with_features: return

        X = np.array([item['features'] for item in notes_with_features])
        n_components_range = range(2, 4)
        bic = [GaussianMixture(n, random_state=0).fit(X).bic(X) for n in n_components_range]
        optimal_n_components = n_components_range[np.argmin(bic)]
        
        final_gmm = GaussianMixture(n_components=optimal_n_components, random_state=0).fit(X)
        labels = final_gmm.predict(X)

        for i, item in enumerate(notes_with_features):
            item['cluster'] = labels[i]
        
        instrument_names = ["guitar", "piano", "synth"]
        for i in range(optimal_n_components):
            instrument_midi = pretty_midi.PrettyMIDI()
            instrument_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
            inst = pretty_midi.Instrument(program=instrument_program)
            
            for item in notes_with_features:
                if item['cluster'] == i:
                    inst.notes.append(item['note'])
            
            if inst.notes: # Solo guardar si tiene notas
                instrument_midi.instruments.append(inst)
                output_midi_path = os.path.join(output_dir, f"other_cluster_{i}_{instrument_names[i%len(instrument_names)]}.mid")
                instrument_midi.write(output_midi_path)
                print(f"TASK [Other-Clustering]: Guardado {output_midi_path}")

    except Exception as e:
        import traceback
        traceback.print_exc()

def process_song(upload_path, stems_folder):
    from basic_pitch.inference import predict_and_save
    
    try:
        song_name_without_ext = os.path.splitext(os.path.basename(upload_path))[0]
        model = "htdemucs"
        
        # --- ¡EL COMANDO DE LA VICTORIA! ---
        # Este patrón le dice a Demucs que cree una carpeta con el nombre de la canción
        # y dentro, los archivos de pista con su nombre y extensión.
        # {name} -> nombre del archivo de entrada sin extensión
        # {track} -> nombre de la pista (vocals, bass, etc.)
        # {ext} -> la extensión (.wav)
        filename_pattern = f"\"{model}/{{name}}/{{track}}.{{ext}}\""
        command = f"python3 -m demucs -n {model} -o \"{stems_folder}\" --filename {filename_pattern} \"{upload_path}\""
        
        print(f"TASK [Main]: Separando pistas con Demucs...")
        subprocess.run(shlex.split(command), check=True)
        print("TASK [Main]: Separación completada.")

        # Ahora la ruta de salida es correcta
        output_dir = os.path.join(stems_folder, model, song_name_without_ext)
        tracks_to_transcribe = ["vocals", "bass", "other"]

        for track_name in tracks_to_transcribe:
            audio_track_path = os.path.join(output_dir, f"{track_name}.wav")
            if os.path.exists(audio_track_path):
                print(f"TASK [Main]: Transcribiendo {track_name}.wav...")
                predict_and_save(
                    audio_path_list=[audio_track_path],
                    output_directory=output_dir,
                    save_midi=True, save_notes=False, save_model_outputs=False
                )
        
        other_audio_path = os.path.join(output_dir, "other.wav")
        other_midi_path = os.path.join(output_dir, "other_basic_pitch.mid")
        if os.path.exists(other_audio_path) and os.path.exists(other_midi_path):
            separate_instruments_in_other(other_audio_path, other_midi_path, output_dir)
            os.remove(other_midi_path) 

        print(f"TASK [Main]: Proceso completado para {song_name_without_ext}.")

    except Exception as e:
        import traceback
        traceback.print_exc()

# Rellenamos la función de clustering
def separate_instruments_in_other(audio_path, midi_path, output_dir):
    from basic_pitch import ICASSP_2022_MODEL_PATH
    try:
        print("TASK [Other-Clustering]: Iniciando clustering...")
        y, sr = librosa.load(audio_path, sr=None)
        pm = pretty_midi.PrettyMIDI(midi_path)
        all_notes = []
        for instrument in pm.instruments: all_notes.extend(instrument.notes)
        if not all_notes: return

        notes_with_features = []
        for note in all_notes:
            start_sample, end_sample = librosa.time_to_samples([note.start, note.end], sr=sr)
            note_audio = y[start_sample:end_sample]
            if len(note_audio) == 0: continue
            mfccs = librosa.feature.mfcc(y=note_audio, sr=sr, n_mfcc=13)
            notes_with_features.append({'note': note, 'features': np.mean(mfccs, axis=1)})

        if not notes_with_features: return

        X = np.array([item['features'] for item in notes_with_features])
        n_components_range = range(2, 4)
        bic = [GaussianMixture(n, random_state=0).fit(X).bic(X) for n in n_components_range]
        optimal_n_components = n_components_range[np.argmin(bic)]
        
        final_gmm = GaussianMixture(n_components=optimal_n_components, random_state=0).fit(X)
        labels = final_gmm.predict(X)

        for i, item in enumerate(notes_with_features):
            item['cluster'] = labels[i]
        
        instrument_names = ["guitar", "piano", "synth"]
        for i in range(optimal_n_components):
            instrument_midi = pretty_midi.PrettyMIDI()
            instrument_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
            inst = pretty_midi.Instrument(program=instrument_program)
            
            for item in notes_with_features:
                if item['cluster'] == i:
                    inst.notes.append(item['note'])
            
            if inst.notes:
                instrument_midi.instruments.append(inst)
                output_midi_path = os.path.join(output_dir, f"other_cluster_{i}_{instrument_names[i%len(instrument_names)]}.mid")
                instrument_midi.write(output_midi_path)
                print(f"TASK [Other-Clustering]: Guardado {output_midi_path}")

    except Exception as e:
        import traceback
        traceback.print_exc()