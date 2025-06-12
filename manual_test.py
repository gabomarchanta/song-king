import subprocess
import shlex

print("--- INICIANDO PRUEBA MANUAL DE DEMUCS ---")

# Variables que vienen de la app
upload_path = 'uploads/CUANDO_BAJE_LA_MAREA.mp3'
stems_folder = 'static/stems'
model = 'htdemucs_ft'

# El mismo comando que está en tasks.py
command = f"python3 -m demucs -d cuda --two-stems vocals -n {model} -o \"{stems_folder}\" \"{upload_path}\""

print(f"Ejecutando comando: {command}")

try:
    # Ejecutamos el comando
    subprocess.run(shlex.split(command), check=True)
    print("✅ ¡ÉXITO! El proceso de Demucs terminó sin errores.")
except subprocess.CalledProcessError as e:
    print(f"❌ ¡FALLO! El proceso de Demucs devolvió un error: {e}")
except Exception as e:
    print(f"❌ ¡FALLO! Ocurrió un error inesperado de Python: {e}")

print("--- PRUEBA MANUAL FINALIZADA ---")