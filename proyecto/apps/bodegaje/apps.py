# backend/proyecto/apps/bodegaje/apps.py
from django.apps import AppConfig

class BodegajeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bodegaje'

    # --- AÑADIR MÉTODO ready ---
    def ready(self):
        try:
            import apps.bodegaje.signals  # Importa el archivo de señales
            print("Señales de Bodegaje cargadas correctamente.")
        except ImportError:
            print("Advertencia: No se pudo importar signals.py de Bodegaje.")
            pass # Evita errores si el archivo no existe o hay problemas
    # --- FIN AÑADIR ---