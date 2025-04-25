# backend/proyecto/apps/transporte/views.py

from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser # Para manejar subida de archivos
from django.shortcuts import get_object_or_404 
from .models import PedidoTransporte, PruebaEntrega, ConfirmacionCliente
from .serializers import PedidoTransporteSerializer, PruebaEntregaSerializer
from apps.usuarios.permissions import IsConductor
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db import transaction
import logging
from django.conf import settings
from rest_framework.views import APIView
# Asegúrate que IsCliente y otros permisos necesarios estén importados
from apps.usuarios.permissions import IsCliente, IsConductor, IsJefeEmpresa

# Importa el modelo y el serializer principal
from .models import PedidoTransporte    
from .serializers import PedidoTransporteSerializer, ConfirmacionClienteSerializer

logger = logging.getLogger(__name__)

# Vista para formulario de confirmación de cliente

class ConfirmacionClienteView(APIView):
    """
    Vista pública para que el cliente envíe los datos de confirmación
    a través del enlace único (token).
    Maneja la petición POST.
    """
    permission_classes = [AllowAny] # ¡Importante! Es una vista pública

    @transaction.atomic # Envuelve la operación en una transacción de BD
    def post(self, request, token, format=None):
        # 1. Buscar la instancia de ConfirmacionCliente por token
        confirmacion = get_object_or_404(ConfirmacionCliente, token=token)
        pedido = confirmacion.pedido # Obtener el pedido asociado

        # 2. Verificar si ya fue confirmada previamente
        if confirmacion.fecha_confirmacion:
            return Response(
                {"detail": "Este pedido ya fue confirmado previamente."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validar y actualizar la instancia de ConfirmacionCliente con los datos del POST
        # Usamos la instancia encontrada y los datos del request
        serializer = ConfirmacionClienteSerializer(confirmacion, data=request.data, partial=True) # partial=True por si no vienen todos los campos opcionales

        if serializer.is_valid(raise_exception=True):
            # Guardar los datos en la instancia de ConfirmacionCliente
            # El método update del serializer se encarga de guardar los campos
            confirmacion_actualizada = serializer.save()

            # 4. Establecer la fecha de confirmación
            confirmacion_actualizada.fecha_confirmacion = timezone.now()
            confirmacion_actualizada.save(update_fields=['fecha_confirmacion'])

            # 5. Actualizar el flag en el PedidoTransporte asociado
            if pedido: # Asegurarse que el pedido existe
                pedido.confirmacion_cliente_realizada = True
                # ¿Debería cambiar el estado del pedido aquí? Podría ser...
                # Por ejemplo, a un estado 'listo_para_finalizar_conductor'
                # O simplemente dejamos que el flag habilite el botón 'Finalizar'
                pedido.save(update_fields=['confirmacion_cliente_realizada'])
                print(f"Pedido {pedido.id}: Confirmación de cliente marcada como True.")
            else:
                # Esto no debería pasar si la confirmación tiene pedido, pero por si acaso
                print(f"ADVERTENCIA: No se encontró pedido asociado para ConfirmacionCliente ID {confirmacion_actualizada.id}")


            # 6. Devolver respuesta de éxito
            # Podríamos devolver los datos guardados o solo un mensaje
            return Response({"detail": "Confirmación recibida con éxito."}, status=status.HTTP_200_OK)


# ---Vista para Datos del QR ---
class GenerarQRDataView(APIView):
    """
    Vista para que el conductor obtenga la URL de confirmación
    del cliente para un pedido específico.
    Devuelve la URL que se codificará en el QR.
    """
    permission_classes = [IsAuthenticated, IsConductor]

    def get(self, request, pedido_pk, format=None):
        # 1. Obtener el pedido
        pedido = get_object_or_404(PedidoTransporte, pk=pedido_pk)

        # 2. Verificar permisos: conductor asignado y estado/requisitos correctos
        if pedido.conductor != request.user:
            raise PermissionDenied("No eres el conductor asignado a este pedido.")

        # Verificar si el pedido está en el estado correcto y listo para confirmación
        # (Fotos de fin deben estar completas si son requeridas)
        if not (pedido.estado == 'en_curso' and
                pedido.requiere_confirmacion_cliente and
                (not pedido.requiere_fotos_fin or pedido.fotos_fin_completas)):
             return Response(
                 {"detail": "El pedido no está listo para la confirmación del cliente (verifica estado y fotos de finalización)."},
                 status=status.HTTP_400_BAD_REQUEST
             )

        # 3. Obtener o crear el registro de ConfirmacionCliente y su token
        # get_or_create devuelve una tupla: (objeto, created_boolean)
        confirmacion, created = ConfirmacionCliente.objects.get_or_create(pedido=pedido)
        token = confirmacion.token

        # 4. Construir la URL completa del frontend
        # Necesitas definir FRONTEND_BASE_URL en tus settings.py
        # Ej: FRONTEND_BASE_URL = 'http://localhost:3000' # O tu dominio de producción
        frontend_base_url = getattr(settings, 'FRONTEND_BASE_URL', None)
        if not frontend_base_url:
            # Es importante tenerla configurada
             print("ADVERTENCIA: FRONTEND_BASE_URL no está definida en settings.py. Usando ruta relativa.")
             # Alternativa: devolver solo la ruta relativa si el frontend añade el host
             confirmation_url = f"/confirmar/{token}/"
             # O lanzar un error si la URL completa es estrictamente necesaria
             # return Response({"detail": "Configuración del servidor incompleta."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
             # Construye la URL que abrirá la página de confirmación en el frontend
             # Asegúrate que la ruta '/confirmar/:token/' exista en tu router de React
             confirmation_url = f"{frontend_base_url.rstrip('/')}/confirmar/{token}/"


        print(f"Generando URL de confirmación para Pedido {pedido.id}: {confirmation_url}")

        # 5. Devolver la URL en la respuesta
        return Response({'confirmation_url': confirmation_url})


class PruebaEntregaUploadView(generics.CreateAPIView):
    serializer_class = PruebaEntregaSerializer
    permission_classes = [IsAuthenticated, IsConductor]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        pedido_id = self.kwargs.get('pedido_pk')
        pedido = get_object_or_404(PedidoTransporte, pk=pedido_id)

        if pedido.conductor != self.request.user:
            raise PermissionDenied("No tienes permiso para subir pruebas para este pedido.")

        # --- Validar Estado vs Tipo de Foto ---
        tipo_foto = serializer.validated_data.get('tipo_foto')
        etapa_actual_pedido = pedido.estado # pendiente, en_curso

        # Determinar etapa esperada para este tipo de foto
        etapa_esperada = None
        if tipo_foto.startswith('INICIO'): etapa_esperada = 'pendiente'
        elif tipo_foto.startswith('FIN'): etapa_esperada = 'en_curso'

        if not etapa_esperada:
            raise ValidationError("Tipo de foto no reconocido o inválido.")
        if etapa_actual_pedido != etapa_esperada:
             raise ValidationError(f"No se puede subir foto de tipo '{tipo_foto}' si el pedido está en estado '{etapa_actual_pedido}'. Se esperaba '{etapa_esperada}'.")
        # --- Fin Validación Estado ---


        # Guardar la prueba (el modelo save() calculará la etapa)
        instancia_prueba = serializer.save(pedido=pedido, subido_por=self.request.user)
        print(f"Prueba de entrega guardada: ID {instancia_prueba.id} para Pedido {pedido.id}, Tipo Foto {tipo_foto}")

        # --- Actualizar estado de flags en el Pedido ---
        try:
            updated_fields = []
            # Lógica para fotos de INICIO (generalmente solo se requiere una)
            if instancia_prueba.etapa == 'INICIO' and pedido.requiere_fotos_inicio and not pedido.fotos_inicio_completas:
                 # Asumimos que una foto de INICIO_GEN es suficiente
                 if tipo_foto == 'INICIO_GEN':
                    pedido.fotos_inicio_completas = True
                    updated_fields.append('fotos_inicio_completas')
                    print(f"Marcando fotos_inicio_completas=True para Pedido {pedido.id}")

            # Lógica para fotos de FIN (requiere tipos específicos)
            elif instancia_prueba.etapa == 'FIN' and pedido.requiere_fotos_fin and not pedido.fotos_fin_completas:
                 # Definir qué tipos de foto son OBLIGATORIOS para marcar como completas las de FIN
                 # Esto podría depender del tipo de servicio del pedido
                 tipos_requeridos_fin = ['FIN_MERC', 'FIN_REC'] # Ejemplo para mercancía
                 # Para otros tipos de servicio podrías requerir solo 'FIN_GEN', etc.
                 # if pedido.tipo_servicio == 'PASAJEROS': tipos_requeridos_fin = ['FIN_GEN']

                 # Contar las fotos existentes para CADA tipo requerido para ESTE pedido
                 fotos_fin_existentes = PruebaEntrega.objects.filter(
                     pedido=pedido,
                     etapa='FIN', # Filtrar por etapa sigue siendo útil
                     tipo_foto__in=tipos_requeridos_fin # Solo contar las relevantes
                 ).values_list('tipo_foto', flat=True) # Obtener lista de tipos existentes

                 # Verificar si todos los tipos requeridos están presentes
                 todos_presentes = all(tipo_req in fotos_fin_existentes for tipo_req in tipos_requeridos_fin)

                 if todos_presentes:
                     pedido.fotos_fin_completas = True
                     updated_fields.append('fotos_fin_completas')
                     print(f"Marcando fotos_fin_completas=True para Pedido {pedido.id} (Tipos requeridos {tipos_requeridos_fin} presentes)")
                 else:
                      print(f"Pedido {pedido.id}: Aún faltan tipos de fotos de FIN. Existentes: {list(fotos_fin_existentes)}, Requeridos: {tipos_requeridos_fin}")


            if updated_fields:
                pedido.save(update_fields=updated_fields)
                print(f"Pedido {pedido.id} actualizado, campos: {updated_fields}")

        except Exception as e:
            print(f"ERROR al actualizar flags del pedido {pedido.id} tras subir prueba: {e}")


    def get_serializer_context(self):
        # Pasamos el request al contexto para que el serializer pueda construir URLs absolutas
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# --- VISTA SIMPLE PARA CREAR PEDIDO (AHORA FUNCIONAL) --- Recuaerda modificar la PedidoTransporteCreateView por que es redundante y ajusat el codigo
class ClientePedidoSimpleCreateView(APIView):
    """
    Endpoint SIMPLE para que un cliente CREE un pedido.
    VALIDA usando PedidoTransporteSerializer y GUARDA en la BD.
    URL: (Depende de tu urls.py, ej: /api/transporte/pedidos/nuevo/)
    """
    permission_classes = [IsAuthenticated, IsCliente] # Solo clientes autenticados
    serializer_class = PedidoTransporteSerializer     # Usa el serializer principal

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        logger.info(f"ClientePedidoSimpleCreateView: Intento POST por User ID {user.id} con data: {data}")
        print(f"\n--- ClientePedidoSimpleCreateView POST ---")
        print(f"--- User: {user}, Rol: {getattr(user.rol, 'nombre', 'N/A')} ---")
        print(f"--- Data Recibida: {data} ---")

        serializer = None
        try:
            # 1. Instanciar Serializer con datos recibidos y contexto
            # El contexto es útil si el serializer necesita acceder al request (ej: para el usuario)
            print("--- Instanciando Serializer... ---")
            serializer = self.serializer_class(data=data, context={'request': request})

            # 2. Validar (ejecuta el método validate del serializer)
            print("--- Validando Serializer... ---")
            serializer.is_valid(raise_exception=True)
            print("--- Validación Exitosa ---")

            # 3. Guardar en Base de Datos
            # Pasamos el cliente explícitamente al método save.
            # El método 'create' del serializer se encargará del resto.
            print("--- Guardando Pedido... ---")
            instancia_guardada = serializer.save(cliente=user) # Asigna el cliente logueado
            print(f"--- Pedido Guardado Exitosamente! ID: {instancia_guardada.id} ---")
            logger.info(f"Pedido {instancia_guardada.id} (Tipo: {instancia_guardada.tipo_servicio}) creado vía ClientePedidoSimpleCreateView por cliente: {user.cedula}")

            # 4. Devolver Respuesta Exitosa (201 Created) con los datos del pedido creado
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.warning(f"Validation failed for user {user.id} creating pedido: {e.detail}")
            print(f"--- ERROR DE VALIDACIÓN (400 Bad Request): {e.detail} ---")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
             # Aunque los permission_classes deberían manejar esto, por si acaso
             logger.warning(f"Permission denied during POST for user {user.id}: {e}")
             print(f"--- ERROR DE PERMISO (403 Forbidden): {e} ---")
             return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
             # Captura cualquier otro error inesperado
             logger.error(f"Unexpected error during POST for user {user.id}: {e}", exc_info=True)
             print(f"--- ERROR INESPERADO: {e} ---")
             # Devuelve un error genérico al cliente
             return Response({"detail": "Error inesperado al procesar el pedido."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- VISTA DE PRUEBA (YA FUNCIONABA, SIN CAMBIOS NECESARIOS) ---
# Si esta era tu endpoint principal, también funcionará con los nuevos tipos.
class SimplePedidoTestView(APIView):
    """
    Endpoint de prueba incremental que VALIDA y GUARDA pedidos de cliente.
    URL: /api/transporte/simple-test/ (Si todavía existe y la usas)
    """
    permission_classes = [IsAuthenticated, IsCliente]
    serializer_class = PedidoTransporteSerializer

    def post(self, request, *args, **kwargs):
        # (Misma lógica que ClientePedidoSimpleCreateView arriba)
        user = request.user
        data = request.data
        print(f"\n--- SimplePedidoTestView POST ---")
        print(f"--- Data Recibida: {data} ---")
        serializer = None
        try:
            print("--- Instanciando Serializer... ---")
            serializer = self.serializer_class(data=data, context={'request': request})
            print("--- Validando Serializer... ---")
            serializer.is_valid(raise_exception=True)
            print("--- Validación Exitosa ---")
            print("--- Guardando Pedido... ---")
            instancia_guardada = serializer.save(cliente=request.user)
            print(f"--- Pedido Guardado Exitosamente! ID: {instancia_guardada.id} ---")
            logger.info(f"Pedido {instancia_guardada.id} creado vía SimplePedidoTestView por cliente: {user.cedula}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.warning(f"SimplePedidoTestView Validation failed: {e.detail}")
            print(f"--- ERROR DE VALIDACIÓN (400 Bad Request): {e.detail} ---")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             logger.error(f"SimplePedidoTestView Unexpected error: {e}", exc_info=True)
             print(f"--- ERROR INESPERADO: {e} ---")
             return Response({"detail": "Error inesperado procesando el pedido."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- VISTA GENÉRICA CreateAPIView (Alternativa, si prefieres usarla) ---
# Esta vista es más estándar de DRF para creación. Funciona igual que las anteriores.
class PedidoTransporteCreateView(generics.CreateAPIView):
    """
    Endpoint estándar de DRF para que CLIENTES creen pedidos.
    Usa el serializer principal para validar y asigna el cliente automáticamente.
    URL: (Depende de tu urls.py, ej: /api/transporte/pedidos/crear/)
    """
    serializer_class = PedidoTransporteSerializer
    permission_classes = [IsAuthenticated, IsCliente] # Solo clientes autenticados

    def perform_create(self, serializer):
        """Sobrescribe para asignar el cliente logueado automáticamente."""
        try:
            # El serializer ya fue validado antes de llamar a perform_create
            serializer.save(cliente=self.request.user)
            logger.info(f"Pedido creado vía PedidoTransporteCreateView por cliente: {self.request.user.cedula}")
        except Exception as e:
            # Captura errores específicos del guardado si es necesario
            logger.error(f"Error en perform_create para cliente {getattr(self.request.user, 'cedula', 'N/A')}: {e}", exc_info=True)
            # Re-lanza la excepción para que DRF maneje la respuesta de error
            raise e

# --- VISTAS PARA CONDUCTOR (SIN CAMBIOS) ---
# Estas vistas filtran o muestran datos, no dependen directamente de la lógica
# específica de cada tipo de servicio más allá de lo que el serializer expone.

class PedidosConductorList(generics.ListAPIView):
    """Devuelve pedidos ACTIVOS asignados al conductor."""
    serializer_class = PedidoTransporteSerializer
    permission_classes = [IsAuthenticated, IsConductor]

    def get_queryset(self):
        user = self.request.user
        queryset = PedidoTransporte.objects.filter(
            conductor=user
        ).exclude(
            estado__in=['finalizado', 'cancelado']
        ).select_related('cliente').order_by('-fecha_creacion') # select_related añadido
        logger.debug(f"Queryset count for active orders conductor {user.id}: {queryset.count()}")
        return queryset

class HistorialMesConductorList(generics.ListAPIView):
    """Devuelve pedidos FINALIZADOS del conductor para un mes/año."""
    serializer_class = PedidoTransporteSerializer
    permission_classes = [IsAuthenticated, IsConductor]

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        try:
            selected_year = int(self.request.query_params.get('year', now.year))
            selected_month = int(self.request.query_params.get('month', now.month))
            if not 1 <= selected_month <= 12: selected_month = now.month
        except (TypeError, ValueError):
            selected_year = now.year
            selected_month = now.month
        logger.debug(f"Fetching history for conductor {user.id}, year={selected_year}, month={selected_month}")
        queryset = PedidoTransporte.objects.filter(
            conductor=user, estado='finalizado',
            fecha_fin__year=selected_year, fecha_fin__month=selected_month
        ).select_related(
            'cliente', 'conductor'
        ).prefetch_related(
            # --- CORRECCIÓN AQUÍ ---
            'pruebas_entrega', # Correcto
            # --- FIN CORRECCIÓN ---
            'confirmacion_cliente'
        ).order_by('-fecha_fin')
        return queryset


# --- VIEWSET PARA GESTIÓN COMPLETA (SIN CAMBIOS NECESARIOS EN LA LÓGICA CENTRAL) ---
# El serializer maneja la validación específica del tipo.
# Los permisos por acción parecen seguir siendo válidos.
# La lógica de partial_update para iniciar/finalizar es genérica.
class PedidoTransporteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD completo de Pedidos (Admin/Jefe).
    Conductores pueden usar PATCH para iniciar/finalizar.
    """
    serializer_class = PedidoTransporteSerializer
    queryset = PedidoTransporte.objects.all().select_related('cliente', 'conductor', 'cliente__empresa')

    def get_permissions(self):
        """Define permisos por acción (sin cambios respecto a la versión anterior)."""
        permission_classes = [IsAuthenticated] # Base
        user = self.request.user # Obtener usuario para chequeos más finos si es necesario

        if self.action == 'list':
            # Quién puede ver la lista general de pedidos activos?
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        elif self.action == 'retrieve':
            # Quién puede ver el detalle de UN pedido?
            # Permitimos Admin, Jefe, y Conductor o Cliente SI ES SU PEDIDO (requiere has_object_permission)
            # Por ahora, mantenemos la lógica anterior que permite a todos los roles autenticados ver detalles
            # (la lógica de negocio debe asegurar que solo vean lo relevante)
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsConductor | IsCliente)]
        elif self.action == 'create':
            # Quién puede crear pedidos DESDE EL VIEWSET? (Clientes usan su propia vista)
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        elif self.action in ['update', 'partial_update']:
            # Quién puede modificar? Admin, Jefe, o Conductor (solo para iniciar/finalizar)
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa | IsConductor)]
        elif self.action == 'destroy':
            # Quién puede eliminar?
            permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
        else:
            # Permiso por defecto para acciones no estándar
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filtra queryset para 'list' (sin cambios)."""
        user = self.request.user
        base_queryset = super().get_queryset()
        if self.action == 'list' and (user.is_staff or (user.rol and user.rol.nombre == 'jefe_empresa')):
             # Solo Admin/Jefe ven la lista de activos
             return base_queryset.exclude(
                 estado__in=['finalizado', 'cancelado']
             ).order_by('-fecha_creacion')
        # Para otras acciones (retrieve, etc.), se usa el queryset base.
        # Si un cliente o conductor intenta listar aquí, get_permissions lo bloquea.
        # Si necesitan listar *sus* pedidos, usan las vistas específicas (PedidosConductorList, etc.)
        return base_queryset

    def partial_update(self, request, *args, **kwargs):
        """Maneja PATCH, incluyendo iniciar/finalizar por conductor (sin cambios)."""
        pedido = self.get_object() # DRF maneja 404 si no existe
        user = request.user
        logger.info(f"Partial update attempt on Pedido ID {pedido.id} (Type: {pedido.tipo_servicio}) by User {user.id} ({getattr(user.rol, 'nombre', 'N/A')}) with data: {request.data}")

        # Lógica Específica para Conductores
        if user.rol and user.rol.nombre == 'conductor':
            if pedido.conductor != user:
                logger.warning(f"Conductor {user.id} denied PATCH on Pedido {pedido.id} (not assigned)")
                # Usar PermissionDenied para respuesta 403 estándar
                raise PermissionDenied('No tienes permiso para modificar este pedido.')

            iniciar = request.data.get('iniciar') == 'confirmado'
            finalizar = request.data.get('finalizar') == 'confirmado'

            if iniciar:
                if pedido.estado == 'pendiente':
                    pedido.estado = 'en_curso'
                    pedido.fecha_inicio = timezone.now()
                    pedido.save(update_fields=['estado', 'fecha_inicio'])
                    logger.info(f"Pedido {pedido.id} iniciado por conductor {user.id}")
                    serializer = self.get_serializer(pedido)
                    return Response(serializer.data) # Status 200 OK por defecto
                else:
                    logger.warning(f"Conductor {user.id} intento iniciar pedido {pedido.id} no pendiente (estado: {pedido.estado})")
                    # Devolver error claro al cliente
                    return Response({'detail': f'El pedido no está pendiente (estado actual: {pedido.estado}).'}, status=status.HTTP_400_BAD_REQUEST)
            elif finalizar:
                if pedido.estado == 'en_curso':
                    pedido.estado = 'finalizado'
                    pedido.fecha_fin = timezone.now()
                    pedido.save(update_fields=['estado', 'fecha_fin'])
                    logger.info(f"Pedido {pedido.id} finalizado por conductor {user.id}")
                    serializer = self.get_serializer(pedido)
                    return Response(serializer.data)
                else:
                    logger.warning(f"Conductor {user.id} intento finalizar pedido {pedido.id} no en curso (estado: {pedido.estado})")
                    return Response({'detail': f'El pedido no está en curso (estado actual: {pedido.estado}).'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                 # Si conductor envía otros campos o acción no reconocida
                 logger.warning(f"Conductor {user.id} intento de PATCH no válido en pedido {pedido.id}: {request.data}")
                 return Response({'detail': 'Acción no permitida o datos incorrectos para conductores.'}, status=status.HTTP_400_BAD_REQUEST)

        # Si NO es conductor (Admin/Jefe)
        else:
            # Deja que el método padre maneje la actualización estándar (PUT/PATCH)
            # El serializer se encargará de validar los datos enviados.
            logger.info(f"Admin/Jefe {user.id} procediendo con partial_update estándar para pedido {pedido.id}.")
            # La llamada a super() aplicará las validaciones del serializer
            try:
                return super().partial_update(request, *args, **kwargs)
            except Exception as e:
                 # Capturar errores inesperados durante la actualización estándar
                 logger.error(f"Error en super().partial_update para pedido {pedido.id} por usuario {user.id}: {e}", exc_info=True)
                 return Response({"detail": "Ocurrió un error al actualizar el pedido."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # perform_create/update/destroy solo añaden logging (sin cambios)
    def perform_create(self, serializer):
        logger.info(f"Pedido creado vía ViewSet por usuario {self.request.user}")
        # El cliente se asigna desde el serializer si viene cliente_id,
        # o podría asignarse aquí si la lógica fuera diferente.
        serializer.save()

    def perform_update(self, serializer):
        logger.info(f"Pedido {serializer.instance.id} actualizado vía ViewSet por usuario {self.request.user}")
        serializer.save()

    def perform_destroy(self, instance):
        logger.warning(f"Pedido {instance.id} eliminado vía ViewSet por usuario {self.request.user}")
        instance.delete()


# --- VISTA HISTORIAL GENERAL (SIN CAMBIOS) ---
class HistorialMesGeneralList(generics.ListAPIView):
    """Devuelve TODOS los pedidos finalizados del mes/año (Admin/Jefe)."""
    serializer_class = PedidoTransporteSerializer
    permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]
    def get_queryset(self):
        now = timezone.now()
        try:
            selected_year = int(self.request.query_params.get('year', now.year))
            selected_month = int(self.request.query_params.get('month', now.month))
            if not 1 <= selected_month <= 12: selected_month = now.month
        except (TypeError, ValueError):
            selected_year = now.year
            selected_month = now.month
        logger.debug(f"Fetching general history for year={selected_year}, month={selected_month}")
        queryset = PedidoTransporte.objects.filter(
            estado='finalizado',
            fecha_fin__year=selected_year,
            fecha_fin__month=selected_month
        ).select_related(
            'cliente', 'conductor', 'cliente__empresa'
        ).prefetch_related(
             # --- CORRECCIÓN AQUÍ ---
            'pruebas_entrega', # Correcto
             # --- FIN CORRECCIÓN ---
            'confirmacion_cliente', 'items_pedido', 'items_pedido__producto'
        ).order_by('-fecha_fin')
        return queryset
    
    # --- NUEVA VISTA PARA HISTORIAL CLIENTE ---
class HistorialMesClienteList(generics.ListAPIView):
    """
    Devuelve pedidos FINALIZADOS o CANCELADOS del cliente autenticado
    para un mes/año específico.
    """
    serializer_class = PedidoTransporteSerializer # Reutiliza el serializer detallado
    permission_classes = [IsAuthenticated, IsCliente] # Solo clientes autenticados

    def get_queryset(self):
        user = self.request.user
        now = timezone.now() # Para obtener fecha actual como default

        # Obtener año y mes de query params, con defaults
        try:
            selected_year = int(self.request.query_params.get('year', now.year))
            selected_month = int(self.request.query_params.get('month', now.month))
            # Validación básica del mes
            if not 1 <= selected_month <= 12:
                selected_month = now.month
        except (TypeError, ValueError):
            selected_year = now.year
            selected_month = now.month

        logger.debug(f"Fetching history for CLIENTE {user.id}, year={selected_year}, month={selected_month}")

        # Filtrar pedidos por cliente, estado y fecha de finalización
        queryset = PedidoTransporte.objects.filter(
            cliente=user, # <-- Filtro clave: solo pedidos de este cliente
            estado__in=['finalizado', 'cancelado'], # Incluye finalizados y cancelados
            fecha_fin__year=selected_year,
            fecha_fin__month=selected_month
        ).select_related( # Optimiza FKs
            'conductor' # Cliente ya es user, no necesita select_related
        ).prefetch_related( # Optimiza ManyToMany y Reverse FKs
            'pruebas_entrega',
            'confirmacion_cliente',
            'items_pedido', # Para tipo BODEGAJE_SALIDA
            'items_pedido__producto' # Incluye info del producto en los items
        ).order_by('-fecha_fin') # Ordenar por fecha de finalización descendente

        return queryset