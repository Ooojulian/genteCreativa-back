# backend/proyecto/apps/transporte/serializers.py
from rest_framework import serializers, viewsets
from .models import PedidoTransporte, ItemPedido, PruebaEntrega, ConfirmacionCliente, Vehiculo, TipoVehiculo # Modelos de esta app
#from .serializers import VehiculoSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from apps.usuarios.permissions import IsJefeEmpresa, IsJefeInventario
from apps.usuarios.models import Usuario # Modelo de otra app
from apps.bodegaje.models import Producto, Inventario # Modelos de otra app
from django.utils.translation import gettext_lazy as _ # Para mensajes de error
from django.core.exceptions import ObjectDoesNotExist # Para manejo de errores

class VehiculoSerializer(serializers.ModelSerializer):
    # Campo de Lectura: Muestra el objeto TipoVehiculo anidado o solo su nombre
    # Opción 1: Mostrar objeto completo (más datos, pero más pesado)
    # tipo = TipoVehiculoSerializer(read_only=True)
    # Opción 2: Mostrar solo el nombre del tipo (más ligero)
    tipo = serializers.StringRelatedField(read_only=True)

    # Campo de Escritura: Recibe el ID del TipoVehiculo
    tipo_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoVehiculo.objects.all(), # Opciones posibles
        source='tipo',              # Apunta al campo 'tipo' del modelo Vehiculo
        write_only=True,
        label="Tipo de Vehículo (ID)" # Etiqueta para la API explorable
    )

    class Meta:
        model = Vehiculo
        # --- ACTUALIZAR fields ---
        fields = [
            'id',
            'placa',
            'tipo',          # Para lectura (mostrará el nombre o el objeto según opción arriba)
            'tipo_id',       # Para escritura (recibe el ID)
            'marca',
            'modelo',
            'year',
            'activo',
        ]
        # Ya no necesitamos 'tipo_display' porque 'tipo' ahora da el nombre o el objeto.
        # read_only_fields = ['id', 'tipo'] # Hacemos 'tipo' read_only para lectura


class TipoVehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVehiculo
        fields = ['id', 'nombre', 'descripcion'] # Incluye los campos del modelo
# --- FIN NUEVO ---


class VehiculoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los Vehículos (CRUD).
    Accesible por Admin y Jefe de Empresa.
    """
    queryset = Vehiculo.objects.all().order_by('placa') # Obtiene todos los vehículos ordenados
    serializer_class = VehiculoSerializer
    # Define quién puede acceder a esta gestión
    permission_classes = [IsAuthenticated, (IsAdminUser | IsJefeEmpresa)]

    # Opcional: Podrías añadir filtros aquí más adelante si necesitas
    # filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    # search_fields = ['placa', 'marca', 'modelo']
    # filterset_fields = ['tipo', 'activo']

# --- FIN NUEVO VIEWSET ---

# Confirmacion de Formulario Cliente
class ConfirmacionClienteSerializer(serializers.ModelSerializer):
    # Hacemos los campos escribibles que vienen del formulario público
    # La firma viene como un string largo base64
    firma_imagen_base64 = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    # Cédula y Observaciones son opcionales
    cedula_receptor = serializers.CharField(max_length=50, allow_blank=True, allow_null=True, required=False)
    observaciones = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    # Nombre es requerido
    nombre_receptor = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = ConfirmacionCliente
        # Campos que esperamos recibir del formulario del cliente
        fields = [
            'nombre_receptor',
            'cedula_receptor',
            'firma_imagen_base64',
            'observaciones',
            # Campos que son solo de lectura en este contexto o se manejan internamente
            'pedido',
            'token',
            'fecha_confirmacion'
        ]
        # Estos campos no los debe enviar el cliente, se determinan por el contexto o se generan
        read_only_fields = ['pedido', 'token', 'fecha_confirmacion']

    def validate_nombre_receptor(self, value):
        if not value or len(value.strip()) < 3: # Validación simple de ejemplo
            raise serializers.ValidationError("El nombre del receptor es requerido.")
        return value

    # Podrías añadir una validación básica para la firma si quisieras
    # def validate_firma_imagen_base64(self, value):
    #     if value and not value.startswith('data:image/png;base64,'):
    #          raise serializers.ValidationError("Formato de firma inválido.")
    #     return value

    def update(self, instance, validated_data):
        # Sobrescribimos update para asegurarnos que solo actualizamos los campos del form
        # y ponemos la fecha de confirmación. El pedido se actualiza en la vista.
        instance.nombre_receptor = validated_data.get('nombre_receptor', instance.nombre_receptor)
        instance.cedula_receptor = validated_data.get('cedula_receptor', instance.cedula_receptor)
        instance.firma_imagen_base64 = validated_data.get('firma_imagen_base64', instance.firma_imagen_base64)
        instance.observaciones = validated_data.get('observaciones', instance.observaciones)
        # La fecha de confirmación se pondrá en la vista después de llamar a save()
        instance.save()
        return instance
    
class VehiculoSerializer(serializers.ModelSerializer):
    # Campo de Lectura: Usa el serializer anidado para devolver el objeto TipoVehiculo
    tipo = TipoVehiculoSerializer(read_only=True)

    # Campo de Escritura: Recibe el ID del TipoVehiculo al crear/actualizar
    tipo_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoVehiculo.objects.all(),
        source='tipo',              # Apunta al campo 'tipo' (FK) del modelo Vehiculo
        write_only=True,
        label="Tipo de Vehículo (ID)"
    )

    class Meta:
        model = Vehiculo
        # --- ACTUALIZAR fields ---
        fields = [
            'id',
            'placa',
            'tipo',          # Para lectura (ahora devuelve el objeto TipoVehiculo)
            'tipo_id',       # Para escritura (recibe el ID)
            'marca',
            'modelo',
            'year',
            'activo',
        ]

# --- Serializer para PruebaEntrega ---
class PruebaEntregaSerializer(serializers.ModelSerializer):
    foto = serializers.ImageField(required=True, write_only=True) # WriteOnly si no necesitas reenviar el archivo
    # --- CAMBIO: Ahora esperamos tipo_foto ---
    tipo_foto = serializers.ChoiceField(choices=PruebaEntrega.TIPO_FOTO_CHOICES, required=True)
    # --- FIN CAMBIO ---
    foto_url = serializers.SerializerMethodField(read_only=True)
    subido_por_info = serializers.StringRelatedField(source='subido_por', read_only=True)
    # Añadimos el display de tipo_foto para la respuesta
    tipo_foto_display = serializers.CharField(source='get_tipo_foto_display', read_only=True)
    # El pedido_id será útil en la respuesta
    pedido_id = serializers.PrimaryKeyRelatedField(source='pedido', read_only=True)


    class Meta:
        model = PruebaEntrega
        fields = [
            'id',
            'pedido_id', # Mostrar ID del pedido
            # 'etapa', # Ya no es necesario aquí, se deriva
            'tipo_foto', # Campo de escritura y lectura (clave)
            'tipo_foto_display', # Lectura (texto)
            'foto', # Solo escritura
            'foto_url', # Lectura
            'subido_por_info',
            'timestamp'
        ]
        # etapa ya no es un campo de entrada directo
        read_only_fields = ['id', 'pedido_id', 'timestamp', 'subido_por_info', 'tipo_foto_display', 'foto_url']

    # Método para obtener la URL completa de la imagen
    def get_foto_url(self, obj):
        request = self.context.get('request')
        if obj.foto and request:
            return request.build_absolute_uri(obj.foto.url)
        return None

    # Validación adicional si es necesaria
    def validate_etapa(self, value):
        # Puedes añadir validaciones extra aquí si quieres
        if value not in dict(PruebaEntrega.ETAPA_CHOICES):
             raise serializers.ValidationError("Etapa inválida.")
        return value

# --- Serializers ItemPedido (Sin cambios respecto a la versión anterior) ---
class ItemPedidoWriteSerializer(serializers.ModelSerializer):
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        source='producto'
    )
    class Meta:
        model = ItemPedido
        fields = ('producto_id', 'cantidad')

class ItemPedidoReadSerializer(serializers.ModelSerializer):
    producto = serializers.StringRelatedField()
    class Meta:
        model = ItemPedido
        fields = ('id', 'producto', 'cantidad')
# --- FIN Serializers ItemPedido ---


class PedidoTransporteSerializer(serializers.ModelSerializer):
    # --- Campos de Lectura ---
    cliente = serializers.StringRelatedField(read_only=True)
    conductor = serializers.StringRelatedField(read_only=True)
    # Muestra items anidados (solo relevante para BODEGAJE_SALIDA)
    items_pedido = ItemPedidoReadSerializer(many=True, read_only=True)
    # Muestra etiquetas legibles para los campos 'choices'
    tipo_servicio_display = serializers.CharField(source='get_tipo_servicio_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    # Asegúrate que el modelo tenga el método get_TIPO_CAMPO_display para estos
    tipo_vehiculo_display = serializers.CharField(source='get_tipo_vehiculo_requerido_display', read_only=True, allow_null=True)
    tipo_tarifa_pasajero_display = serializers.CharField(source='get_tipo_tarifa_pasajero_display', read_only=True, allow_null=True)

    # --- CAMPOS BOOLEANOS (DEFINIDOS AQUÍ) ---
    requiere_fotos_inicio = serializers.BooleanField(read_only=True)
    requiere_fotos_fin = serializers.BooleanField(read_only=True)
    requiere_confirmacion_cliente = serializers.BooleanField(read_only=True)
    fotos_inicio_completas = serializers.BooleanField(read_only=True)
    fotos_fin_completas = serializers.BooleanField(read_only=True)
    confirmacion_cliente_realizada = serializers.BooleanField(read_only=True)

     # --- NUEVO: Incluir Serializers Anidados Explícitamente ---
    pruebas_entrega = PruebaEntregaSerializer(many=True, read_only=True)
    confirmacion_cliente = ConfirmacionClienteSerializer(read_only=True) # Es OneToOne, no many=True
    # --- FIN NUEVO ---

    # --- Campos de Escritura ---
    # Se usan para asignar relaciones al crear/actualizar desde ViewSets (Admin/Jefe)
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol__nombre='cliente'),
        source='cliente', write_only=True, required=False, allow_null=True
    )
    conductor_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol__nombre='conductor'),
        source='conductor', required=False, allow_null=True, write_only=True
    )
    # Campo específico para recibir items al crear pedidos de BODEGAJE_SALIDA
    items_a_retirar = ItemPedidoWriteSerializer(many=True, write_only=True, required=False)


    class Meta:
        model = PedidoTransporte
        # --- Lista COMPLETA de campos ---
        fields = (
           'id',
           # Relacionados
           'cliente', 'conductor', # Strings para lectura fácil
           # Básicos
           'origen', 'destino', 'descripcion', 'estado', 'estado_display',
           # Fechas
           'fecha_creacion', 'fecha_inicio', 'fecha_fin',
           'hora_recogida_programada', 'hora_entrega_programada',
           # Tipo Servicio y Vehículo
           'tipo_servicio', 'tipo_servicio_display',
           'tipo_vehiculo_requerido', 'tipo_vehiculo_display',
           # Mercancía / Bodega
           'tiempo_bodegaje_estimado', 'dimensiones_contenido',
           'items_pedido', # Lectura items retiro
           # Pasajeros (Nuevos)
           'numero_pasajeros', 'tipo_tarifa_pasajero', 'tipo_tarifa_pasajero_display',
           'duracion_estimada_horas', 'distancia_estimada_km',
           # --- AÑADIR LOS NUEVOS CAMPOS BOOLEANOS AQUÍ ---
           'requiere_fotos_inicio',
           'requiere_fotos_fin',
           'requiere_confirmacion_cliente',
           'fotos_inicio_completas',
           'fotos_fin_completas',
           'confirmacion_cliente_realizada',
           # --- FIN CAMPOS BOOLEANOS ---
           # Campos Write-Only (necesarios para que el serializer los reconozca al validar data de entrada, aunque no salgan en GET)
           'cliente_id', 'conductor_id', 
           'items_a_retirar',
           'pruebas_entrega',
           'confirmacion_cliente',
        )
        # Read only fields se definen aquí para PREVENIR que se escriban via API,
        # pero NO afecta si se muestran o no en una respuesta GET (eso lo controla 'fields')
        read_only_fields = (
            'id', # ID usualmente es read-only
            'cliente', 'conductor', # Los campos StringRelatedField son inherentemente read-only
            'estado_display', 'fecha_creacion', 'fecha_inicio', 'fecha_fin',
            'tipo_servicio_display', 'tipo_vehiculo_display', 'items_pedido',
            'tipo_tarifa_pasajero_display',
            # Los flags booleanos también deben ser read_only aquí para que no se puedan modificar directamente por la API
            'requiere_fotos_inicio', 'requiere_fotos_fin', 'requiere_confirmacion_cliente',
            'fotos_inicio_completas', 'fotos_fin_completas', 'confirmacion_cliente_realizada',
            'pruebas_entrega', 'confirmacion_cliente',
        )

    def validate(self, data):
        """
        Valida los datos según el tipo_servicio y limpia campos no aplicables.
        """
        # Obtiene tipo_servicio (input o instancia actual si es update)
        tipo_servicio = data.get('tipo_servicio', getattr(self.instance, 'tipo_servicio', None))
        if not tipo_servicio:
             raise serializers.ValidationError(_("El tipo de servicio es obligatorio."))

        # Define qué campos pertenecen a cada lógica
        campos_mercancia = ['tiempo_bodegaje_estimado', 'dimensiones_contenido', 'items_a_retirar']
        campos_pasajeros = ['numero_pasajeros', 'tipo_tarifa_pasajero', 'duracion_estimada_horas', 'distancia_estimada_km']

        # Campos potencialmente requeridos/validados
        origen = data.get('origen', getattr(self.instance, 'origen', None))
        destino = data.get('destino', getattr(self.instance, 'destino', None))
        hora_recogida = data.get('hora_recogida_programada', getattr(self.instance, 'hora_recogida_programada', None))
        hora_entrega = data.get('hora_entrega_programada', getattr(self.instance, 'hora_entrega_programada', None))
        tiempo_bodegaje = data.get('tiempo_bodegaje_estimado', getattr(self.instance, 'tiempo_bodegaje_estimado', None))
        items_retiro = data.get('items_a_retirar') # Solo relevante en input data (creación)
        numero_pasajeros = data.get('numero_pasajeros', getattr(self.instance, 'numero_pasajeros', None))
        tipo_tarifa = data.get('tipo_tarifa_pasajero', getattr(self.instance, 'tipo_tarifa_pasajero', None))
        duracion = data.get('duracion_estimada_horas', getattr(self.instance, 'duracion_estimada_horas', None))
        distancia = data.get('distancia_estimada_km', getattr(self.instance, 'distancia_estimada_km', None))
        tipo_vehiculo = data.get('tipo_vehiculo_requerido', getattr(self.instance, 'tipo_vehiculo_requerido', None))
        cliente_id_input = data.get('cliente_id') # ID del cliente enviado en la petición (puede ser string o int)
        cliente_obj_input = data.get('cliente') # Objeto cliente resuelto por PrimaryKeyRelatedField si existe

        # Errores acumulados
        errors = {}

        # --- Validación por tipo_servicio ---
        if tipo_servicio == 'SIMPLE':
            if not origen: errors['origen'] = _("Obligatorio para Envío Simple.")
            if not destino: errors['destino'] = _("Obligatorio para Envío Simple.")
            if not hora_recogida: errors['hora_recogida_programada'] = _("Obligatoria para Envío Simple.")
            # Limpia campos no aplicables
            for campo in campos_pasajeros + ['tiempo_bodegaje_estimado', 'items_a_retirar']: data.pop(campo, None)

        elif tipo_servicio == 'BODEGAJE_ENTRADA':
            if not origen: errors['origen'] = _("Obligatorio para Entrada a Bodega.")
            if not hora_recogida: errors['hora_recogida_programada'] = _("Obligatoria para Entrada a Bodega.")
            if not tiempo_bodegaje: errors['tiempo_bodegaje_estimado'] = _("Obligatorio para Entrada a Bodega.")
            # Limpia campos no aplicables
            for campo in campos_pasajeros + ['destino', 'hora_entrega_programada', 'items_a_retirar']: data.pop(campo, None)

        elif tipo_servicio == 'BODEGAJE_SALIDA':
            if not destino: errors['destino'] = _("Destino es obligatorio para Retiro de Bodega.")
            # Validar items solo si se están creando (no en update, usualmente)
            # O si vienen explícitamente en el payload del PATCH/PUT
            if 'items_a_retirar' in data: # Chequea si la clave existe en el input
                if not items_retiro or len(items_retiro) == 0:
                    errors['items_a_retirar'] = _("Debe seleccionar al menos un producto a retirar.")
                else:
                    # --- Validación de Stock CORREGIDA ---
                    cliente_obj_target = None
                    target_empresa = None

                    # Intenta obtener el cliente del objeto resuelto o del ID de entrada
                    if isinstance(cliente_obj_input, Usuario):
                         cliente_obj_target = cliente_obj_input
                    elif cliente_id_input:
                        try:
                            # Busca el usuario basado en el ID
                            cliente_obj_target = Usuario.objects.get(pk=int(cliente_id_input))
                        except (Usuario.DoesNotExist, ValueError, TypeError):
                            errors['cliente_id'] = _("El cliente seleccionado no es válido.")
                        except Exception as e:
                            print(f"Error buscando cliente ID {cliente_id_input}: {e}")
                            errors['cliente_id'] = _("Error interno buscando cliente.")
                    else:
                         # Si es una actualización (self.instance existe) y no se cambió el cliente
                         if self.instance and self.instance.cliente:
                             cliente_obj_target = self.instance.cliente
                         else:
                             # No hay cliente en el input ni en la instancia (no debería pasar si cliente es obligatorio)
                             errors['cliente_id'] = _("No se pudo determinar el cliente para validar stock.")

                    # Si encontramos un cliente, validamos su empresa
                    if cliente_obj_target and 'cliente_id' not in errors:
                        if not hasattr(cliente_obj_target, 'empresa') or not cliente_obj_target.empresa:
                            errors['cliente_id'] = _(f"El cliente ({cliente_obj_target.cedula}) no tiene empresa asociada.")
                        else:
                            target_empresa = cliente_obj_target.empresa

                    # Si tenemos empresa, validamos stock de items
                    if target_empresa and 'cliente_id' not in errors:
                        items_errors = []
                        for idx, item_data in enumerate(items_retiro):
                            producto_obj = item_data.get('producto')
                            cantidad_a_retirar = item_data.get('cantidad')

                            if not producto_obj:
                                items_errors.append(f"Item #{idx+1}: Producto inválido.")
                                continue
                            if cantidad_a_retirar is None or cantidad_a_retirar <= 0:
                                items_errors.append(f"Item '{producto_obj.nombre}': Cantidad debe ser mayor a 0.")
                                continue

                            try:
                                inventario = Inventario.objects.get(producto=producto_obj, empresa=target_empresa)
                                if inventario.cantidad < cantidad_a_retirar:
                                    items_errors.append(f"Item '{producto_obj.nombre}': Stock insuficiente (Disp: {inventario.cantidad}, Sol: {cantidad_a_retirar}).")
                            except Inventario.DoesNotExist:
                                items_errors.append(f"Item '{producto_obj.nombre}': No encontrado en inventario de '{target_empresa.nombre}'.")
                            except Exception as e:
                                items_errors.append(f"Item '{producto_obj.nombre}': Error consultando stock ({e}).")

                        if items_errors:
                            errors['items_a_retirar'] = items_errors
                    # --- Fin Validación Stock CORREGIDA ---
                    
        elif tipo_servicio == 'PASAJEROS':
            numero_pasajeros = data.get('numero_pasajeros')
            tipo_tarifa = data.get('tipo_tarifa_pasajero')
            duracion = data.get('duracion_estimada_horas')
            distancia = data.get('distancia_estimada_km')

            if not origen: errors['origen'] = _("Obligatorio para Transporte Pasajeros.")
            if not destino: errors['destino'] = _("Obligatorio para Transporte Pasajeros.")
            if not hora_recogida: errors['hora_recogida_programada'] = _("Obligatoria para Transporte Pasajeros.")
            if numero_pasajeros is None or numero_pasajeros <= 0: errors['numero_pasajeros'] = _("Número de pasajeros inválido.")
            if not tipo_tarifa: errors['tipo_tarifa_pasajero'] = _("Tipo de tarifa obligatorio.")
            else:
                if tipo_tarifa == 'TIEMPO' and (duracion is None or duracion <= 0): errors['duracion_estimada_horas'] = _("Duración obligatoria para tarifa por tiempo.")
                if tipo_tarifa == 'DISTANCIA' and (distancia is None or distancia <= 0): errors['distancia_estimada_km'] = _("Distancia obligatoria para tarifa por distancia.")
            # Limpia campos no aplicables
            for campo in campos_mercancia: data.pop(campo, None)
            if tipo_tarifa == 'TIEMPO': data.pop('distancia_estimada_km', None)
            if tipo_tarifa == 'DISTANCIA': data.pop('duracion_estimada_horas', None)

        elif tipo_servicio == 'RENTA_VEHICULO':
            if not hora_recogida: errors['hora_recogida_programada'] = _("Fecha/Hora de Inicio Renta obligatoria.")
            if not hora_entrega: errors['hora_entrega_programada'] = _("Fecha/Hora de Fin Renta obligatoria.")
            if not tipo_vehiculo: errors['tipo_vehiculo_requerido'] = _("Tipo de vehículo a rentar obligatorio.")
            # Validar que fin > inicio (solo si ambas fechas están presentes)
            if hora_recogida and hora_entrega and hora_recogida >= hora_entrega:
                errors['hora_entrega_programada'] = _("La fecha/hora de fin debe ser posterior a la de inicio.")
            # Limpia campos no aplicables
            for campo in campos_mercancia + campos_pasajeros + ['origen', 'destino']: data.pop(campo, None)

        else:
            errors['tipo_servicio'] = _("Tipo de servicio no válido.")

        # Si hay errores acumulados, lanzarlos
        if errors:
            raise serializers.ValidationError(errors)

        # Devolvemos los datos originales (DRF maneja la limpieza basada en fields de Meta)
        # No devolvemos la copia modificada 'validated_data' porque DRF ya hace esa limpieza.
        return data


    def create(self, validated_data):
        """
        Crea el PedidoTransporte y maneja la creación de ItemPedido
        y el descuento de stock si aplica (BODEGAJE_SALIDA).
        """
        # validated_data ya ha pasado por self.validate()
        items_data = validated_data.pop('items_a_retirar', None)
        tipo_servicio = validated_data.get('tipo_servicio') # Obtener tipo para lógica interna

        # Crear el pedido principal
        pedido = PedidoTransporte.objects.create(**validated_data)

        # Si es retiro de bodega Y hay items válidos, procesarlos
        if tipo_servicio == 'BODEGAJE_SALIDA' and items_data:
            for item_data in items_data:
                # Crear el ItemPedido asociado
                ItemPedido.objects.create(pedido=pedido, **item_data)

                # --- Lógica de Descontar Stock (CRÍTICA - Considerar Transacciones) ---
                # Idealmente, esto debería estar dentro de una transacción atómica
                # from django.db import transaction
                # with transaction.atomic(): ... (en la vista o aquí)
                try:
                    # Usar select_for_update para bloquear la fila si usas transacciones
                    inventario_a_actualizar = Inventario.objects.select_for_update().get(
                        producto=item_data.get('producto'),
                        empresa=pedido.cliente.empresa # Asume cliente y empresa existen
                    )
                    # Re-validar stock justo antes de descontar (importante por concurrencia)
                    if inventario_a_actualizar.cantidad >= item_data.get('cantidad'):
                        inventario_a_actualizar.cantidad -= item_data.get('cantidad')
                        inventario_a_actualizar.save(update_fields=['cantidad'])
                        # Aquí es un buen lugar para crear el MovimientoInventario
                        # MovimientoInventario.objects.create(...)
                    else:
                        # El stock cambió desde la validación inicial.
                        # ¿Qué hacer? ¿Cancelar el pedido? ¿Notificar?
                        # Por ahora, solo logueamos. Necesita definición de negocio.
                        print(f"ADVERTENCIA: Stock insuficiente al intentar descontar para Pedido {pedido.id}, Producto {item_data.get('producto').id}. Stock actual: {inventario_a_actualizar.cantidad}")
                        # Podrías lanzar una excepción aquí para detener la creación si es crítico
                        # raise serializers.ValidationError(f"Stock insuficiente para {item_data.get('producto').nombre} al momento de confirmar.")
                except Inventario.DoesNotExist:
                     # Esto no debería pasar si la validación fue correcta, pero es posible
                     print(f"ERROR CRÍTICO: Inventario no encontrado al descontar stock para Pedido {pedido.id}, Producto {item_data.get('producto').id}")
                     # Considera lanzar excepción
                except Exception as e:
                     print(f"ERROR inesperado descontando stock para Pedido {pedido.id}: {e}")
                     # Considera lanzar excepción
            # --- FIN Descontar Stock ---

        return pedido
