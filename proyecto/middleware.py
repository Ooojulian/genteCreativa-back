# backend/proyecto/middleware.py
import datetime
import logging
logger = logging.getLogger(__name__)

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print(f"\n[{datetime.datetime.now()}] **** RequestLogMiddleware Cargado ****\n")

    def __call__(self, request):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n[{timestamp}] >>> Middleware STARTING for: {request.method} {request.path}")
        print(f"\n--- INICIO MIDDLEWARE LOG ---")

        # --- Log ANTES de llamar a la siguiente capa ---
        user_before = getattr(request, 'user', 'No request.user attr (before)')
        auth_before = getattr(user_before, 'is_authenticated', 'N/A') if hasattr(user_before, 'is_authenticated') else 'N/A'
        print(f"[{timestamp}] User (Before get_response): {user_before}, Authenticated: {auth_before}")
        # -----------------------------------------------

        # --- Llama a la siguiente capa (Middleware/Vista) ---
        response = self.get_response(request)
        # ----------------------------------------------------

        # --- Log DESPUÉS de que la siguiente capa ha respondido ---
        user_after = getattr(request, 'user', 'No request.user attr (after)')
        auth_after = getattr(user_after, 'is_authenticated', 'N/A') if hasattr(user_after, 'is_authenticated') else 'N/A'
        print(f"[{timestamp}] User (After get_response): {user_after}, Authenticated: {auth_after}")
        # ------------------------------------------------

        # Resto de logs que ya tenías
        print(f"[{timestamp}] Method: {request.method}, Path: {request.path}")
        auth_header = request.headers.get('Authorization', 'No Auth Header')
        if auth_header.startswith('Bearer '): auth_header = f"Bearer {auth_header[7:17]}..."
        print(f"Auth Header: {auth_header}")
        print(f"[{timestamp}] Response Status Code: {response.status_code}")
        print(f"--- FIN MIDDLEWARE LOG ---\n")
        return response