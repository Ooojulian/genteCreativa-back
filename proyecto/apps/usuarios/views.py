from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .permissions import IsOwner, IsConductor, IsCliente, IsJefeEmpresa, IsJefeInventario
from .models import Usuario, Rol, Empresa  # Importa los modelos
from .serializers import UsuarioSerializer, RolSerializer  # Importa los serializadores
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate
from .serializers import UsuarioSerializer, RolSerializer, MyTokenObtainPairSerializer, EmpresaSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import PermissionDenied 
from rest_framework.views import APIView


class MinimalAuthTestView(APIView):
    permission_classes = [IsAuthenticated] # Solo requiere autenticación

    def get(self, request):
        print(f"--- MinimalAuthTestView --- User: {request.user}, Auth: {request.user.is_authenticated}")
        return Response({"message": f"Hello authenticated user: {request.user.id} - {request.user.cedula}"})

#Para crear usuarios y listar usuarios
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Usuario.objects.all() # Empezamos con todos

        # --- PERMITIR FILTRADO POR ROL (para obtener conductores) ---
        rol_nombre = self.request.query_params.get('rol', None)
        if rol_nombre:
            queryset = queryset.filter(rol__nombre=rol_nombre)
        # --- FIN FILTRADO POR ROL ---

        # Filtrado de visibilidad general
        if user.is_staff or (user.rol and user.rol.nombre == 'jefe_empresa'):
             # Admins y Jefes ven la lista (potencialmente filtrada por rol arriba)
             return queryset.select_related('rol', 'empresa')
        elif user.is_authenticated:
            # Otros usuarios solo se ven a sí mismos en la lista general
            return queryset.filter(pk=user.pk).select_related('rol', 'empresa')
        return Usuario.objects.none()

    def get_permissions(self):
        """
        Jefe Empresa puede hacer casi lo mismo que Admin, excepto borrar usuarios?
        (Puedes ajustar esto)
        """
        if self.action == 'create' or self.action == 'list':
            # Crear y Listar: Admin o Jefe Empresa
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        elif self.action == 'retrieve':
             # Ver detalle: Admin, Jefe Empresa, o el propio usuario
             permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsOwner)]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAuthenticated, (IsAdminUser | IsOwner | IsJefeEmpresa )]
        elif self.action == 'destroy':
            # Eliminar: Solo Admin (Jefe no puede borrar usuarios)
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        else:
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        return [permission() for permission in permission_classes]

    # Para el login (obtener token) - Vista Personalizada.
class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer # <--- USA TU SERIALIZER PERSONALIZADO


class RefreshTokenView(TokenRefreshView):
    permission_classes = (IsAuthenticated,)

class ConductorLoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        cedula = request.data.get('cedula')

        if not cedula:
            return Response({'error': 'La cédula es obligatoria'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            usuario = Usuario.objects.get(cedula=cedula, rol__nombre='conductor')
        except Usuario.DoesNotExist:
            return Response({'error': 'Cédula no válida o no eres un conductor'}, status=status.HTTP_401_UNAUTHORIZED)

        # Autenticar al usuario (sin contraseña)
        user = authenticate(request, cedula=cedula)

        if user is not None:
                refresh = RefreshToken.for_user(user)
                return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })

        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

class ClienteLoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        cedula = request.data.get('cedula')
        if not cedula:
            return Response({'error': 'La cédula es obligatoria'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            usuario = Usuario.objects.get(cedula=cedula, rol__nombre='cliente')
        except Usuario.DoesNotExist:
            return Response({'error': 'Cédula no válida o no eres un cliente'}, status=status.HTTP_401_UNAUTHORIZED)

        # Autenticar al usuario (sin contraseña)
        user = authenticate(request, cedula=cedula)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            })

        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
    
    
class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

    def get_permissions(self):
        if self.action == 'create':
            # Crear: Admin o Jefe Empresa
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Editar/Borrar: Admin o Jefe Empresa (según lo dejamos antes)
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        else: # list, retrieve
            # Ver lista/detalle: Admin, Jefe Empresa, Y AHORA Jefe Inventario
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsJefeInventario)] 
        return [permission() for permission in permission_classes]