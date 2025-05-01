# backend/proyecto/apps/usuarios/views.py

import logging # <-- Añadir import para logging
from rest_framework import viewsets, status, filters, generics, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action # <-- Importar action
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend

from .permissions import IsOwner, IsConductor, IsCliente, IsJefeEmpresa, IsJefeInventario # <-- Permisos existentes
from .models import Usuario, Rol, Empresa
from .serializers import ( # <-- Serializadores necesarios
    UsuarioSerializer,
    MyTokenObtainPairSerializer,
    EmpresaSerializer,
    RolSerializer,
    CambiarPasswordSerializer # <-- Importar el nuevo serializer
)
from .filters import UsuarioFilter # <-- Filtro existente

# Configurar logger
logger = logging.getLogger(__name__)

# --- Vistas Existentes (Sin cambios, excepto quitar las innecesarias) ---

class MinimalAuthTestView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        logger.debug(f"MinimalAuthTestView - User: {request.user}, Auth: {request.user.is_authenticated}")
        return Response({"message": f"Hello authenticated user: {request.user.id} - {request.user.cedula}"})

class RolListView(generics.ListAPIView):
    queryset = Rol.objects.all().order_by('id')
    serializer_class = RolSerializer
    permission_classes = [permissions.IsAuthenticated]

class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer

class RefreshTokenView(TokenRefreshView):
    permission_classes = (IsAuthenticated,) # Refresh requiere estar autenticado (tener un refresh token válido)

# --- QUITAR VISTAS REDUNDANTES/INSEGURAS ---
# Quitar ConductorLoginView y ClienteLoginView si no se usan y se prefiere el login estándar con contraseña
# class ConductorLoginView(TokenObtainPairView): ... (ELIMINAR)
# class ClienteLoginView(TokenObtainPairView): ... (ELIMINAR)
# --- FIN QUITAR ---


# --- ViewSet para Usuarios (Modificado) ---
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related('rol', 'empresa').all()
    serializer_class = UsuarioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = UsuarioFilter
    search_fields = ['cedula', 'nombre', 'apellido', 'email', 'username']

    def get_queryset(self):
        # La lógica para filtrar el queryset base según filtros ya está bien aquí
        # Usa super().get_queryset() que aplica filter_backends
        queryset = super().get_queryset()
        logger.debug(f"UsuarioViewSet get_queryset: Filtros aplicados, devolviendo queryset.")
        return queryset

    def get_permissions(self):
        """
        Define permisos basados en la acción solicitada.
        Incluye permiso para la nueva acción 'cambiar_password'.
        """
        permission_classes = [IsAuthenticated] # Requerido para todas las acciones

        if self.action == 'create' or self.action == 'list':
            # Crear y Listar: Admin o Jefe Empresa
            permission_classes.append((IsAdminUser | IsJefeEmpresa))
        elif self.action == 'retrieve':
             # Ver detalle: Admin, Jefe Empresa, o el propio usuario
             permission_classes.append((IsAdminUser | IsJefeEmpresa | IsOwner))
        elif self.action in ['update', 'partial_update']:
            # Modificar datos (no contraseña): Admin, Jefe Empresa, o el propio usuario
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsOwner ))
        elif self.action == 'destroy':
            # Eliminar: Solo Admin o Jefe Empresa (ajusta si es necesario)
            permission_classes.append((IsAdminUser | IsJefeEmpresa))
        # --- NUEVO: Permiso para la acción de cambiar contraseña ---
        elif self.action == 'cambiar_password':
            # Solo Admin y Jefe Empresa pueden cambiar contraseñas de otros
            permission_classes.append((IsAdminUser | IsJefeEmpresa))
        # --- FIN NUEVO ---
        else:
            # Acción desconocida, restringir por defecto a Admin/Jefe
            permission_classes.append((IsAdminUser | IsJefeEmpresa))

        # Retorna instancias de las clases de permiso
        return [permission() for permission in permission_classes]

    # --- NUEVA ACCIÓN PERSONALIZADA para cambiar contraseña ---
    @action(detail=True, methods=['post'], url_path='cambiar-password', permission_classes=[IsAuthenticated, (IsAdminUser | IsJefeEmpresa)])
    def cambiar_password(self, request, pk=None):
        """
        Endpoint para que Admin/Jefe Empresa cambie la contraseña de un usuario.
        URL: /api/gestion/usuarios/{pk}/cambiar-password/
        Espera: {'new_password': '...', 'confirm_password': '...'}
        """
        logger.info(f"Intento de cambio de contraseña para usuario PK={pk} por usuario {request.user.cedula}")
        user_a_modificar = self.get_object() # Obtiene el usuario por PK (maneja 404)

        serializer = CambiarPasswordSerializer(
            data=request.data,
            context={'user': user_a_modificar} # Pasamos el usuario para el método save del serializer
        )

        if serializer.is_valid():
            try:
                # El método save del serializer hashea y guarda la contraseña
                serializer.save()
                logger.info(f"Contraseña cambiada exitosamente para usuario {user_a_modificar.cedula} por {request.user.cedula}")
                return Response({"detail": "Contraseña actualizada exitosamente."}, status=status.HTTP_200_OK)
            except Exception as e:
                 # Captura errores inesperados durante el guardado
                 logger.error(f"Error al guardar nueva contraseña para {user_a_modificar.cedula}: {e}", exc_info=True)
                 return Response({"detail": "Error interno al guardar la contraseña."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Devuelve los errores de validación del serializer
            logger.warning(f"Validación fallida al cambiar contraseña para {user_a_modificar.cedula}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    # --- FIN NUEVA ACCIÓN ---

    # Métodos create, update, partial_update, destroy pueden quedarse como estaban
    # si no necesitan lógica adicional más allá de lo que hacen los serializers y permisos.
    # Por ejemplo, el serializer ya maneja la lógica de rol/empresa/vehículo.

    def perform_create(self, serializer):
        # El serializer se encarga de hashear la contraseña y validar
        user = serializer.save()
        logger.info(f"Usuario {user.cedula} creado por {self.request.user.cedula}")

    def perform_update(self, serializer):
        # El serializer maneja la actualización, password se ignora aquí si no se manda
        instance = serializer.save()
        logger.info(f"Usuario {instance.cedula} actualizado por {self.request.user.cedula}")

    def perform_destroy(self, instance):
        user_cedula = instance.cedula
        logger.warning(f"Usuario {user_cedula} eliminado por {self.request.user.cedula}")
        instance.delete()


# --- ViewSet para Empresas (Sin cambios respecto a tu versión) ---
class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all().order_by('nombre') # Ordenar es buena idea
    serializer_class = EmpresaSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'nit']

    def get_permissions(self):
        permission_classes = [IsAuthenticated] # Base
        if self.action == 'create':
            permission_classes.append((IsAdminUser | IsJefeEmpresa))
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes.append((IsAdminUser | IsJefeEmpresa))
        else: # list, retrieve
            # Permitir ver a Admin, Jefes (Empresa e Inventario)
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsJefeInventario))
        return [permission() for permission in permission_classes]