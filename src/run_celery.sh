export DJANGO_SETTINGS_MODULE=base.settings.local

if [ -z $1 ]; then
    object='worker'
else
    object=$1
fi

celery $object -A base.celery -l INFO
