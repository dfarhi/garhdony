# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0022_auto_20150411_1941'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheet',
            name='dummy_field',
            field=models.CharField(default='hi', max_length=10),
            preserve_default=False,
        ),
    ]
