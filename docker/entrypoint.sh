#!/bin/bash

# Fail on error.
set -e

# Always flush output
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Log command (for writing to stderr, unlike echo.)
log() { printf "%s\n" "$*" >&2; }

# Set some baseline variables.
PYTHON="${PYTHON:-/usr/bin/env python}"
MANAGE="${MANAGE:-$PYTHON manage.py}"

cd /app/src

# Wait for Postgres to come alive.
python /app/docker/wait_for_postgres.py

# Parse commandline.
command=$1
shift

if [ $command = "serve" ]; then

    # Migrate database.
    if [ $RUN_MIGRATE = "1" ]; then
      log "Running migrations"
      $MANAGE migrate djstripe --noinput
      $MANAGE migrate --noinput
        # log "Running stripe sync"
        # NOTE: this might break db relationships
        #  $MANAGE djstripe_init_customers
        #  $MANAGE djstripe_sync_plans_from_stripe
    fi


    log "Inserting initial data"
    $PYTHON insert_initial_data.py

    if [ $SYNC_FIXTURES = "1" ]; then
        log "Syncing Fixtures"
        # $MANAGE sync_fixtures

        $MANAGE seed_brand_size_category
        log "Loading Brands..."
        $MANAGE loaddata app/fixtures/brands.json --app app.productbrand
        log "Loading Categories.."
        $MANAGE loaddata app/fixtures/categories.json --app app.productcategory
        log "Loading Sizes.."
        $MANAGE loaddata app/fixtures/sizes.json --app app.productsize
        log "Loading Shipping Rates.."
        $MANAGE loaddata app/fixtures/shipping_rates.json --app app.shippingrate
    fi
    
    # Run django built-in debug server if DEBUG=1 (for local development)
    if [ $DEBUG = "1" ]; then

        log "Collect static"
        $MANAGE collectstatic --noinput


        log "Running debug server"
        $MANAGE runserver 0.0.0.0:$APP_PORT
    fi

    # Run uWSGI server if DEBUG=0 (for staging)
    if [ $DEBUG = "0" ]; then
        log "Running uWSGI server"
        uwsgi --ini /app/uwsgi.ini
    fi
fi

if [ $command = "celery" ]; then
    # log "Prepare background removal model..."
    # $MANAGE download_model

    log "start Celery worker!"
    celery -A base worker -l info --max-tasks-per-child=1 --concurrency=1
fi


if [ $command = "celery-beat" ]; then
    log "start celery beat"
    rm -f /tmp/*.pid
    celery -A base beat -l info --pidfile=/tmp/celerybeat.pid --scheduler django_celery_beat.schedulers:DatabaseScheduler
fi

if [ $command = "celery-flower" ]; then
    log "start celery flower"
    python -m flower flower -A base --address=0.0.0.0 --port=5050 --db=django-db --persistent=true
fi
