# backend/proyecto/apps/transporte/migrations/0009_tipovehiculo_alter_vehiculo_tipo.py
# ¡ARCHIVO EDITADO MANUALMENTE PARA MIGRACIÓN DE DATOS!

from django.db import migrations, models
import django.db.models.deletion

# --- Función para migrar los datos ---
# ESTA FUNCIÓN DEBE ESTAR DEFINIDA ANTES DE LA CLASE MIGRATION
# O IMPORTADA DESDE OTRO LADO SI PREFIERES ORGANIZARLO ASÍ
def forwards_func(apps, schema_editor):
    # Obtenemos los modelos como eran EN ESTE PUNTO de la historia de migraciones
    Vehiculo = apps.get_model('transporte', 'Vehiculo')
    TipoVehiculo = apps.get_model('transporte', 'TipoVehiculo')
    db_alias = schema_editor.connection.alias

    # 1. Crear los objetos TipoVehiculo básicos
    tipos_map = {}
    nombres_tipos = {
        'MOTO': 'Motocicleta',
        'PEQUENO': 'Vehículo Pequeño (Automóvil)',
        'MEDIANO': 'Vehículo Mediano (Camioneta/SUV)',
        'GRANDE': 'Vehículo Grande (Furgón/Camión pequeño)'
        # Añade otros si los tenías
    }
    print("\nCreando Tipos de Vehículo...") # Mensaje útil
    for codigo, nombre in nombres_tipos.items():
        obj, created = TipoVehiculo.objects.using(db_alias).get_or_create(nombre=nombre)
        tipos_map[codigo] = obj
        if created: print(f"  Creado: {nombre} (ID: {obj.id})")
        else: print(f"  Ya existía: {nombre} (ID: {obj.id})")

    # 2. Actualizar los Vehiculos existentes para usar el campo temporal
    print("\nActualizando vehículos existentes...")
    vehiculos_actualizados = 0
    vehiculos_sin_tipo_conocido = 0
    for vehiculo in Vehiculo.objects.using(db_alias).iterator():
        tipo_vehiculo_obj = tipos_map.get(vehiculo.tipo)
        if tipo_vehiculo_obj:
            vehiculo.tipo_temp = tipo_vehiculo_obj
            vehiculo.save(using=db_alias, update_fields=['tipo_temp'])
            vehiculos_actualizados += 1
        else:
            print(f"  ADVERTENCIA: Vehículo ID {vehiculo.id} (Placa: {vehiculo.placa}) tenía un tipo desconocido: '{vehiculo.tipo}'. Se dejará NULL.")
            vehiculos_sin_tipo_conocido += 1

    print(f"Actualizados {vehiculos_actualizados} vehículos.")
    if vehiculos_sin_tipo_conocido > 0:
         print(f"Hubo {vehiculos_sin_tipo_conocido} vehículos con tipos desconocidos que quedaron con tipo NULL.")
         print("  -> ¡DEBERÁS ASIGNARLES UN TIPO MANUALMENTE DESPUÉS DE LA MIGRACIÓN!")


# --- Función para revertir ---
def reverse_func(apps, schema_editor):
    print("\nRevertir esta migración de datos no está implementado automáticamente.")
    pass

# --- !! AQUÍ EMPIEZA LA CLASE Migration !! ---
class Migration(migrations.Migration):

    dependencies = [
        # Asegúrate que '0008_vehiculo' sea tu migración anterior CORRECTA
        ('transporte', '0008_vehiculo'),
    ]

    operations = [
        # 1. Crear el modelo TipoVehiculo
        migrations.CreateModel(
            name='TipoVehiculo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre del Tipo')),
                ('descripcion', models.TextField(blank=True, null=True, verbose_name='Descripción')),
            ],
            options={
                'verbose_name': 'Tipo de Vehículo',
                'verbose_name_plural': 'Tipos de Vehículo',
                'ordering': ['nombre'],
            },
        ),
        # 2. Añadir campo ForeignKey TEMPORAL que permite null
        migrations.AddField(
            model_name='vehiculo',
            name='tipo_temp', # Nombre temporal
            field=models.ForeignKey(
                null=True, # Permite null temporalmente
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+', # No necesitamos related_name inverso para el temporal
                to='transporte.tipovehiculo',
                verbose_name='Tipo Temporal'
            ),
             preserve_default=False,
        ),
        # 3. Ejecutar la función Python para migrar datos
        migrations.RunPython(forwards_func, reverse_func),

        # 4. Eliminar el campo CharField original 'tipo'
        migrations.RemoveField(
            model_name='vehiculo',
            name='tipo',
        ),
        # 5. Renombrar el campo temporal 'tipo_temp' a 'tipo'
        migrations.RenameField(
            model_name='vehiculo',
            old_name='tipo_temp',
            new_name='tipo',
        ),
    ]
# --- !! AQUÍ TERMINA LA CLASE Migration !! ---