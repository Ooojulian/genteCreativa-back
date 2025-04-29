# backend/proyecto/apps/usuarios/management/commands/create_initial_superuser.py

import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings # Para acceder a settings si es necesario

# Obtén tu modelo de Usuario personalizado
Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Crea un superusuario inicial si no existe uno con el username especificado.'

    def handle(self, *args, **options):
        # Lee las credenciales deseadas desde las variables de entorno
        # Es MÁS SEGURO leerlas del entorno que hardcodearlas aquí
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR(
                'Faltan variables de entorno: DJANGO_SUPERUSER_USERNAME, '
                'DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD'
            ))
            return # Salir si faltan variables

        # Verifica si el usuario ya existe
        if not Usuario.objects.filter(cedula=username).exists(): # Usa 'cedula' si es tu USERNAME_FIELD
        # if not Usuario.objects.filter(username=username).exists(): # O usa 'username' si ese es tu USERNAME_FIELD
            self.stdout.write(f"Creando superusuario inicial: {username} ({email})")
            try:
                Usuario.objects.create_superuser(
                    cedula=username,    # Usa 'cedula' si es tu USERNAME_FIELD
                    # username=username,# O usa 'username'
                    email=email,
                    password=password
                    # Puedes añadir otros campos necesarios para tu modelo Usuario aquí
                    # nombre='Admin',
                    # apellido='User'
                )
                self.stdout.write(self.style.SUCCESS(f"Superusuario {username} creado exitosamente."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al crear superusuario: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"Superusuario con username '{username}' ya existe. No se creó uno nuevo."))