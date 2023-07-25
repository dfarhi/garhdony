# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('garhdony_app', '0025_auto_20150421_2248'),
    ]

    operations = [
        migrations.AddField(
            model_name='nonplayercharacter',
            name='gender_linked_pc',
            field=models.ForeignKey(related_name='gender_linked_npcs', blank=True, to='garhdony_app.PlayerCharacter', null=True, on_delete=models.SET_NULL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='nonplayercharacter',
            name='npc_gender',
            field=models.CharField(default=b'M', max_length=2, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'OP', b'Opposite of'), (b'EQ', b'Same as')]),
            preserve_default=True,
        ),
    ]
