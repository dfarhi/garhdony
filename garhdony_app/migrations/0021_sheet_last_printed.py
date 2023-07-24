# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0020_remove_sheet_last_printed'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0)),
            preserve_default=True,
        ),
    ]
