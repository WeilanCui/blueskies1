# syntax=docker/dockerfile:1

# ---- base: shared dependency layer -------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- dev: used by docker-compose, which bind-mounts source over /app ---------
FROM base AS dev

COPY . .

EXPOSE 8000

# ---- prod: self-contained image for the Swarm stack -------------------------
FROM base AS prod

COPY . .

# Collect admin and DRF assets at build time. No database is contacted, but
# settings.py refuses to import with the placeholder key while DEBUG is off, so
# a throwaway key is supplied for the duration of this one command.
RUN DJANGO_DEBUG=False DJANGO_SECRET_KEY=collectstatic-build-only \
    DJANGO_STATIC_URL=/django-static/ \
    python manage.py collectstatic --noinput

RUN chmod +x deploy/entrypoint.sh

# Drop root for the running service: it holds the database password and the Django
# secret key, and needs no privileged port (gunicorn binds 8000) and no runtime writes
# (whitenoise serves the collectstatic output produced above).
RUN useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
