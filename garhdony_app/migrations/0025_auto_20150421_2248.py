# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import garhdony_app.models

def infinite_past_func(): pass  # Migrations think this function has to exist. It doesn't do anything.

class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0024_remove_sheet_dummy_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=infinite_past_func, null=True),
            preserve_default=True,
        ),
    ]
