from rest_framework import serializers
from .models import Producto, Inventario, Ubicacion


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = '__all__'


class InventarioSerializer(serializers.ModelSerializer):
    # Usamos StringRelatedField para mostrar representaciones de texto:
    producto = serializers.StringRelatedField(read_only=True)
    ubicacion = serializers.StringRelatedField(read_only=True)

    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(), source='producto', write_only=True #Agregamos
    )
    ubicacion_id = serializers.PrimaryKeyRelatedField(
        queryset=Ubicacion.objects.all(), source='ubicacion', write_only=True #Agregamos
    )

    class Meta:
        model = Inventario
        fields = '__all__'
