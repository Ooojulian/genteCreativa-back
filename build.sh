#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

# --- AÑADIR ESTA LÍNEA ---
# Crear superusuario inicial (leerá variables de entorno)
python manage.py create_initial_superuser
# --- FIN AÑADIR 