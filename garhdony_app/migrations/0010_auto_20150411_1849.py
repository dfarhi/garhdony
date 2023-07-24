# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0009_auto_20150411_1849'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2015, 4, 11, 18, 49, 53, 36978), null=True),
            preserve_default=True,
        ),
    ]
