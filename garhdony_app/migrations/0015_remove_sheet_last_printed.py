# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0014_auto_20150411_1929'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sheet',
            name='last_printed',
        ),
    ]
