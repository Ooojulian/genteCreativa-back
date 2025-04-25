# backend/proyecto/apps/usuarios/auth_urls.py (NUEVO ARCHIVO)

from django.urls import path
# Importa tu LoginView y RefreshTokenView personalizadas
from .views import LoginView, RefreshTokenView

# Si estuvieras usando las vistas por defecto de SimpleJWT (pero usamos LoginView personalizada):
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Apunta a tu vista de Login personalizada
    path('login/', LoginView.as_view(), name='token_obtain_pair'), # Puedes nombrarla 'login' o 'token_obtain_pair'
    # Apunta a tu vista de Refresh (o la por defecto)
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
]