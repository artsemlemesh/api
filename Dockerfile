FROM python:3.10-slim

# create unprivileged user.
RUN useradd --create-home --shell /bin/bash bynde
RUN apt-get update -y && apt-get install -y libjpeg-dev zlib1g-dev inotify-tools curl git build-essential \
    libsm6 libxext6 chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN curl -L https://github.com/ulule/django-separatedvaluesfield/tarball/master | tar zx
RUN cd ulule-django-separatedvaluesfield-750d212 && python setup.py install
COPY ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./docker/entrypoint.sh .

# fixing windows line endings problems.
COPY ./docker/entrypoint.sh entrypoint.sh.raw
RUN sed 's/\r$//' entrypoint.sh.raw > entrypoint.sh \
    && rm entrypoint.sh.raw

# These env variables must be added on staging and production env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE='base.settings.local' \
    RUN_MIGRATE=1 \
    DEBUG=1 \
    ADMIN_EMAIL='admin@bynde.com' \
    ADMIN_PASSWORD='admin123' \
    DATABASE_URL='postgres://bynde:123@db:5433/bynde' \
    CELERY_BROKER_URL='redis://redis:6379' \
    CELERY_RESULT_BACKEND='django-db' \
    REDIS_CACHE_LOCATION="redis://redis:6379/1"


COPY docker /app/docker
COPY src /app/src
COPY uwsgi.ini /app/uwsgi.ini

EXPOSE 8000 5050
RUN chown -R \
    bynde:www-data \
    /var/log/ \
    /app/src/public/ \
    /app/src/storage/ \
    /app/src/app/fixtures/
USER bynde
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
# CMD ["serve"]

CMD ["serve", "--bind", "0.0.0.0:8000", "src/base/wsgi.py"]

