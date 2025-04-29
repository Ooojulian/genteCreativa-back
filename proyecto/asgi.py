import os
import sys
from pathlib import Path

# --- CORRECCIÓN AQUÍ ---
# Añade el directorio que CONTIENE 'apps' (es decir, 'proyecto/') al sys.path
# Path(__file__).resolve().parent es 'proyecto/'
PROJECT_DIR = Path(__file__).resolve().parent
# Path(__file__).resolve().parent.parent es 'backend/' (lo necesitamos para importar 'proyecto' si fuera necesario, aunque manage.py ya lo hace)
# BASE_DIR = PROJECT_DIR.parent
# sys.path.append(str(BASE_DIR)) # Añadimos backend/ por si acaso
sys.path.append(str(PROJECT_DIR)) # Añadimos proyecto/ que contiene apps/
# --- FIN CORRECCIÓN ---

# Código de diagnóstico (puedes mantenerlo o quitarlo)
print("--- ASGI sys.path (CORREGIDO) ---")
import pprint
pprint.pprint(sys.path)
print("--- FIN ASGI sys.path (CORREGIDO) ---")

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')

print(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
print("Llamando a get_asgi_application()...")

application = get_asgi_application()

print("get_asgi_application() llamado.")