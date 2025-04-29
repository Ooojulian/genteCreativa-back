# backend/proyecto/apps/usuarios/serializers.py
from rest_framework import serializers
from .models import Usuario, Rol, Empresa  # Importa los modelos necesarios
from django.contrib.auth.hashers import make_password
from ..transporte.models import Vehiculo
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import gettext_lazy as _ # Importa para mensajes de error

# Serializer simple para mostrar info básica de Empresa (solo lectura anidada)
class EmpresaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ('id', 'nombre')

# Serializer para el Token de Login que incluye datos del Usuario
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Opcional: añadir claims personalizados al token
        # token['nombre_completo'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs) # Obtiene tokens access y refresh
        # Usa UsuarioSerializer para obtener los datos del usuario
        # ¡Asegúrate que UsuarioSerializer esté definido ANTES de esta clase!
        serializer = UsuarioSerializer(self.user)
        user_data = serializer.data
        # Añade los datos del usuario a la respuesta del login
        data['user'] = user_data
        return data

# Serializer para el modelo Rol
class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'nombre')

# Serializer principal para el modelo Usuario (CRUD y lectura en Login)
class UsuarioSerializer(serializers.ModelSerializer):
    # --- Campos de Solo Lectura (para mostrar datos relacionados) ---
    rol = RolSerializer(read_only=True)
    empresa = EmpresaSimpleSerializer(read_only=True)
    vehiculo_asignado = serializers.StringRelatedField(read_only=True, allow_null=True)

    # --- Campos de Solo Escritura (para recibir IDs al crear/editar) ---
    rol_id = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(),
        source='rol',          # Mapea al campo 'rol' del modelo
        write_only=True
        # required=True por defecto, lo cual está bien para rol
    )
    # ¡Eliminamos la línea duplicada de rol_id que tenías!

    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(),
        source='empresa',       # Mapea al campo 'empresa' del modelo
        write_only=True,
        required=False,         # No requerido para roles internos
        allow_null=True         # Permite enviar null
    )
    vehiculo_asignado_id = serializers.PrimaryKeyRelatedField(
        queryset=Vehiculo.objects.filter(activo=True), # Solo permite asignar vehículos activos
        source='vehiculo_asignado',      # Mapea al campo del modelo
        write_only=True,
        required=False,                  # No siempre es requerido
        allow_null=True                  # Permite enviar null para desasignar
    )
    # --- Fin Campos ---

    class Meta:
        model = Usuario
        # --- CORRECCIÓN: Incluir 'empresa_id' en la lista ---
        fields = (
            'id', 'username', 'email', 'nombre', 'apellido', 'cedula',
            'rol', 'rol_id',           # Lectura y Escritura Rol
            'empresa', 'empresa_id',   # Lectura y Escritura Empresa
            'vehiculo_asignado',       # NUEVO: Lectura Vehículo
            'vehiculo_asignado_id',    # NUEVO: Escritura Vehículo
            'password', 'is_active', 'is_staff'
        )
        # --- FIN CORRECCIÓN ---
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            # Mantenemos is_active/is_staff editables desde el form (en Jefe),
            # pero podrías hacerlos read_only si prefieres controlarlos de otra forma.
            # 'is_active': {'read_only': True},
            # 'is_staff': {'read_only': True}
        }

    # Validación personalizada para la lógica rol/empresa
    def validate(self, data):
        # Obtiene el rol que se está intentando asignar o el existente si no se cambia
        rol_obj = None
        if 'rol' in data: # Si se envió rol_id, 'rol' tendrá el objeto Rol validado
            rol_obj = data['rol']
        elif self.instance and self.instance.rol: # Si es update y no se envió rol_id, usa el rol actual
            rol_obj = self.instance.rol

        # Obtiene el ID de vehículo enviado (puede ser None)
        vehiculo_asignado_input = data.get('vehiculo_asignado', None) # 'vehiculo_asignado' contiene el objeto Vehiculo si se envió ID válido

        # Obtiene el ID de empresa enviado (puede ser None)
        empresa_input = data.get('empresa', None) # 'empresa' contiene el objeto Empresa si se envió ID válido

        # --- Lógica de Validación Cruzada ---

        # 1. Solo conductores pueden tener vehículo
        if rol_obj and rol_obj.nombre != 'conductor' and vehiculo_asignado_input:
            raise serializers.ValidationError({
                "vehiculo_asignado_id": _("Solo los conductores pueden tener un vehículo asignado.")
            })
        # Si el rol NO es conductor, nos aseguramos que el valor final de vehiculo_asignado sea None
        # (Aunque esto también lo hace el clean del modelo, es bueno tenerlo aquí)
        if rol_obj and rol_obj.nombre != 'conductor':
             data['vehiculo_asignado'] = None # Asegura null en los datos validados

        # 2. Solo clientes pueden tener empresa
        if rol_obj and rol_obj.nombre != 'cliente' and empresa_input:
            raise serializers.ValidationError({
                "empresa_id": _(f"Los usuarios con rol '{rol_obj.nombre}' no deben tener una empresa asignada.")
            })
        # Si el rol NO es cliente, aseguramos que la empresa sea None
        if rol_obj and rol_obj.nombre != 'cliente':
            data['empresa'] = None

        # 3. Clientes DEBEN tener empresa
        if rol_obj and rol_obj.nombre == 'cliente' and not empresa_input:
             # Si es una creación (self.instance es None) Y no se envió empresa_id
             # O si es una actualización Y se intentó quitar la empresa (empresa_id es None/no enviado)
             # y el rol sigue siendo cliente.
             # Esta validación es más compleja si permites cambiar rol y empresa a la vez.
             # El clean() del modelo ya debería cubrir esto también.
             # Podríamos simplificar aquí y confiar en el modelo, o añadir lógica más explícita.
             # Por ahora, lo dejamos así, confiando en que si rol es cliente, debe venir empresa_id.
             # La validación anterior ya cubre el caso de asignar empresa a no-clientes.
             # Necesitaríamos asegurar que SIEMPRE se envíe empresa_id si rol_id es cliente.
             if not self.instance: # Si es creación
                 raise serializers.ValidationError({"empresa_id": _("Los clientes deben tener una empresa asignada.")})
             # En update, si se mantiene el rol cliente pero se quita empresa, también es error
             elif self.instance.rol.nombre == 'cliente' and 'empresa' in data and data['empresa'] is None:
                 raise serializers.ValidationError({"empresa_id": _("Los clientes deben tener una empresa asignada.")})


        # ¡Devuelve los datos validados!
        return data

    # Método para hashear contraseña al crear
    def create(self, validated_data):
        # ... (lógica existente para hashear password y crear usuario) ...
        # validated_data ya tiene 'vehiculo_asignado' (el objeto o None)
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        if not user.username and user.email: user.username = user.email
        # Las validaciones del modelo se ejecutan antes de guardar si se llama a full_clean
        # user.full_clean() # Opcional, pero recomendado si tienes validaciones en clean()
        user.save()
        return user

    # Método para hashear contraseña si se actualiza
    def update(self, instance, validated_data):
        # ... (lógica existente para hashear password si cambia) ...
        password = validated_data.pop('password', None)
        if password: instance.set_password(password)

        # Genera username si se actualiza y queda vacío pero hay email
        if 'username' in validated_data and not validated_data['username'] and validated_data.get('email', instance.email):
             validated_data['username'] = validated_data.get('email', instance.email)

        # Actualiza los demás campos (incluyendo vehiculo_asignado)
        # El super().update se encarga de asignar los valores de validated_data
        # y luego llama a instance.save(), que a su vez llamará a instance.clean()
        return super().update(instance, validated_data)


# Serializer completo para gestionar Empresas (CRUD)
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'