# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0023_sheet_dummy_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sheet',
            name='dummy_field',
        ),
    ]
