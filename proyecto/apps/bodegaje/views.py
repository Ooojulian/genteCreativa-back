# backend/proyecto/apps/bodegaje/views.py
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db import IntegrityError, DatabaseError, transaction
from .models import Producto, Ubicacion, Inventario, MovimientoInventario, Inventario
from .serializers import ProductoSerializer, UbicacionSerializer, InventarioSerializer, MovimientoInventarioSerializer, EntradaInventarioSerializer, SalidaInventarioSerializer, InventarioSerializer
from django.shortcuts import get_object_or_404 # <-- Útil para buscar objetos
from rest_framework.decorators import action # <-- Importa action
from apps.usuarios.permissions import IsCliente, IsJefeEmpresa, IsJefeInventario
from apps.usuarios.models import Empresa
from django.core.exceptions import PermissionDenied
from .models import MovimientoInventario
import logging
from django_filters.rest_framework import DjangoFilterBackend
from .filters import InventarioFilter
from django.utils.translation import gettext_lazy as _ # Para mensajes de error
from django.http import HttpResponse
import openpyxl
from io import BytesIO

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
    # Mantenemos los permisos anteriores para ver/gestionar en general
    # permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsJefeInventario)]
    # Ajusta los permisos generales si es necesario

    filter_backends = [DjangoFilterBackend] # Usa el backend de django-filter
    filterset_class = InventarioFilter      # Especifica tu clase FilterSet
    

    def get_queryset(self):
        user = self.request.user
        # El queryset base ahora se optimiza con select_related
        # El filtrado por producto, ubicacion, empresa lo hará DjangoFilterBackend ANTES
        queryset = Inventario.objects.select_related('producto', 'ubicacion', 'empresa')

        # La lógica aquí solo se enfoca en la VISIBILIDAD según el rol,
        # asumiendo que los filtros de producto/ubicacion/empresa ya fueron aplicados por el backend.
        if user.is_staff or (user.rol and user.rol.nombre in ['jefe_empresa', 'jefe_inventario', 'admin']):
            # Jefes/Admin pueden ver todo (lo que pasó los filtros)
            # YA NO necesitamos filtrar por 'empresa_id' manualmente aquí
            # if self.request.query_params.get('empresa_id'): ... # BORRAR ESTA LÓGICA MANUAL
            return queryset
        elif user.rol and user.rol.nombre == 'cliente' and user.empresa:
            # Clientes solo ven su inventario (además de otros filtros aplicados)
            # Este filtro adicional por la empresa del cliente SÍ es necesario aquí
            return queryset.filter(empresa=user.empresa)
        else:
             # Si no es ninguno de los anteriores, no debería ver nada
            return Inventario.objects.none()

    def get_permissions(self):
        # Define permisos por acción
        permission_classes = [IsAuthenticated] # Base: estar autenticado

        if self.action in ['list', 'retrieve']:
            # Quién puede VER lista/detalle (clientes ven suyo, jefes ven todo filtrado)
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsJefeInventario | IsCliente))
        elif self.action in ['entrada', 'salida']:
            # Quién puede registrar entradas/salidas manuales
            permission_classes.append((IsAdminUser | IsJefeEmpresa | IsJefeInventario))
        else:
            # Restringe otras acciones (create, update, destroy directos) si quieres
            permission_classes.append((IsAdminUser | IsJefeEmpresa)) # Solo roles altos
            # O deshabilítalas sobrescribiendo los métodos (ver abajo)

        return [permission() for permission in permission_classes]

    # --- ACCIÓN PERSONALIZADA PARA ENTRADAS ---
    @action(detail=False, methods=['post'], url_path='entrada')
    @transaction.atomic # Asegura que la operación sea atómica
    def entrada(self, request):
        serializer = EntradaInventarioSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            producto = data['producto_id'] # El serializer devuelve el objeto
            ubicacion = data['ubicacion_id']
            empresa = data['empresa_id']
            cantidad_entrada = data['cantidad']
            motivo = data.get('motivo', 'Entrada manual registrada vía API.')
            usuario_actual = request.user

            # Usamos select_for_update para bloquear la fila si existe
            inventario, created = Inventario.objects.select_for_update().get_or_create(
                producto=producto,
                ubicacion=ubicacion,
                empresa=empresa,
                defaults={'cantidad': 0} # Valor inicial si se crea
            )

            cantidad_anterior = inventario.cantidad
            inventario.cantidad += cantidad_entrada
            inventario.save() # Guarda el inventario actualizado/creado

            # Registrar movimiento
            MovimientoInventario.objects.create(
                # inventario=inventario, # Puedes asociarlo si quieres
                producto=producto,
                ubicacion=ubicacion,
                empresa=empresa,
                tipo_movimiento='AJUSTE_POS', # O 'ENTRADA_MANUAL' si creas ese tipo
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=inventario.cantidad,
                cantidad_cambio=cantidad_entrada,
                usuario=usuario_actual if usuario_actual.is_authenticated else None,
                motivo=motivo
            )

            # Devuelve el estado actualizado del inventario
            inventario_serializer = InventarioSerializer(inventario)
            return Response(inventario_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        # 1. Aplicar los mismos filtros que la lista
        #    filter_queryset() usa filter_backends y filterset_class configurados
        #    para filtrar basado en request.query_params (?producto=X&empresa=Y...)
        queryset = self.filter_queryset(self.get_queryset())

        # 2. Crear un libro de Excel en memoria
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Inventario Filtrado'

        # 3. Escribir encabezados
        headers = ['ID', 'Producto', 'SKU', 'Ubicación', 'Cantidad', 'Empresa Cliente', 'Fecha Creación', 'Última Actualización']
        sheet.append(headers)

        # 4. Escribir datos del queryset filtrado
        for item in queryset:
            # Accede a los campos relacionados de forma segura
            sku = item.producto.sku if item.producto else ''
            ubicacion_nombre = item.ubicacion.nombre if item.ubicacion else ''
            empresa_nombre = item.empresa.nombre if item.empresa else ''
            # Formatea fechas si quieres (opcional)
            fecha_creacion_str = item.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if item.fecha_creacion else ''
            fecha_actualizacion_str = item.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S') if item.fecha_actualizacion else ''

            sheet.append([
                item.id,
                item.producto.nombre if item.producto else '',
                sku,
                ubicacion_nombre,
                item.cantidad,
                empresa_nombre,
                fecha_creacion_str,
                fecha_actualizacion_str
            ])

        # 5. Guardar el libro en un stream de bytes en memoria
        excel_file = BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0) # Rebobina el stream al principio

        # 6. Crear la respuesta HTTP
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="inventario_filtrado.xlsx"' # Sugiere nombre de archivo

        return response
    # --- FIN NUEVA ACCIÓN ---

    # --- ACCIÓN PERSONALIZADA PARA SALIDAS ---
    @action(detail=False, methods=['post'], url_path='salida')
    @transaction.atomic # Asegura que la operación sea atómica
    def salida(self, request):
        serializer = SalidaInventarioSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            producto = data['producto_id']
            ubicacion = data['ubicacion_id']
            empresa = data['empresa_id']
            cantidad_salida = data['cantidad']
            motivo = data.get('motivo', 'Salida manual registrada vía API.')
            usuario_actual = request.user

            try:
                # Usamos select_for_update para bloquear la fila
                inventario = Inventario.objects.select_for_update().get(
                    producto=producto,
                    ubicacion=ubicacion,
                    empresa=empresa
                )
            except Inventario.DoesNotExist:
                return Response(
                    {"detail": _("No existe inventario para este producto/ubicación/empresa.")},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validar stock
            if inventario.cantidad < cantidad_salida:
                return Response(
                    {"detail": _(f"Stock insuficiente. Disponible: {inventario.cantidad}, Solicitado: {cantidad_salida}")},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cantidad_anterior = inventario.cantidad
            cantidad_nueva = inventario.cantidad - cantidad_salida

            # Registrar movimiento ANTES de borrar (por si acaso)
            MovimientoInventario.objects.create(
                # inventario=inventario, # Asocia si quieres
                producto=producto,
                ubicacion=ubicacion,
                empresa=empresa,
                tipo_movimiento='AJUSTE_NEG', # O 'SALIDA_MANUAL'
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=cantidad_nueva,
                cantidad_cambio=-cantidad_salida, # Negativo
                usuario=usuario_actual if usuario_actual.is_authenticated else None,
                motivo=motivo
            )

            # Actualizar o borrar inventario
            if cantidad_nueva == 0:
                inventario.delete()
                return Response(
                    {"detail": _("Salida registrada. Stock en cero, registro eliminado.")},
                    status=status.HTTP_200_OK # O 204 No Content si prefieres
                )
            else:
                inventario.cantidad = cantidad_nueva
                inventario.save()
                inventario_serializer = InventarioSerializer(inventario)
                return Response(inventario_serializer.data, status=status.HTTP_200_OK)

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



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