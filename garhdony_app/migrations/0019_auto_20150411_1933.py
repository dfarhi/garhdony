# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0018_auto_20150411_1932'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2015, 4, 11, 23, 33, 4, 875098, tzinfo=utc)),
            preserve_default=True,
        ),
    ]
