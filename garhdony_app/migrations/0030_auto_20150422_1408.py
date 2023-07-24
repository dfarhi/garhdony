# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0029_auto_20150422_1324'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0, tzinfo=utc), null=True),
            preserve_default=True,
        ),
    ]
