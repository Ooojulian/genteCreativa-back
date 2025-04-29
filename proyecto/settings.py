# backend/proyecto/settings.py

import os
from pathlib import Path
import dj_database_url 
from datetime import timedelta # Asegúrate que esté importado

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Asegúrate que esta sea la clave correcta y consistente
SECRET_KEY = 'django-insecure-^#689i%7zyfzrj=@mz*x*$rnru3^$9x%05ygs=eelkw%al0)fx'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [] # Configura si es necesario para despliegue

# Configuración de CORS (Parece correcta para desarrollo local)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# URL base donde corre tu aplicación Frontend (React)
# Cambia esto en producción a tu dominio real
FRONTEND_BASE_URL = 'http://localhost:3000'

# Opcional: Si usas cookies o credenciales entre dominios
# CORS_ALLOW_CREDENTIALS = True

# Application definition
INSTALLED_APPS = [
    'corsheaders', # Debe ir antes que apps que manejan peticiones
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'rest_framework_simplejwt', # Asegúrate que esté instalada
    'django_filters',

    # Tus apps
    'apps.usuarios',
    'apps.transporte',
    'apps.bodegaje',
]

# --- Configuración MIDDLEWARE Limpia ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',            # CORS primero
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware', # Necesario para Admin/Login Django
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',      # <-- Comentado por ahora (para pruebas API)
    'django.contrib.auth.middleware.AuthenticationMiddleware', # <-- Procesa Auth (Session y otros backends)
    'apps.bodegaje.middleware.CurrentUserMiddleware', 
    'proyecto.middleware.RequestLogMiddleware',       # <-- Tu logger (después de Auth)
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proyecto.urls' # Archivo URL principal

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Añade directorios si tienes plantillas fuera de las apps
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'proyecto.wsgi.application'


# Database (Configuración PostgreSQL parece bien para local)
DATABASES = {
    'default': dj_database_url.config(
        # Reemplaza default='' con tu cadena de conexión local
        default='postgresql://gestion_user:1234@localhost:5432/gestion_db',
        conn_max_age=600
    )
}


# --- Configuración DRF Limpia ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Usar SOLO JWT por defecto para la API inicialmente
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Si necesitas SessionAuth para admin/browsable API, descomenta después
        # 'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Requerir autenticación por defecto para todas las vistas API
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [ # Para interfaz web de DRF y JSON
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
    # Puedes añadir aquí otras configuraciones de DRF como paginación, etc.
}

# --- Configuración SIMPLE_JWT Limpia ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False, # Simplifica manejo inicial
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Usa la SECRET_KEY principal
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id', # Campo PK en tu modelo Usuario
    'USER_ID_CLAIM': 'user_id', # Claim en el token con el ID
    # Configs por defecto suelen ser suficientes
}


# Modelo de Usuario Personalizado
AUTH_USER_MODEL = 'usuarios.Usuario'

# Password validation (Configuración estándar)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
LANGUAGE_CODE = 'es-co' # Cambiado a español Colombia (opcional)
TIME_ZONE = 'America/Bogota' # Cambiado a zona horaria Colombia (opcional)
USE_I18N = True
USE_TZ = True # Mantener True es generalmente recomendado


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'

# --- CORRECCIÓN ---
# Define STATIC_ROOT siempre, ya que collectstatic lo necesita.
# Apunta al directorio 'staticfiles' en la raíz del proyecto (backend/).
# Asegúrate de que 'os' y 'BASE_DIR' estén importados/definidos correctamente al inicio del archivo.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# --- FIN CORRECCIÓN ---

# Configuraciones específicas de producción (cuando DEBUG es False)
if not DEBUG:
    # Habilita el almacenamiento de WhiteNoise SÓLO en producción.
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Opcional: Si usas la app staticfiles de Django, este directorio es donde
# Django buscará archivos estáticos adicionales que no están dentro de tus apps.
# STATICFILES_DIRS = [ os.path.join(BASE_DIR, 'static'), ] # Ejemplo
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Logging (Opcional, pero útil - puedes mantener la configuración detallada anterior si la necesitas)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO', # Empieza con INFO, cambia a DEBUG si necesitas más detalle
    },
     # Puedes añadir loggers específicos si necesitas más detalle de DRF/JWT
     # 'loggers': { ... }
}

# Base url para servir archivos subidos por usuarios
MEDIA_URL = '/media/'

# Ruta absoluta en el sistema de archivos donde se guardarán esos archivos
# Asegúrate que esta carpeta exista y Django tenga permisos de escritura
MEDIA_ROOT = BASE_DIR / 'media' # BASE_DIR está definido usualmente al inicio del archivo
