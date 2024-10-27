from __future__ import absolute_import, unicode_literals
# from .celery import app as celery_app
# from .celery import Celery
from celery import Celery


__all__ = ('celery_app',)
# __all__ = ('Celery',)

# import exam_geenie.celery_setup

# Import your tasks here
from schools.tasks import send_invite_email
