import os 
from celery import Celery

# set the default django settings models

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("banglamart")

# config name
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()



