# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0015_remove_sheet_last_printed'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2015, 4, 11, 23, 31, 3, 706483, tzinfo=utc)),
            preserve_default=True,
        ),
    ]
