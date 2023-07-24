# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0035_gametemplate_how_to_app'),
    ]

    operations = [
        migrations.AddField(
            model_name='gametemplate',
            name='short_desc',
            field=models.TextField(default='This is a game!'),
            preserve_default=False,
        ),
    ]
