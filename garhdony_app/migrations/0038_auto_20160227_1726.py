# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0037_websiteaboutpage'),
    ]

    operations = [
        migrations.AddField(
            model_name='gametemplate',
            name='interest',
            field=models.TextField(default='This form is not available now.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='gametemplate',
            name='is_accepting_apps',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
