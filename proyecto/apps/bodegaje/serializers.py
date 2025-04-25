from rest_framework import serializers
from .models import Producto, Inventario, Ubicacion, Empresa, MovimientoInventario
from ..usuarios.serializers import EmpresaSimpleSerializer


# --- Serializer de Producto (Asegúrate que esté definido) ---
class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

# --- Serializer de Ubicacion (Asegúrate que esté definido) ---
class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = '__all__'


class InventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.StringRelatedField(source='producto', read_only=True, label="Producto")
    #ubicacion_nombre = serializers.StringRelatedField(source='ubicacion', read_only=True, label="Ubicación")
    empresa = EmpresaSimpleSerializer(read_only=True, label="Empresa Cliente")
    producto_id_read = serializers.IntegerField(source='producto.id', read_only=True, label="ID Producto")
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all(), source='producto', write_only=True, label="Producto (ID para Escritura)")
    ubicacion_id = serializers.PrimaryKeyRelatedField(queryset=Ubicacion.objects.all(), source='ubicacion', write_only=True, label="Ubicación (ID para Escritura)")
    empresa_id = serializers.PrimaryKeyRelatedField(queryset=Empresa.objects.all(), source='empresa', write_only=True, required=True, allow_null=False, label="Empresa Cliente (ID para Escritura)")
    fecha_creacion = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%S.%fZ") # <-- AÑADIDO (formato ISO 8601 es estándar)
    
    class Meta:
        model = Inventario
        fields = [
            'id',
            'producto_nombre', 'producto_id_read', #'ubicacion_nombre',
            'empresa', 'cantidad', #'fecha_actualizacion',
            'fecha_creacion',
            'producto_id', 'ubicacion_id', 'empresa_id', # Campos de escritura
        ]
        read_only_fields = ('fecha_actualizacion',)

    # Opcional: Añadir validaciones extra si es necesario
    def validate_cantidad(self, value):
         if value < 0:
             raise serializers.ValidationError("La cantidad no puede ser negativa.")
         return value

    def validate(self, data):
         # Validaciones combinadas si fueran necesarias
         return data

# --- SERIALIZER CORRECTO PARA MOVIMIENTO DE INVENTARIO ---
class MovimientoInventarioSerializer(serializers.ModelSerializer):
    # Representaciones legibles para campos relacionados
    usuario = serializers.StringRelatedField(read_only=True)
    producto = serializers.StringRelatedField(read_only=True)
    ubicacion = serializers.StringRelatedField(read_only=True)
    empresa = EmpresaSimpleSerializer(read_only=True) # O StringRelatedField si prefieres solo el nombre

    # Muestra el texto legible para el campo 'choices'
    tipo_movimiento = serializers.CharField(source='get_tipo_movimiento_display', read_only=True)

    # Opcional: Formatear el timestamp
    # timestamp = serializers.DateTimeField(format="%d/%m/%Y %H:%M", read_only=True)

    class Meta:
        model = MovimientoInventario
        # --- Lista de campos REALES del modelo MovimientoInventario ---
        fields = [
            'id',
            'timestamp',            # Campo de fecha real
            'usuario',              # Nombre/repr del usuario
            'tipo_movimiento',      # Texto del tipo
            'producto',             # Nombre del producto
            'ubicacion',            # Nombre de la ubicación
            'empresa',              # Nombre u objeto de la empresa
            'cantidad_anterior',    # Campo real
            'cantidad_nueva',       # Campo real
            'cantidad_cambio',      # Campo real
            'motivo',               # Campo real
            'inventario_id',        # Campo real (FK a Inventario, puede ser null)
        ]
        # No incluyas aquí campos que no existen en el modelo MovimientoInventario
# --- FIN SERIALIZER CORRECTO ---
