# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0028_gameinfolink'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameinfolink',
            name='link_url',
            field=models.CharField(max_length=200),
            preserve_default=True,
        ),
    ]
