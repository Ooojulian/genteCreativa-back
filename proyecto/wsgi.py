import os
import sys
from pathlib import Path

# --- CORRECCIÓN AQUÍ ---
# Añade el directorio que CONTIENE 'apps' (es decir, 'proyecto/') al sys.path
PROJECT_DIR = Path(__file__).resolve().parent
# BASE_DIR = PROJECT_DIR.parent
# sys.path.append(str(BASE_DIR))
sys.path.append(str(PROJECT_DIR))
# --- FIN CORRECCIÓN ---

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')

application = get_wsgi_application()