import os
import subprocess
import shlex
import shutil
import pretty_midi
import librosa
import numpy as np
from sklearn.mixture import GaussianMixture

# basic-pitch se importa dentro de las funciones para evitar problemas de inicialización
# en el hilo principal cuando se usa Flask en modo debug.

def separate_instruments_in_other(audio_path, midi_path, output_dir):
    """Separa instrumentos en la pista 'other' usando clustering de características de audio"""
    try:
        print("TASK [Other-Clustering]: Iniciando clustering...")
        
        # Validar que los archivos existen
        if not os.path.exists(audio_path):
            print(f"TASK [Other-Clustering]: Archivo de audio no encontrado: {audio_path}")
            return
            
        if not os.path.exists(midi_path):
            print(f"TASK [Other-Clustering]: Archivo MIDI no encontrado: {midi_path}")
            return
            
        # Validar que el directorio de salida existe
        if not os.path.exists(output_dir):
            print(f"TASK [Other-Clustering]: Directorio de salida no encontrado: {output_dir}")
            return
            
        # Cargar audio y MIDI con validaciones
        try:
            y, sr = librosa.load(audio_path, sr=None)
            if len(y) == 0:
                print("TASK [Other-Clustering]: El archivo de audio está vacío")
                return
        except Exception as e:
            print(f"TASK [Other-Clustering]: Error cargando audio: {str(e)}")
            return
            
        try:
            pm = pretty_midi.PrettyMIDI(midi_path)
        except Exception as e:
            print(f"TASK [Other-Clustering]: Error cargando MIDI: {str(e)}")
            return
        
        all_notes = []
        for instrument in pm.instruments:
            if not instrument.is_drum:  # Excluir pistas de batería
                all_notes.extend(instrument.notes)
                
        if not all_notes: 
            print("TASK [Other-Clustering]: No se encontraron notas melódicas en el MIDI")
            return

        notes_with_features = []
        for note in all_notes:
            # Validar que las notas tienen tiempos válidos
            if note.start >= note.end or note.start < 0:
                continue
                
            start_sample, end_sample = librosa.time_to_samples([note.start, note.end], sr=sr)
            
            # Validar límites del array de audio
            if start_sample >= len(y) or end_sample >= len(y) or start_sample < 0:
                continue
                
            note_audio = y[start_sample:end_sample]
            if len(note_audio) == 0: 
                continue
                
            try:
                mfccs = librosa.feature.mfcc(y=note_audio, sr=sr, n_mfcc=13)
                if mfccs.size > 0:  # Verificar que se extrajeron características
                    notes_with_features.append({'note': note, 'features': np.mean(mfccs, axis=1)})
            except Exception as e:
                print(f"TASK [Other-Clustering]: Error extrayendo MFCC para nota: {str(e)}")
                continue

        if len(notes_with_features) < 2: 
            print("TASK [Other-Clustering]: Muy pocas notas válidas para clustering")
            return

        X = np.array([item['features'] for item in notes_with_features])
        
        # Validar que las características son válidas
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            print("TASK [Other-Clustering]: Características contienen valores inválidos")
            return
            
        n_components_range = range(2, min(4, len(notes_with_features)))
        if len(n_components_range) == 0:
            print("TASK [Other-Clustering]: Muy pocas notas para clustering")
            return
            
        try:
            bic = []
            for n in n_components_range:
                gmm = GaussianMixture(n, random_state=0, max_iter=100)
                gmm.fit(X)
                bic.append(gmm.bic(X))
            
            optimal_n_components = n_components_range[np.argmin(bic)]
            
            final_gmm = GaussianMixture(n_components=optimal_n_components, random_state=0, max_iter=100)
            final_gmm.fit(X)
            labels = final_gmm.predict(X)
        except Exception as e:
            print(f"TASK [Other-Clustering]: Error en clustering: {str(e)}")
            return

        for i, item in enumerate(notes_with_features):
            item['cluster'] = labels[i]
        
        instrument_names = ["guitar", "piano", "synth"]
        successful_clusters = 0
        
        for i in range(optimal_n_components):
            try:
                instrument_midi = pretty_midi.PrettyMIDI()
                instrument_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
                inst = pretty_midi.Instrument(program=instrument_program)
                
                cluster_notes = []
                for item in notes_with_features:
                    if item['cluster'] == i:
                        cluster_notes.append(item['note'])
                
                if cluster_notes: # Solo proceder si hay notas en este cluster
                    inst.notes.extend(cluster_notes)
                    instrument_midi.instruments.append(inst)
                    
                    output_midi_path = os.path.join(output_dir, f"other_cluster_{i}_{instrument_names[i%len(instrument_names)]}.mid")
                    instrument_midi.write(output_midi_path)
                    successful_clusters += 1
                    print(f"TASK [Other-Clustering]: Guardado {output_midi_path} con {len(cluster_notes)} notas")
                    
            except Exception as e:
                print(f"TASK [Other-Clustering]: Error guardando cluster {i}: {str(e)}")
                continue
                
        print(f"TASK [Other-Clustering]: Completado con {successful_clusters} clusters exitosos")

    except Exception as e:
        print(f"TASK [Other-Clustering]: Error inesperado durante clustering: {str(e)}")
        import traceback
        traceback.print_exc()

def process_song(upload_path, stems_folder, progress_callback=None):
    """Procesa una canción: separa pistas, transcribe a MIDI y clasifica instrumentos"""
    
    def update_progress(message, progress):
        """Helper para actualizar progreso"""
        if progress_callback:
            progress_callback(message, progress)
        print(f"TASK [Main]: {message} ({progress}%)")
    
    try:
        # Validar archivo de entrada
        if not os.path.exists(upload_path):
            print(f"TASK [Main]: Error - Archivo no encontrado: {upload_path}")
            return
            
        # Validar que el archivo no está vacío
        if os.path.getsize(upload_path) == 0:
            print(f"TASK [Main]: Error - Archivo vacío: {upload_path}")
            return
            
        song_name_without_ext = os.path.splitext(os.path.basename(upload_path))[0]
        model = "htdemucs"
        
        update_progress(f"Iniciando procesamiento de '{song_name_without_ext}'", 5)
        
        # 1. Ejecutar Demucs para separación de pistas
        import torch; device="cuda" if torch.cuda.is_available() else "cpu"; command=f"python -m demucs --device {device} -n {model} \"{upload_path}\""; print(f"TASK [Main]: Usando {device.upper()}")
        
        update_progress("Separando pistas con Demucs...", 10)
        try:
            # Obtener timeout de configuración
            timeout = int(os.environ.get('DEMUCS_TIMEOUT', 1800))  # 30 minutos por defecto
            result = subprocess.run(shlex.split(command), check=True, capture_output=True, text=True, timeout=timeout)
            update_progress("Separación de pistas completada", 40)
        except subprocess.TimeoutExpired:
            print(f"TASK [Main]: Error - Timeout en procesamiento de Demucs (límite: {timeout} segundos)")
            raise
        except subprocess.CalledProcessError as e:
            print(f"TASK [Main]: Error ejecutando Demucs: {str(e)}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"TASK [Main]: Stderr: {e.stderr}")
            raise

        # 2. Definir rutas de origen y destino con separadores correctos
        demucs_default_output = os.path.join('separated', model, song_name_without_ext)
        final_output_dir = os.path.join(stems_folder, song_name_without_ext, model)
        
        # Normalizar rutas para el entorno actual
        demucs_default_output = os.path.normpath(demucs_default_output)
        final_output_dir = os.path.normpath(final_output_dir)
        
        # 3. Validar que Demucs generó resultados
        if not os.path.exists(demucs_default_output):
            raise FileNotFoundError(f"La carpeta de salida de Demucs no se encontró en {demucs_default_output}")
            
        # Verificar que hay archivos en la salida
        try:
            output_files = os.listdir(demucs_default_output)
            if not output_files:
                raise ValueError(f"La carpeta de salida de Demucs está vacía: {demucs_default_output}")
        except OSError as e:
            raise OSError(f"Error accediendo a la carpeta de salida de Demucs: {str(e)}")
        
        # 4. Mover resultados a la ubicación final
        update_progress("Organizando archivos de salida...", 45)
        try:
            os.makedirs(os.path.dirname(final_output_dir), exist_ok=True)
            shutil.move(demucs_default_output, final_output_dir)
            
            # Limpiar carpeta 'separated' si queda vacía
            try:
                separated_model_dir = os.path.join('separated', model)
                if os.path.exists(separated_model_dir) and not os.listdir(separated_model_dir):
                    os.rmdir(separated_model_dir)
                if os.path.exists('separated') and not os.listdir('separated'):
                    os.rmdir('separated')
            except OSError:
                pass  # No pasa nada si no se puede limpiar
        except (OSError, shutil.Error) as e:
            print(f"TASK [Main]: Error moviendo archivos: {str(e)}")
            raise

        # 5. Transcribir pistas a MIDI
        output_dir = final_output_dir
        tracks_to_transcribe = ["vocals", "bass", "other"]
        successful_transcriptions = 0
        update_progress("Iniciando transcripción a MIDI...", 50)

        midi_files = []

        for i, track_name in enumerate(tracks_to_transcribe):
            audio_track_path = os.path.normpath(os.path.join(output_dir, f"{track_name}.wav"))
            if os.path.exists(audio_track_path):
                # Verificar que el archivo no está vacío
                if os.path.getsize(audio_track_path) == 0:
                    print(f"TASK [Main]: Saltando {track_name}.wav - archivo vacío")
                    continue
                    
                progress = 50 + (i + 1) * 15  # 50-95% para transcripciones
                update_progress(f"Transcribiendo {track_name}.wav...", progress)
                try:
                    print(f"TASK [Main]: Intentando transcribir {audio_track_path}")
                    print(f"TASK [Main]: Directorio de salida: {output_dir}")
                    
                    # Usar la API de Python de basic-pitch en lugar del comando CLI
                    print(f"TASK [Main]: Ejecutando transcripción MIDI para {track_name}...")
                    
                    try:
                        from basic_pitch.inference import predict_and_save
                        from basic_pitch import ICASSP_2022_MODEL_PATH
                        import librosa
                        
                        # Verificar que el archivo de audio es válido
                        if not os.path.exists(audio_track_path):
                            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_track_path}")
                        
                        if os.path.getsize(audio_track_path) == 0:
                            raise ValueError(f"Archivo de audio vacío: {audio_track_path}")
                        
                        # Cargar audio para verificar que es válido
                        try:
                            audio_data, sr = librosa.load(audio_track_path, sr=22050)
                            if len(audio_data) == 0:
                                raise ValueError(f"No se pudo cargar audio de: {audio_track_path}")
                            print(f"TASK [Main]: Audio cargado: {len(audio_data)} samples, SR: {sr}Hz")
                        except Exception as audio_error:
                            raise RuntimeError(f"Error cargando audio {audio_track_path}: {audio_error}")
                        
                        # Ejecutar la transcripción usando la API de basic-pitch
                        # Usar modelo por defecto (se descarga automáticamente)
                        predict_and_save(
                            audio_path_list=[audio_track_path],
                            output_directory=output_dir,
                            model_or_model_path=ICASSP_2022_MODEL_PATH,
                            save_midi=True,
                            sonify_midi=False,
                            save_model_outputs=False,
                            save_notes=False
                        )
                        
                        print(f"TASK [Main]: basic-pitch API ejecutado exitosamente para {track_name}")
                        
                    except ImportError as import_error:
                        raise RuntimeError(f"Error importando basic-pitch: {import_error}. Verifica la instalación.")
                    except Exception as api_error:
                        raise RuntimeError(f"Error en basic-pitch API: {api_error}")
                    
                    # Verificar que se generó el archivo MIDI
                    expected_midi = os.path.join(output_dir, f"{track_name}_basic_pitch.mid")
                    if os.path.exists(expected_midi):
                        print(f"TASK [Main]: MIDI generado exitosamente: {expected_midi}")
                        midi_files.append(expected_midi)
                        successful_transcriptions += 1
                    else:
                        # Buscar archivos MIDI generados con cualquier nombre
                        midi_pattern = os.path.join(output_dir, "*.mid")
                        import glob
                        found_midis = glob.glob(midi_pattern)
                        new_midis = [f for f in found_midis if f not in midi_files]
                        if new_midis:
                            print(f"TASK [Main]: Archivos MIDI encontrados: {new_midis}")
                            midi_files.extend(new_midis)
                            successful_transcriptions += 1
                        else:
                            print(f"TASK [Main]: No se encontró MIDI para {track_name}")
                    
                    # Listar contenido del directorio para debug
                    print(f"TASK [Main]: Contenido de {output_dir}: {os.listdir(output_dir)}")
                    
                except subprocess.CalledProcessError as e:
                    print(f"TASK [Main]: Error transcribiendo {track_name}: {e}")
                    print(f"TASK [Main]: Return code: {e.returncode}")
                    if e.stdout:
                        print(f"TASK [Main]: stdout: {e.stdout}")
                    if e.stderr:
                        print(f"TASK [Main]: stderr: {e.stderr}")
                except Exception as e:
                    print(f"TASK [Main]: Error inesperado transcribiendo {track_name}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"TASK [Main]: Advertencia - No se encontró {track_name}.wav")
        
        update_progress(f"Completadas {successful_transcriptions} transcripciones", 90)
        
        # 6. Procesar clustering de instrumentos en 'other'
        other_audio_path = os.path.normpath(os.path.join(output_dir, "other.wav"))
        other_midi_path = os.path.normpath(os.path.join(output_dir, "other_basic_pitch.mid"))
        
        if os.path.exists(other_audio_path) and os.path.exists(other_midi_path):
            # Verificar que ambos archivos tienen contenido válido
            if os.path.getsize(other_audio_path) > 0 and os.path.getsize(other_midi_path) > 0:
                update_progress("Analizando instrumentos adicionales...", 95)
                try:
                    separate_instruments_in_other(other_audio_path, other_midi_path, output_dir)
                    # Limpiar archivo MIDI temporal solo si el clustering fue exitoso
                    try:
                        os.remove(other_midi_path)
                        print(f"TASK [Main]: Archivo temporal eliminado: {other_midi_path}")
                    except OSError as e:
                        print(f"TASK [Main]: No se pudo eliminar {other_midi_path}: {str(e)}")
                except Exception as e:
                    print(f"TASK [Main]: Error en clustering de instrumentos: {str(e)}")
            else:
                print("TASK [Main]: Archivos de audio u MIDI 'other' están vacíos, saltando clustering")
        else:
            print("TASK [Main]: No se encontraron archivos necesarios para clustering de 'other'")

        update_progress(f"Proceso completado exitosamente para '{song_name_without_ext}'", 100)

    except subprocess.CalledProcessError as e:
        print(f"TASK [Main]: Error ejecutando Demucs: {str(e)}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"TASK [Main]: Stderr: {e.stderr}")
        raise
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"TASK [Main]: Error de archivos procesando '{upload_path}': {str(e)}")
        raise
    except Exception as e:
        print(f"TASK [Main]: Error inesperado procesando '{upload_path}': {str(e)}")
        import traceback
        traceback.print_exc()
        raise