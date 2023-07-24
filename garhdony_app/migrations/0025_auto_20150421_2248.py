# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import garhdony_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0024_remove_sheet_dummy_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheet',
            name='last_printed',
            field=models.DateTimeField(default=garhdony_app.models.infinite_past_func, null=True),
            preserve_default=True,
        ),
    ]
