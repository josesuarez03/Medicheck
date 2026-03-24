FROM python:3.13.1-slim

WORKDIR /app

# Instalar dependencias del microservicio Django
COPY django_services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar código del microservicio Django
COPY django_services /app/

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
