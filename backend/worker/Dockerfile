FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY worker /app

CMD ["celery", "-A", "celery_app", "worker", "-Q", "chat_queue,etl_queue", "--loglevel=info"]
