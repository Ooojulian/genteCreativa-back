# backend/proyecto/apps/bodegaje/middleware.py
import threading

_thread_locals = threading.local()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Almacena el usuario (o None si es anónimo) antes de procesar la vista
        _thread_locals.user = getattr(request, 'user', None)
        response = self.get_response(request)
        # Limpia el usuario después de que la respuesta se ha generado
        if hasattr(_thread_locals, 'user'):
            del _thread_locals.user
        return response

def get_current_user():
    """Función helper para obtener el usuario desde cualquier lugar."""
    return getattr(_thread_locals, 'user', None)