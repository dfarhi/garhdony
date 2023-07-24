# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0026_auto_20150422_1008'),
    ]

    operations = [
        migrations.RenameField(
            model_name='nonplayercharacter',
            old_name='npc_gender',
            new_name='gender_field',
        ),
    ]
