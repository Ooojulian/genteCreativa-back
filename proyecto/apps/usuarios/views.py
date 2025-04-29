from rest_framework import viewsets, status, filters,generics, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .permissions import IsOwner, IsConductor, IsCliente, IsJefeEmpresa, IsJefeInventario
from .models import Usuario, Rol, Empresa  # Importa los modelos
from .serializers import UsuarioSerializer  # Importa los serializadores
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate
from .serializers import UsuarioSerializer, MyTokenObtainPairSerializer, EmpresaSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .filters import UsuarioFilter
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import RolSerializer


class MinimalAuthTestView(APIView):
    permission_classes = [IsAuthenticated] # Solo requiere autenticación

    def get(self, request):
        print(f"--- MinimalAuthTestView --- User: {request.user}, Auth: {request.user.is_authenticated}")
        return Response({"message": f"Hello authenticated user: {request.user.id} - {request.user.cedula}"})

class RolListView(generics.ListAPIView):
    queryset = Rol.objects.all().order_by('id') # Obtiene todos los roles
    serializer_class = RolSerializer
    # Define quién puede ver la lista de roles (ej. cualquier autenticado)
    permission_classes = [permissions.IsAuthenticated]

#Para crear usuarios y listar usuarios
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related('rol', 'empresa').all()
    serializer_class = UsuarioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = UsuarioFilter
    search_fields = ['cedula', 'nombre', 'apellido', 'email', 'username']

    def get_queryset(self):
        print(f"DEBUG: Query Params recibidos en UsuarioViewSet.get_queryset: {self.request.query_params}")
        user = self.request.user
        # super().get_queryset() AHORA devuelve el queryset YA filtrado por los backends
        queryset = super().get_queryset()

        # QUITAR EL FILTRADO MANUAL POR ROL DE AQUÍ
        # rol_nombre = self.request.query_params.get('rol', None) # <-- BORRAR ESTO
        # if rol_nombre:                                          # <-- BORRAR ESTO
        #     queryset = queryset.filter(rol__nombre=rol_nombre)  # <-- BORRAR ESTO

        # Lógica de visibilidad (si es necesaria además de permisos)
        if self.action == 'list':
             if user.is_staff or (user.rol and user.rol.nombre == 'jefe_empresa'):
                 return queryset
             else:
                 return queryset # Devuelve lo filtrado por backends/permisos
        return queryset

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

    # --- AÑADIR ESTAS LÍNEAS ---
    filter_backends = [filters.SearchFilter] # Activa el backend de búsqueda
    search_fields = ['nombre', 'nit']       # Define en qué campos buscar
    # --------------------------

    # El método get_permissions sigue igual que antes
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