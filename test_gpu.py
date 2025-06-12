import torch

print("--- Verificación de PyTorch y CUDA ---")
if torch.cuda.is_available():
    print("✅ ¡ÉXITO! PyTorch puede ver la GPU NVIDIA.")
    print(f"   Nombre del dispositivo: {torch.cuda.get_device_name(0)}")
    print(f"   Versión de CUDA detectada por PyTorch: {torch.version.cuda}")
    print(f"   Número de GPUs disponibles: {torch.cuda.device_count()}")
else:
    print("❌ FALLO. PyTorch NO puede ver la GPU.")
    print("   Por favor, revisa los pasos de instalación de los drivers de NVIDIA y el CUDA Toolkit.")
print("---------------------------------------")