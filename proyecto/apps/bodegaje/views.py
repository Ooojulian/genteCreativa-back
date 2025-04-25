# backend/proyecto/apps/bodegaje/views.py
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db import IntegrityError, DatabaseError 
from .models import Producto, Ubicacion, Inventario
from .serializers import ProductoSerializer, UbicacionSerializer, InventarioSerializer, MovimientoInventarioSerializer

from apps.usuarios.permissions import IsCliente, IsJefeEmpresa, IsJefeInventario
from django.core.exceptions import PermissionDenied
from .models import MovimientoInventario
import logging
from django.utils.translation import gettext_lazy as _ # Para mensajes de error

logger = logging.getLogger(__name__)

# Vista para listar inventario de UN cliente (si aún la necesitas)
# class InventarioListView(generics.ListAPIView):
#     serializer_class = InventarioSerializer
#     permission_classes = [IsAuthenticated, IsCliente]
#     def get_queryset(self):
#         user = self.request.user
#         if user.rol and user.rol.nombre == 'cliente' and user.empresa:
#             return Inventario.objects.filter(empresa=user.empresa).select_related('producto', 'ubicacion', 'empresa')
#         return Inventario.objects.none()

# ViewSet para Productos
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Admin, Jefe Empresa, Jefe Inventario pueden modificar
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsJefeInventario)]
        else: # list, retrieve
            permission_classes = [IsAuthenticated] # Cualquiera autenticado puede ver
        return [permission() for permission in permission_classes]

# ViewSet para Ubicaciones
class UbicacionViewSet(viewsets.ModelViewSet):
    queryset = Ubicacion.objects.all()
    serializer_class = UbicacionSerializer
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
             # Admin, Jefe Empresa, Jefe Inventario pueden modificar
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsJefeInventario)]
        else: # list, retrieve
            permission_classes = [IsAuthenticated] # Cualquiera autenticado puede ver
        return [permission() for permission in permission_classes]


class InventarioViewSet(viewsets.ModelViewSet):
    serializer_class = InventarioSerializer
    #permission_classes = [IsAuthenticated] # Permiso base

    def get_queryset(self):
        user = self.request.user
        # Logs para depuración
        logger.debug(f"\n--- DEBUG: InventarioViewSet.get_queryset ---") # Usar logger.debug
        logger.debug(f"User ID: {user.id}, Rol: {user.rol.nombre if user.rol else 'N/A'}")

        # Queryset base optimizado
        queryset = Inventario.objects.select_related('producto', 'ubicacion', 'empresa')

        # Si es Admin o Jefe (Empresa o Inventario), permitir filtrar por empresa
        if user.is_staff or (user.rol and user.rol.nombre in ['jefe_empresa', 'jefe_inventario', 'admin']):
            empresa_id_filtro = self.request.query_params.get('empresa_id')
            if empresa_id_filtro:
                try:
                    # Aplica el filtro si el parámetro existe y es válido
                    queryset = queryset.filter(empresa_id=int(empresa_id_filtro))
                    logger.debug(f"-> Vista Admin/Jefe: Filtrando por Empresa ID (param): {empresa_id_filtro}")
                except (ValueError, TypeError):
                    # Si el ID no es un número válido, decide qué hacer.
                    # Podrías devolver vacío, un error 400, o (como aquí) devolver todo.
                    logger.warning(f"-> Vista Admin/Jefe: empresa_id '{empresa_id_filtro}' inválido. Devolviendo todo el inventario.")
                    # No aplicamos filtro adicional, queryset ya tiene todos los items optimizados
            else:
                 logger.debug(f"-> Vista Admin/Jefe: No se especificó filtro empresa_id. Devolviendo TODO el inventario.")
            # Devuelve el queryset (filtrado o completo)
            return queryset

        # Si es Cliente, filtrar SIEMPRE por su propia empresa
        elif user.rol and user.rol.nombre == 'cliente' and user.empresa:
            logger.debug(f"-> Vista Cliente: Filtrando por Empresa ID (propia): {user.empresa.id} (Nombre: {user.empresa.nombre})")
            # Aplica el filtro por la empresa del usuario
            # select_related ya se aplicó al inicio, no es necesario repetirlo
            queryset = queryset.filter(empresa=user.empresa)
            logger.debug(f"-> Vista Cliente: Queryset encontró {queryset.count()} items para esta empresa.")
            return queryset

        # Otros roles o usuarios sin rol/empresa no deberían ver inventario general
        logger.debug("-> Vista Otro Rol/Sin Empresa: No cumple condiciones, devolviendo vacío.")
        return Inventario.objects.none() # Devuelve un queryset vacío
    
    def get_permissions(self):
        """
        Define permisos basados en la acción solicitada.
        """
        # Permisos por defecto más restrictivos si es necesario
        permission_classes = [IsAuthenticated] # Todos deben estar autenticados

        if self.action in ['update', 'partial_update', 'create', 'destroy']:
            # Solo Admin y Jefes pueden modificar/crear/borrar inventario
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsJefeInventario))
        elif self.action in ['list', 'retrieve']:
             # Cliente puede listar/ver detalle (get_queryset filtra su vista)
             # Jefes/Admin también pueden listar/ver detalle
             # Cualquiera autenticado podría ver detalles (si la lógica de get_queryset lo permite)
             # Mantenemos IsAuthenticated como base, get_queryset hace el filtrado fino
             pass # Ya tiene IsAuthenticated
        else:
            # Acciones personalizadas u otras podrían requerir permisos de Admin/Jefe
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsJefeInventario))

        # Instancia y devuelve las clases de permiso
        return [permission() for permission in permission_classes]

    # --- Métodos create, perform_create, perform_update, perform_destroy ---
    # (Asegúrate que estos métodos estén definidos como los tenías antes,
    # incluyendo el manejo de IntegrityError y la creación de logs
    # en MovimientoInventario si esa lógica sigue siendo necesaria)

    def create(self, request, *args, **kwargs):
        # Manejo de duplicados (sin cambios respecto a la versión anterior)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except IntegrityError:
            # ... (manejo de error 400 como antes) ...
            try: # Mensaje específico
                prod_nombre = serializer.validated_data.get('producto').nombre
                ubi_nombre = serializer.validated_data.get('ubicacion').nombre
                emp_nombre = serializer.validated_data.get('empresa').nombre
                error_msg = _(f"Ya existe inventario para '{prod_nombre}' en '{ubi_nombre}' para la empresa '{emp_nombre}'. Use editar.")
            except Exception: # Mensaje genérico
                error_msg = _("Ya existe una entrada de inventario para esta combinación. Use editar.")
            return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)

    # --- perform_create CON LOGGING ---
    def perform_create(self, serializer):
        user = self.request.user
        # Verifica permiso (redundante si get_permissions es correcto)
        if not (user.is_staff or (user.rol and user.rol.nombre in ['jefe_empresa', 'jefe_inventario'])):
             raise PermissionDenied("No tienes permiso para crear inventario.")

        # Guarda primero para tener el 'instance'
        instance = serializer.save()

        # --- Log de Creación ---
        try:
            MovimientoInventario.objects.create(
                inventario=instance,
                producto=instance.producto,
                ubicacion=instance.ubicacion,
                empresa=instance.empresa,
                tipo_movimiento='CREACION',
                cantidad_anterior=0, # Anterior es 0 al crear
                cantidad_nueva=instance.cantidad,
                cantidad_cambio=instance.cantidad, # El cambio es la cantidad total
                usuario=user,
                motivo="Registro inicial vía API."
            )
            print(f"INFO: Log de CREACION creado para Inventario ID {instance.id}")
        except Exception as e:
            print(f"ERROR al crear log de inventario para CREACION ID {instance.id}: {e}")
        # --- Fin Log ---
    # --- FIN perform_create ---

    # --- perform_update CON LOGGING ---
    def perform_update(self, serializer):
        # Obtiene el estado ANTES de guardar
        instance_pre_update = self.get_object()
        cantidad_anterior = instance_pre_update.cantidad

        # Guarda los cambios
        instance = serializer.save()

        # --- Log de Actualización ---
        try:
            cantidad_nueva = instance.cantidad
            cantidad_cambio = cantidad_nueva - cantidad_anterior
            # Solo registra si la cantidad realmente cambió
            if cantidad_cambio != 0:
                MovimientoInventario.objects.create(
                    inventario=instance,
                    producto=instance.producto,
                    ubicacion=instance.ubicacion,
                    empresa=instance.empresa,
                    tipo_movimiento='ACTUALIZACION',
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=cantidad_nueva,
                    cantidad_cambio=cantidad_cambio, # Diferencia
                    usuario=self.request.user,
                    motivo="Actualización de cantidad vía API."
                )
                print(f"INFO: Log de ACTUALIZACION creado para Inventario ID {instance.id}")
            else:
                print(f"INFO: No se creó log para Inventario ID {instance.id} porque la cantidad no cambió.")
        except Exception as e:
            print(f"ERROR al crear log de inventario para ACTUALIZACION ID {instance.id}: {e}")
        # --- Fin Log ---
    # --- FIN perform_update ---

    # --- perform_destroy CON LOGGING ---
    def perform_destroy(self, instance):
        user = self.request.user
        print(f"--- DEBUG: perform_destroy INICIADO ---")
        print(f"Usuario ID: {user.id}, Rol: {user.rol.nombre if user.rol else 'N/A'}")
        print(f"Intentando eliminar Inventario ID: {instance.id}")

        # Guarda datos ANTES de borrar para el log
        inventario_id_log = instance.id
        producto_log = instance.producto
        ubicacion_log = instance.ubicacion
        empresa_log = instance.empresa
        cantidad_log = instance.cantidad

        # Verifica permiso explícito
        can_delete = False
        if user.is_staff or (user.rol and user.rol.nombre in ['jefe_empresa', 'jefe_inventario']):
             can_delete = True
        if not can_delete:
            print(f"PERMISSION DENIED dentro de perform_destroy para usuario {user.id}")
            raise PermissionDenied("No tienes permiso para eliminar este registro.")

        try:
            instance.delete() # Intenta borrar de la BD
            print(f"Inventario ID: {inventario_id_log} BORRADO exitosamente de la BD.")

            # --- Log de Eliminación ---
            try:
                MovimientoInventario.objects.create(
                    inventario=None, # Ya no existe
                    producto=producto_log,
                    ubicacion=ubicacion_log,
                    empresa=empresa_log,
                    tipo_movimiento='ELIMINACION',
                    cantidad_anterior=cantidad_log,
                    cantidad_nueva=None, # Ya no hay cantidad
                    cantidad_cambio=-cantidad_log, # El cambio es la cantidad que había (negativo)
                    usuario=user,
                    motivo=f"Eliminación de registro ID {inventario_id_log} vía API."
                )
                print(f"INFO: Log de ELIMINACION creado para ex-Inventario ID {inventario_id_log}")
            except Exception as e:
                 print(f"ERROR al crear log de inventario para ELIMINACION ID {inventario_id_log}: {e}")
            # --- Fin Log ---

        except DatabaseError as e: print(f"ERROR DB borrando ID {inventario_id_log}: {e}"); raise e
        except Exception as e: print(f"ERROR Inesperado borrando ID {inventario_id_log}: {e}"); raise e
        print(f"--- FIN DEBUG: perform_destroy ---")

# --- NUEVA VISTA PARA CONSULTAR HISTORIAL ---
class HistorialInventarioView(generics.ListAPIView):
    """
    API para ver el historial de movimientos de inventario.
    Permite filtrar por query parameters (ej: ?producto_id=1&year=2025&month=4)
    """
    serializer_class = MovimientoInventarioSerializer
    # Define quién puede ver el historial completo
    permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsJefeInventario)]

    def get_queryset(self):
        queryset = MovimientoInventario.objects.all().select_related(
            'usuario', 'producto', 'ubicacion', 'empresa'
        ) # Empezamos con todos y optimizamos

        # --- Filtros Opcionales (Ejemplos) ---
        producto_id = self.request.query_params.get('producto_id')
        ubicacion_id = self.request.query_params.get('ubicacion_id')
        empresa_id = self.request.query_params.get('empresa_id')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        day = self.request.query_params.get('day') # Podrías filtrar por día también

        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if ubicacion_id:
            queryset = queryset.filter(ubicacion_id=ubicacion_id)
        if empresa_id:
             queryset = queryset.filter(empresa_id=empresa_id)

        # Filtrado por fecha
        if year:
            try: queryset = queryset.filter(timestamp__year=int(year))
            except ValueError: pass # Ignora si no es un año válido
        if month:
             try: queryset = queryset.filter(timestamp__month=int(month))
             except ValueError: pass
        if day:
             try: queryset = queryset.filter(timestamp__day=int(day))
             except ValueError: pass

        return queryset 