# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0034_auto_20160227_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='gametemplate',
            name='how_to_app',
            field=models.TextField(default='hi'),
            preserve_default=False,
        ),
    ]
